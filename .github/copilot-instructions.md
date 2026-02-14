# Copilot Instructions

## Project Overview

mikrotik-irrupdater generates and pushes IRR-based BGP prefix filters to Mikrotik routers running RouterOS 7+ via the RouterOS API.

## Data Flow

```
peers.conf → fetchprefixes.sh (bgpq4) → db/{asn}.4.agg / db/{asn}.6.agg
sessions.conf → mikrotik-filtergen.py → filters/{label}-{slug}-import-ipv{4,6}.txt
sessions.conf → pushfilters.sh → mikrotik-irrupdater.py → RouterOS API
```

`buildprefixes.sh` orchestrates the first two steps. `pushfilters.sh` handles deployment.

## Configuration Files

- `config/peers.conf` - CSV: `ASN,AS-SET`
- `config/sessions.conf` - CSV: `ASN,slug,router[,affinity][,peer_name]`
  - `affinity` is optional: `ipv4`, `ipv6`, or empty for both
  - `peer_name` is optional: replaces `as{ASN}` in chain/filter names (e.g. `Kerfuffle` instead of `as35008`)
  - Use double comma for peer name without affinity: `35008,fcix,pr1.fmt2,,Kerfuffle`
- `config/routers.conf` - INI format with `[API]` section containing `username` and `password`

## Chain/Filter Naming

The label used in chain names and filter filenames is either `peer_name` (if provided) or `as{ASN}`. The pattern is: `{label}-{slug}-import-ipv{4|6}`.

Prefix database files in `db/` are always keyed by ASN regardless of peer name.

## Key Conventions

- The RouterOS API `.get()` returns a list of dicts - never use `eval()` to parse API responses
- Prefix length limits: /24 for IPv4, /48 for IPv6
- Filter rules use single-quoted Python dict syntax (not JSON) for historical reasons - the irrupdater script converts quotes before parsing with `json.loads()`
- All scripts expect to be installed at `/usr/share/mikrotik-irrupdater/`
- Backwards compatibility matters - config changes must not break existing setups without the new optional fields
