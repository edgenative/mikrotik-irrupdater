# Copyright (c) 2023 - Lee Hetherington <lee@edgenative.net>
# Script: mikrotik_irr_updater.py
#
# Usage: mikrotik-irrupdater.py chain_name config_file router_ip
#
# This script will take an input file in the format of the Mikrotik RouterOS API for a /routing/filter/rule
# and compare it with the version already on the router.  It's aim is to give you the ability to update IRR filters
# against your BGP peers, whilst comparing if an update is required.

import sys
import configparser
import routeros_api
import json
import re
import argparse

#
# Where is everything installed?
#

path = "/usr/share/mikrotik-irrupdater"

#
# We want to take some inputs from the command line, such as the name of the route-filter chain
# the desired config in a text file and the IP/Hostname of the router API endpoint
#
parser = argparse.ArgumentParser()

# add arguments to the parser
parser.add_argument("chain_name", help="name of the import chain")
parser.add_argument("config_file", help="path to the desired configuration of the chain")
parser.add_argument("router_ip", help="IP address or hostname of the router")

# parse the arguments
args = parser.parse_args()

# access the values of the arguments
CHAIN_NAME = args.chain_name
CONFIG_FILE = args.config_file
ROUTER_IP = args.router_ip

# Read from the config file
# which contains the auth information
config = configparser.ConfigParser()
config.read(f"{path}/config/routers.conf")
username = config.get('API', 'username')
password = config.get('API', 'password')

# Build the API connection to the router
connection = routeros_api.RouterOsApiPool(ROUTER_IP, username=username, password=password, use_ssl=True, ssl_verify=False, plaintext_login=True)
api = connection.get_api()

# Let's compare the router and the desired configuration

with open(CONFIG_FILE, 'r') as f:
    desired_config = []
    for line in f:
        line = re.sub(r"\'", "\"", line)
        data = json.loads(line)
        desired_config.append((data['chain'], data['rule']))

# Get the current configuration from the router
current_config_connection = api.get_resource('/routing/filter/rule')
current_config_response = current_config_connection.get(chain=CHAIN_NAME)
current_config_str = str(current_config_response)
config_list = eval(current_config_str)

# Create a list of tuples of chain and rule from the current config
current_config = []
for item in config_list:
    chain = item.get('chain')
    rule = item.get('rule')
    current_config.append((chain, rule))

# Check if the desired config matches the current config
if set(desired_config) == set(current_config):
        print(f"{CHAIN_NAME} matches - No update required")
        sys.exit()

print(f"Config does not match - Updating Router with desired {CHAIN_NAME}")

# Routes that needs to be added
to_add = set(desired_config) - set(current_config)
if to_add:
    print("Rules to add:")
    for desired_chain,desired_rule in to_add:
        print(f"  + {desired_rule}")
        try:
            current_config_connection.add(rule=desired_rule,chain=desired_chain,disabled="false")
        except Exception as e:
            print(f"Failed to add rule to chain {chain}: {rule}\nError: {e}")
else:
    print("No new rules to add.")

# Routes that needs to be removed
my_list = current_config_connection.get(chain=CHAIN_NAME)
rule_to_id_map = {entry['rule']: entry['id'] for entry in my_list}
to_remove = set(current_config) - set(desired_config)
if to_remove:
    print("Rules to remove:")
    for chain, rule in to_remove:
        rule_id = rule_to_id_map.get(rule)
        if rule_id:
            print(f"  - Removing rule from chain {chain}: {rule}")
            current_config_connection.remove(id=str(rule_id))
        else:
            print(f"Could not find ID for rule: {rule} - Skipping")
