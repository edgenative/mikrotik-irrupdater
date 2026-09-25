#!/bin/bash
# Script for generating BGP filters for Mikrotik RouterOS
# (c) 2023-2026 Lee Hetherington <lee@edgenative.net>
#
# Fetches the aggregated prefix list for an AS-SET with bgpq4 and stores it in
# db/<asn>.<afi>.agg. The previous copy is kept as db/<asn>.<afi>.agg.prev.
#
# Safety: bgpq4 output goes to a temporary file first and is only moved into
# place if bgpq4 exited cleanly AND produced at least one prefix. bgpq4 exits 0
# with empty output when an AS-SET is unknown, when the IRR is unreachable, or
# when the disk is full. Each of those used to leave a 0-byte .agg file behind,
# which became a reject-everything filter on the router.

path=/usr/share/mikrotik-irrupdater

asn="$1"
asset="$2"

if [ -z "$asn" ] || [ -z "$asset" ]; then
    echo "Usage: fetchprefixes.sh <asn> <as-set>"
    exit 1
fi

rc=0
for afi in 4 6; do
    target="$path/db/$asn.$afi.agg"

    if ! tmp=$(mktemp "$path/db/.$asn.$afi.agg.XXXXXX"); then
        echo "ERROR: cannot create a temporary file in $path/db (disk full?) - keeping previous $target"
        exit 2
    fi

    if ! bgpq4 -F '%n/%l \n' "-$afi" -A "$asset" > "$tmp"; then
        echo "ERROR: bgpq4 failed for as$asn $asset (IPv$afi) - keeping previous $target"
        rm -f "$tmp"
        rc=1
        continue
    fi

    if [ ! -s "$tmp" ]; then
        echo "ERROR: bgpq4 returned no IPv$afi prefixes for as$asn $asset - keeping previous $target"
        rm -f "$tmp"
        rc=1
        continue
    fi

    # Keep one backup of the last good prefix list, then atomically replace it.
    if [ -s "$target" ]; then
        cp -p "$target" "$target.prev"
    fi
    chmod 0644 "$tmp"
    mv -f "$tmp" "$target"
done

exit $rc
