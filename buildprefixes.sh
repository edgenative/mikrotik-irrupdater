#!/bin/bash
# Script for generating BGP filter for Mikrotik RouterOS
# (c) 2023 Lee Hetherington <lee@edgenative.net>


path=/home/lee/test

# Check if the configuration file 'peers.conf' exists
if [ ! -f $path/config/peers.conf ]; then
    echo "Configuration File 'peers.conf' not found."
    exit 1
fi

# Read the input file line by line
while IFS=',' read -r param1 param2; do
    if [ -n "$param1" ] && [ -n "$param2" ]; then
        # Run bgpq4 to fetch the prefixes, with ASN $param1 and AS-SET $param2 as arguments
        $path/bin/fetchprefixes.sh "$param1" "$param2"
    fi
done < $path/config/peers.conf

# Check if the configuration file 'sessions.conf' exists
if [ ! -f $path/config/sessions.conf ]; then
    echo "Configuration File 'sessions.conf' not found."
    exit 1
fi

# Read the input file line by line
while IFS=',' read -r param1 param2 param3; do
    if [ -n "$param1" ] && [ -n "$param2" ]; then
        # Run bgpq4 to fetch the prefixes, with ASN $param1 and AS-SET $param2 as arguments
        $path/bin/filtergen.sh get "$param1" "$param2"
    fi
done < $path/config/sessions.conf
