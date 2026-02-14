#!/usr/bin/env python3
# Script for generating BGP filter for Mikrotik RouterOS
# (c) 2023-2026 Lee Hetherington <lee@edgenative.net>
#
import os
import sys

# Set the path configuration variable here
path = "/usr/share/mikrotik-irrupdater"

def generate_filter(slug, asn, afi):
    """Generate filter rules for a given address family.

    Args:
        slug: Exchange/peer slug name
        asn: AS number
        afi: Address family - 4 for IPv4, 6 for IPv6
    """
    max_prefix_len = 24 if afi == 4 else 48
    prefix_file = f"{path}/db/{asn}.{afi}.agg"
    output_file = f"{path}/filters/as{asn}-{slug}-import-ipv{afi}.txt"
    chain_name = f"as{asn}-{slug}-import-ipv{afi}"

    if not os.path.exists(prefix_file):
        print(f"Error: Prefix file not found: {prefix_file}", file=sys.stderr)
        sys.exit(1)

    seen = set()
    with open(output_file, "w") as f:
        with open(prefix_file, "r") as prefixes:
            for prefix in prefixes:
                prefix = prefix.strip()
                if not prefix or prefix in seen:
                    continue
                seen.add(prefix)
                masklength = int(prefix.split("/")[1])
                if masklength == max_prefix_len:
                    f.write(f"{{'chain': '{chain_name}', 'rule': 'if (dst=={prefix}) {{ jump {slug}-import }}'}}\n")
                elif masklength < max_prefix_len:
                    f.write(f"{{'chain': '{chain_name}', 'rule': 'if (dst in {prefix} && dst-len<={max_prefix_len}) {{ jump {slug}-import }}'}}\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 mikrotik-filtergen.py <slug> <ASN>")
        sys.exit(1)

    slug = sys.argv[1]
    asn = sys.argv[2]

    generate_filter(slug, asn, 4)
    generate_filter(slug, asn, 6)
