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
connection = routeros_api.RouterOsApiPool(ROUTER_IP, username=username, password=password, use_ssl=False, ssl_verify=False, plaintext_login=True)
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

# Check if there are any duplicates in the current config
if len(set(current_config)) != len(current_config):
    print("Error: current config has duplicates")
    match = False
else:
    match = True

# Check if the desired config matches the current config, we're going to ignore duplicates and call it
# non matching if the router contains duplicates, but the desired configuration doesn't.
if set(desired_config) == set(current_config):
    if match:
        print(f"{CHAIN_NAME} matches - No update required")
        sys.exit()

print(f"Config does not match - Updating Router with desired {CHAIN_NAME}")

#
# Everything below here is distructive to your router configuration.  Here we know the configs don't match
# and so we assume you're good to go. This will cleanup the current config, and replace it with the chains from
# your config file.
#
# Cleanup the router configuration.  Mikrotik has no configuration management
# so sadly, the easiest way is to remove the existing filter and replace it.
#
my_list = current_config_connection.get(chain=CHAIN_NAME)
for dictionary in my_list:
    id_value = dictionary['id']
    # do something with id_value here, like passing it to another command
    print("Cleaning up chain: " + CHAIN_NAME + " rule: " + id_value)
    #command to remove chain values
    current_config_connection.remove(id=str(id_value))
#
# Add new entries based on desired configuration supplied
#
#current_config = api.get_resource('/routing/filter/rule')
with open(CONFIG_FILE) as f:
    desired_config = f.read().strip()
    for line in desired_config.splitlines():

        # Replace single quotes with double quotes
        # Mikrotik doesn't output actual JSON
        line = re.sub(r"\'", "\"", line)

        # Load the JSON data from the line
        data = json.loads(line)

        # Extract the values for the 'chain' and 'rule' keys
        # These are the only two values we really care about, we could take notice of disabled/enabled in future versions
        desired_chain = data['chain']
        desired_rule = data['rule']

        # Print the extracted values
        current_config_connection.add(rule=desired_rule,chain=CHAIN_NAME,disabled="false")
        print(f"Adding: Chain: {desired_chain}, Rule: {desired_rule}")
