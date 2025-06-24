#!/usr/bin/env python3
# Script for generating BGP filter for Mikrotik RouterOS
# (c) 2023 Lee Hetherington <lee@edgenative.net>
#
import os
import sys

# Set the path configuration variable here
path = "/usr/share/mikrotik-irrupdater"

def generate_ipv4_filter(slug, asn):
    with open(f"{path}/filters/as{asn}-{slug}-import-ipv4.txt", "w") as f:
        with open(f"{path}/db/{asn}.4.agg", "r") as prefixes:
            for prefix in prefixes:
                prefix = prefix.strip()
                masklength = int(prefix.split("/")[1])
                if masklength == 24:
                    # Prefix is a /24 - generating config without defining prefix length
                    f.write(f"{{'chain': 'as{asn}-{slug}-import-ipv4', 'rule': 'if (dst=={prefix}) {{ jump {slug}-import }}'}}\n")
                elif masklength < 24:
                    # Prefix is greater than /24 - generating config with prefix length up to /24
                    f.write(f"{{'chain': 'as{asn}-{slug}-import-ipv4', 'rule': 'if (dst in {prefix} && dst-len<=24) {{ jump {slug}-import }}'}}\n")

def generate_ipv6_filter(slug, asn):
    with open(f"{path}/filters/as{asn}-{slug}-import-ipv6.txt", "w") as f:
        with open(f"{path}/db/{asn}.6.agg", "r") as prefixes6:
            for prefix6 in prefixes6:
                prefix6 = prefix6.strip()
                masklength6 = int(prefix6.split("/")[1])
                if masklength6 == 48:
                    # Prefix is a /48 - generating config without defining prefix length
                    f.write(f"{{'chain': 'as{asn}-{slug}-import-ipv6', 'rule': 'if (dst=={prefix6}) {{ jump {slug}-import }}'}}\n")
                elif masklength6 < 48:
                    # Prefix is greater than /48 - generating config with prefix length up to /48
                    f.write(f"{{'chain': 'as{asn}-{slug}-import-ipv6', 'rule': 'if (dst in {prefix6} && dst-len<=48) {{ jump {slug}-import }}'}}\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 mikrotik-filtergen.py <slug> <ASN>")
        sys.exit(1)

    slug = sys.argv[1]
    asn = sys.argv[2]

    generate_ipv4_filter(slug, asn)
    generate_ipv6_filter(slug, asn)
