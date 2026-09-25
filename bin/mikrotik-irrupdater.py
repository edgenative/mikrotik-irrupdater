# Copyright (c) 2023-2026 - Lee Hetherington <lee@edgenative.net>
# Script: mikrotik-irrupdater.py
#
# Usage: mikrotik-irrupdater.py chain_name config_file router_ip
#
# This script will take an input file in the format of the Mikrotik RouterOS API for a /routing/filter/rule
# and compare it with the version already on the router.  It's aim is to give you the ability to update IRR filters
# against your BGP peers, whilst comparing if an update is required.

import sys
import os
import configparser
import routeros_api
import json
import argparse

#
# Where is everything installed?
#

path = "/usr/share/mikrotik-irrupdater"

# ---------------------------------------------------------------------------
# Local safety checks - run BEFORE anything is pushed to the router.
#
# Background: a full disk once left every db/*.agg file at 0 bytes. The filter
# generator turned those into empty filter files, this script saw they "differed"
# from the router, and removed every rule from every chain. These checks make
# that impossible:
#
#   1. an empty or malformed filter file is never pushed
#   2. a copy of every filter is kept in filters/last-pushed/ after a successful
#      push (and seeded when a chain is found to be up to date)
#   3. before pushing, the new file is compared with that copy - if it lost all
#      of its prefix rules, or more than SHRINK_REFUSE_RATIO of them (once the
#      baseline had at least SHRINK_MIN_BASELINE rules), the push is refused
#   4. if any rule fails to add, the old rules are NOT removed
#   5. new rules are inserted BEFORE any terminal rule already in the chain (a
#      bare 'reject' or 'accept'); appended after it they would never be reached
#   6. after pushing, the chain is read back from the router and compared with
#      the file; the push only counts as done when the router actually matches
#
# A known-good large change can be pushed by setting IRRUPDATER_FORCE=1 in the
# environment; that bypasses check 3 only. The other checks always apply.
# ---------------------------------------------------------------------------
LAST_PUSHED_DIR = f"{path}/filters/last-pushed"
SHRINK_MIN_BASELINE = 10   # apply the ratio check only when the last pushed copy had at least this many rules
SHRINK_REFUSE_RATIO = 0.8  # refuse when more than 80% of the rules disappeared

def load_filter_file(config_file):
    # Returns a list of (chain, rule) tuples. Raises ValueError on a malformed line.
    desired = []
    with open(config_file, 'r') as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line.replace("'", '"'))
                desired.append((data['chain'], data['rule']))
            except (ValueError, KeyError, TypeError) as e:
                raise ValueError(f"line {lineno} is not a valid rule: {e}")
    return desired

def is_prefix_rule(rule):
    # A rule that matches on a prefix, as opposed to a bare terminal 'reject' / 'accept'.
    return "dst" in rule

def count_prefix_rules(rules):
    return sum(1 for _, rule in rules if is_prefix_rule(rule))

def read_chain(resource, chain_name):
    # Returns (list of (chain, rule), {rule: id}, id of the first terminal rule or None) for the chain on the router.
    rules = []
    rule_to_id = {}
    terminal_id = None
    for item in resource.get(chain=chain_name):
        chain = item.get('chain')
        rule = item.get('rule')
        rules.append((chain, rule))
        rule_to_id[rule] = item.get('id')
        if terminal_id is None and rule is not None and not is_prefix_rule(rule):
            terminal_id = item.get('id')
    return rules, rule_to_id, terminal_id

def last_pushed_file(chain_name):
    return os.path.join(LAST_PUSHED_DIR, f"{chain_name}.txt")

def sanity_check_filter(chain_name, config_file):
    # Returns (desired_config, None) when safe to push, or (None, reason) when it must not be.
    if not os.path.isfile(config_file) or os.path.getsize(config_file) == 0:
        return None, "filter file is missing or empty"
    try:
        desired = load_filter_file(config_file)
    except ValueError as e:
        return None, str(e)
    if not desired:
        return None, "filter file contains no rules"
    wrong_chain = [c for c, _ in desired if c != chain_name]
    if wrong_chain:
        return None, f"filter file contains rules for chain {wrong_chain[0]}, expected {chain_name}"

    baseline = last_pushed_file(chain_name)
    if not os.path.isfile(baseline):
        return desired, None

    try:
        old_count = count_prefix_rules(load_filter_file(baseline))
    except ValueError:
        return desired, None
    new_count = count_prefix_rules(desired)
    force = os.environ.get("IRRUPDATER_FORCE") == "1"

    if old_count > 0 and new_count == 0:
        reason = f"filter lost all {old_count} prefix rules since the last push"
    elif old_count >= SHRINK_MIN_BASELINE and new_count < old_count * (1 - SHRINK_REFUSE_RATIO):
        reason = f"prefix rules dropped from {old_count} to {new_count} (more than {int(SHRINK_REFUSE_RATIO * 100)}% shrink)"
    else:
        return desired, None

    if force:
        print(f"WARNING: {reason} - pushing anyway because IRRUPDATER_FORCE=1")
        return desired, None
    return None, f"{reason}; refusing to push. Set IRRUPDATER_FORCE=1 to override if this is expected"

