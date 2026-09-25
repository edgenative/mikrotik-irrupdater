#!/bin/bash
# Script for generating BGP filter for Mikrotik RouterOS
# (c) 2023-2026 Lee Hetherington <lee@edgenative.net>


path=/usr/share/mikrotik-irrupdater

# Refuse to run when the disk is nearly full. bgpq4 and filtergen would otherwise
# write empty or truncated files. The downstream scripts guard against that too,
# but there is no point starting. Exit code 2 so a wrapper can tell this apart
# from a per-peer failure (exit code 1).
min_free_kb=204800  # 200 MB
free_kb=$(df -Pk "$path" | awk 'NR==2 {print $4}')
if [ -z "$free_kb" ] || [ "$free_kb" -lt "$min_free_kb" ]; then
    echo "ERROR: only ${free_kb:-?} KB free on the filesystem holding $path (need $min_free_kb KB). Aborting."
    exit 2
fi

failed=0

# Check if the configuration file 'peers.conf' exists
if [ ! -f $path/config/peers.conf ]; then
    echo "Configuration File 'peers.conf' not found."
    exit 1
fi

# Read the input file line by line
while IFS=',' read -r param1 param2; do
    if [ -n "$param1" ] && [ -n "$param2" ]; then
        # Run bgpq4 to fetch the prefixes, with ASN $param1 and AS-SET $param2 as arguments
        $path/bin/fetchprefixes.sh "$param1" "$param2" || failed=1
    fi
done < $path/config/peers.conf

# Check if the configuration file 'sessions.conf' exists
if [ ! -f $path/config/sessions.conf ]; then
    echo "Configuration File 'sessions.conf' not found."
    exit 1
fi

# Read the input file line by line
while IFS=',' read -r param1 param2 param3 param4 param5; do
    if [ -n "$param1" ] && [ -n "$param2" ]; then
        # Run filtergen with ASN $param1, slug $param2, and optional peer name $param5
        if [ -n "$param5" ]; then
            python3 $path/bin/mikrotik-filtergen.py "$param2" "$param1" "$param5" || failed=1
        else
            python3 $path/bin/mikrotik-filtergen.py "$param2" "$param1" || failed=1
        fi
    fi
done < $path/config/sessions.conf

if [ "$failed" -ne 0 ]; then
    echo "WARNING: one or more prefix fetches or filter generations failed (see above). Those filters were left as they were."
fi
exit $failed
