#!/usr/bin/env bash
# List columns of a warehouse table by its inodeId.
# Usage:  scripts/api/list-table-columns.sh <inodeId>
# Output: JSON array [{name, type}]
# Transport: `sigma api connections tables columns list`. See _env.sh.
#
# These are the RAW warehouse column names. Sigma's normalized friendly names show up
# in a workbook's GET-back — when a formula says "Unknown column", compare the two.
set -euo pipefail
SIGMA_ENV_CLI_ONLY=1 source "$(dirname "$0")/_env.sh"

if [ "$#" -ne 1 ]; then
  echo "usage: list-table-columns.sh <inodeId>" >&2
  exit 2
fi

sigma_cli api connections tables columns list \
  --params "{\"tableId\":\"$1\",\"pageSize\":200}" -f json \
  | python3 -c '
import sys, json
d = json.load(sys.stdin)
out = [{"name": c.get("name"), "type": (c.get("type") or {}).get("type")} for c in d.get("entries", [])]
json.dump(out, sys.stdout, indent=2); print()
'
