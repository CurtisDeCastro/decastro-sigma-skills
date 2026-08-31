#!/usr/bin/env bash
# Probe a schema for table existence by trying a list of likely names via lookup.
# Used when the API has no "list children of a schema scope" endpoint.
# Usage:  scripts/api/probe-schema-tables.sh <connectionId> <db> <schema> [names...]
# Output: JSON array [{name, inodeId}] for hits.
# Transport: `sigma api connections lookup` via scripts/sigma_api.py. See _env.sh.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"

if [ "$#" -lt 3 ]; then
  echo "usage: probe-schema-tables.sh <connectionId> <db> <schema> [names...]" >&2
  exit 2
fi

CONN="$1"; DB="$2"; SCHEMA="$3"; shift 3

# Default name list — common warehouse-sample table names.
if [ "$#" -eq 0 ]; then
  set -- \
    TRIP TRIPS STATION STATIONS WEATHER \
    CUSTOMER CUSTOMERS USER USERS \
    ORDER ORDERS PRODUCT PRODUCTS \
    SALES TRANSACTIONS PAYMENTS RENTALS \
    EVENT EVENTS SESSIONS RIDES BIKES \
    ACCOUNTS ACCOUNT INVOICES INVOICE \
    EMPLOYEE EMPLOYEES STORE STORES
fi

REPO_ROOT="$repo_root" python3 -c '
import os, sys, json
sys.path.insert(0, os.path.join(os.environ["REPO_ROOT"], "scripts"))
from concurrent.futures import ThreadPoolExecutor
from sigma_api import api, SigmaApiError

conn, db, schema, *names = sys.argv[1:]

def probe(name):
    # A miss is a 404 from the CLI, which sigma_api raises — that is the signal here,
    # not an error, so it must not abort the sweep.
    try:
        d = api("connections", "lookup", params={"connectionId": conn},
                body={"path": [db, schema, name]})
    except SigmaApiError:
        return None
    return {"name": name, "inodeId": d.get("inodeId")} if d.get("kind") == "table" else None

with ThreadPoolExecutor(max_workers=8) as ex:
    found = [r for r in ex.map(probe, names) if r]
json.dump(found, sys.stdout, indent=2); print()
' "$CONN" "$DB" "$SCHEMA" "$@"
