#!/usr/bin/env bash
# List warehouse connections in the org.
# Usage:  scripts/api/list-connections.sh
# Output: JSON array [{connectionId, name, type}]
# Transport: `sigma api connections list` — the CLI owns auth. See _env.sh.
set -euo pipefail
SIGMA_ENV_CLI_ONLY=1 source "$(dirname "$0")/_env.sh"

sigma_cli api connections list --params '{"limit":200}' -f json \
  | python3 -c '
import sys, json
d = json.load(sys.stdin)
out = [{"connectionId": e.get("connectionId"), "name": e.get("name"), "type": e.get("type")}
       for e in d.get("entries", [])]
json.dump(out, sys.stdout, indent=2)
print()
'
