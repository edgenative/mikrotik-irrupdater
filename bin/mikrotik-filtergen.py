#!/usr/bin/env python3
# Script for generating BGP filter for Mikrotik RouterOS
# (c) 2023-2026 Lee Hetherington <lee@edgenative.net>
#
# Safety: a filter is only written when the prefix db for that ASN/AFI exists and
# yields at least one rule. Otherwise the existing filter file is left untouched
# and the script exits non-zero. A 0-byte db file (disk full, IRR outage, unknown
# AS-SET) used to produce an empty filter file, which mikrotik-irrupdater.py would
# then turn into an empty chain on the router by removing every rule.
#
# The filter is written to a temporary file and atomically renamed into place, so
# a crash or a full disk mid-write can never leave a truncated filter behind.

import os
import sys
import tempfile

# Set the path configuration variable here
path = "/usr/share/mikrotik-irrupdater"

def generate_filter(slug, asn, afi, peer_name=None):
    """Generate filter rules for a given address family.

    Args:
        slug: Exchange/peer slug name
        asn: AS number
        afi: Address family - 4 for IPv4, 6 for IPv6
        peer_name: Optional human-readable peer name (replaces 'as{ASN}' in chain/file names)

    Returns True when a filter was written, False when it was refused.
    """
    label = peer_name if peer_name else f"as{asn}"
    max_prefix_len = 24 if afi == 4 else 48
    prefix_file = f"{path}/db/{asn}.{afi}.agg"
    output_dir = f"{path}/filters"
    output_file = f"{output_dir}/{label}-{slug}-import-ipv{afi}.txt"
    chain_name = f"{label}-{slug}-import-ipv{afi}"

    if not os.path.isfile(prefix_file) or os.path.getsize(prefix_file) == 0:
        print(f"ERROR: {prefix_file} is missing or empty - not generating {chain_name} (existing filter left untouched)", file=sys.stderr)
        return False

    rules = []
    seen = set()
    with open(prefix_file, "r") as prefixes:
        for prefix in prefixes:
            prefix = prefix.strip()
            if not prefix or prefix in seen:
                continue
            seen.add(prefix)
            masklength = int(prefix.split("/")[1])
            if masklength == max_prefix_len:
                rules.append(f"{{'chain': '{chain_name}', 'rule': 'if (dst=={prefix}) {{ jump {slug}-import }}'}}\n")
            elif masklength < max_prefix_len:
                rules.append(f"{{'chain': '{chain_name}', 'rule': 'if (dst in {prefix} && dst-len<={max_prefix_len}) {{ jump {slug}-import }}'}}\n")

    if not rules:
        print(f"ERROR: {prefix_file} contained no usable prefixes - not generating {chain_name} (existing filter left untouched)", file=sys.stderr)
        return False

    # Write to a temp file in the same directory, then rename over the old filter.
    fd, tmp_file = tempfile.mkstemp(prefix=f".{chain_name}.", suffix=".tmp", dir=output_dir)
    try:
        with os.fdopen(fd, "w") as f:
            f.writelines(rules)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp_file, 0o644)
        os.replace(tmp_file, output_file)
    except OSError as e:
        print(f"ERROR: could not write {output_file}: {e} (existing filter left untouched)", file=sys.stderr)
        try:
            os.unlink(tmp_file)
        except OSError:
            pass
        return False

    print(f"Generated {chain_name} with {len(rules)} rules")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python3 mikrotik-filtergen.py <slug> <ASN> [peer_name]")
        sys.exit(1)

    slug = sys.argv[1]
    asn = sys.argv[2]
    peer_name = sys.argv[3] if len(sys.argv) == 4 else None

    ok4 = generate_filter(slug, asn, 4, peer_name)
    ok6 = generate_filter(slug, asn, 6, peer_name)
    sys.exit(0 if (ok4 and ok6) else 1)
