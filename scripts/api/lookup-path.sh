#!/usr/bin/env bash
# Look up a fully-qualified path under a connection.
# Usage:  scripts/api/lookup-path.sh <connectionId> <path1> <path2> [<path3>]
# Output: JSON {kind, inodeId, url, path} on success, {error, code, message} otherwise.
# Transport: `sigma api connections lookup`. See _env.sh.
set -euo pipefail
SIGMA_ENV_CLI_ONLY=1 source "$(dirname "$0")/_env.sh"

if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
  echo "usage: lookup-path.sh <connectionId> <path1> <path2> [<path3>]" >&2
  exit 2
fi

CONN="$1"; shift
PATH_JSON=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1:]))" "$@")

# The CLI exits non-zero and prints a JSON error object when the path doesn't resolve;
# capture both streams so a miss is reported as data rather than a stack of noise.
if BODY=$(sigma_cli api connections lookup \
    --params "{\"connectionId\":\"$CONN\"}" \
    --json "{\"path\":$PATH_JSON}" -f json 2>&1); then
  printf '%s' "$BODY" | PATHS="$PATH_JSON" python3 -c "
import sys, json, os
d = json.load(sys.stdin)
out = {'kind': d.get('kind'), 'inodeId': d.get('inodeId'), 'url': d.get('url'),
       'path': json.loads(os.environ['PATHS'])}
json.dump(out, sys.stdout, indent=2); print()
"
else
  printf '%s' "$BODY" | python3 -c "
import sys, json
# The CLI prints a JSON error object AND a trailing 'error[api]: …' line, so a plain
# json.loads() over the whole thing fails; decode just the leading value.
raw = sys.stdin.read().lstrip()
try:
    d, _ = json.JSONDecoder().raw_decode(raw)
except ValueError:
    d = {'message': raw.strip()[:400]}
json.dump({'error': True, 'code': d.get('code'), 'message': d.get('message')},
          sys.stdout, indent=2); print()
"
  exit 1
fi
