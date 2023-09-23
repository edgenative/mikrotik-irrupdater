#!/bin/bash
# Script for generating BGP filter for Mikrotik RouterOS
# (c) 2023 Lee Hetherington <lee@edgenative.net>

path=/usr/share/mikrotik-irrupdater

# Check if the configuration file exists
if [ ! -f $path/config/sessions.conf ]; then
    echo "Configuration File 'peers.conf' not found."
    exit 1
fi

# Read the input file line by line
while IFS=',' read -r param1 param2 param3; do
    if [ -n "$param1" ] && [ -n "$param2" ]; then
        # Run the python, with ASN $param1, slug $param2 and the router IP Address as $param3. Run for both IPv4 and IPv6
	python3 $path/bin/mikrotik_irr_updater.py as$param1-$param2-import-ipv4 $path/filters/as$param1-$param2-import-ipv4.txt $param3
	python3 $path/bin/mikrotik_irr_updater.py as$param1-$param2-import-ipv6 $path/filters/as$param1-$param2-import-ipv6.txt $param3
    fi
done < $path/config/sessions.conf
