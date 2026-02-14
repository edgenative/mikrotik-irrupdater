#!/bin/bash
# Script for generating BGP filter for Mikrotik RouterOS
# (c) 2023-2026 Lee Hetherington <lee@edgenative.net>

path=/usr/share/mikrotik-irrupdater

# Check if the configuration file exists
if [ ! -f $path/config/sessions.conf ]; then
    echo "Configuration File 'sessions.conf' not found."
    exit 1
fi

# Read the input file line by line
while IFS=',' read -r param1 param2 param3 param4 param5; do
    if [ -n "$param1" ] && [ -n "$param2" ]; then
        # Use peer name if provided, otherwise default to as<ASN>
        if [ -n "$param5" ]; then
            label="$param5"
        else
            label="as$param1"
        fi

        # Check if param4 is specified and if it's IPv4 or IPv6
        if [ -n "$param4" ]; then
            if [ "$param4" = "ipv4" ]; then
                # Run for IPv4 only
                python3 $path/bin/mikrotik-irrupdater.py $label-$param2-import-ipv4 $path/filters/$label-$param2-import-ipv4.txt $param3
            elif [ "$param4" = "ipv6" ]; then
                # Run for IPv6 only
                python3 $path/bin/mikrotik-irrupdater.py $label-$param2-import-ipv6 $path/filters/$label-$param2-import-ipv6.txt $param3
            else
                echo "Invalid value for session affinity: $param4"
            fi
        else
            # Run for both IPv4 and IPv6
            python3 $path/bin/mikrotik-irrupdater.py $label-$param2-import-ipv4 $path/filters/$label-$param2-import-ipv4.txt $param3
            python3 $path/bin/mikrotik-irrupdater.py $label-$param2-import-ipv6 $path/filters/$label-$param2-import-ipv6.txt $param3
        fi
    fi
done < $path/config/sessions.conf