def record_last_pushed(chain_name, config_file):
    # Remember what the router now has, so the next run has something to compare against.
    try:
        os.makedirs(LAST_PUSHED_DIR, exist_ok=True)
        tmp = last_pushed_file(chain_name) + ".tmp"
        with open(config_file, 'r') as src, open(tmp, 'w') as dst:
            dst.write(src.read())
        os.replace(tmp, last_pushed_file(chain_name))
    except OSError as e:
        print(f"WARNING: could not record last pushed copy of {chain_name}: {e}")

def main():
    #
    # We want to take some inputs from the command line, such as the name of the route-filter chain
    # the desired config in a text file and the IP/Hostname of the router API endpoint
    #
    parser = argparse.ArgumentParser()
    parser.add_argument("chain_name", help="name of the import chain")
    parser.add_argument("config_file", help="path to the desired configuration of the chain")
    parser.add_argument("router_ip", help="IP address or hostname of the router")
    args = parser.parse_args()

    CHAIN_NAME = args.chain_name
    CONFIG_FILE = args.config_file
    ROUTER_IP = args.router_ip

    # Check the local file BEFORE talking to the router at all.
    desired_config, problem = sanity_check_filter(CHAIN_NAME, CONFIG_FILE)
    if problem:
        print(f"REFUSED: {CHAIN_NAME} on {ROUTER_IP}: {problem}")
        sys.exit(1)

    # Read from the config file which contains the auth information
    config = configparser.ConfigParser()
    config.read(f"{path}/config/routers.conf")
    username = config.get('API', 'username')
    password = config.get('API', 'password')

    # Build the API connection to the router
    connection = routeros_api.RouterOsApiPool(ROUTER_IP, username=username, password=password, use_ssl=True, ssl_verify=False, plaintext_login=True)
    api = connection.get_api()

    # Get the current configuration from the router. This also gives us the rule ids
    # for removals later, and the id of any terminal rule so new rules go in front of it.
    current_config_connection = api.get_resource('/routing/filter/rule')
    current_config, rule_to_id_map, terminal_id = read_chain(current_config_connection, CHAIN_NAME)

    # Check if the desired config matches the current config
    if set(desired_config) == set(current_config):
        print(f"{CHAIN_NAME} matches - No update required")
        record_last_pushed(CHAIN_NAME, CONFIG_FILE)
        sys.exit()

    print(f"Config does not match - Updating Router with desired {CHAIN_NAME}")

    # Rules that need to be added
    add_failures = 0
    to_add = set(desired_config) - set(current_config)
    if to_add:
        print("Rules to add:")
        for desired_chain, desired_rule in to_add:
            print(f"  + {desired_rule}")
            try:
                extra = {"place-before": str(terminal_id)} if terminal_id else {}
                current_config_connection.add(rule=desired_rule, chain=desired_chain, disabled="false", **extra)
            except Exception as e:
                add_failures += 1
                print(f"Failed to add rule to chain {desired_chain}: {desired_rule}\nError: {e}")
    else:
        print("No new rules to add.")

    # Never strip the old rules out if the new ones did not all go in - that would
    # leave the chain partially (or completely) empty.
    if add_failures:
        print(f"ERROR: {add_failures} rule(s) failed to add - leaving the existing rules in place, not removing anything")
        sys.exit(1)

    # Rules that need to be removed
    remove_failures = 0
    to_remove = set(current_config) - set(desired_config)
    if to_remove:
        print("Rules to remove:")
        for chain, rule in to_remove:
            rule_id = rule_to_id_map.get(rule)
            if rule_id:
                print(f"  - Removing rule from chain {chain}: {rule}")
                try:
                    current_config_connection.remove(id=str(rule_id))
                except Exception as e:
                    remove_failures += 1
                    print(f"Failed to remove rule from chain {chain}: {rule}\nError: {e}")
            else:
                remove_failures += 1
                print(f"Could not find ID for rule: {rule} - Skipping")

    if remove_failures:
        print(f"WARNING: {remove_failures} rule(s) could not be removed - the router has extra rules; not recording this as the last pushed state")
        sys.exit(1)

    # Read the chain back and make sure the router really has what we asked for.
    # A successful API call is not evidence the rule landed where we meant it to.
    verified_config, _, _ = read_chain(current_config_connection, CHAIN_NAME)
    if set(verified_config) != set(desired_config):
        missing = set(desired_config) - set(verified_config)
        extra = set(verified_config) - set(desired_config)
        print(f"ERROR: after the update {CHAIN_NAME} on {ROUTER_IP} still does not match the file "
              f"({len(missing)} rule(s) missing, {len(extra)} unexpected); not recording this as the last pushed state")
        for _, rule in list(missing)[:5]:
            print(f"  missing: {rule}")
        for _, rule in list(extra)[:5]:
            print(f"  unexpected: {rule}")
        sys.exit(1)

    print(f"Verified: {CHAIN_NAME} on {ROUTER_IP} now matches the file ({len(desired_config)} rules)")
    record_last_pushed(CHAIN_NAME, CONFIG_FILE)

if __name__ == "__main__":
    main()
