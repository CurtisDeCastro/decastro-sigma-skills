#!/usr/bin/env bash
# List folders in the org, optionally filtered by case-insensitive substring of name.
# Usage:  scripts/api/list-folders.sh [name-substring]
# Output: JSON array [{id, urlId, name, path}]
# Transport: `sigma api files list` via scripts/sigma_api.py (paginated). See _env.sh.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"

REPO_ROOT="$repo_root" NAME_FILTER="${1:-}" python3 -c '
import os, sys, json
sys.path.insert(0, os.path.join(os.environ["REPO_ROOT"], "scripts"))
from sigma_api import paginate

name_lc = os.environ.get("NAME_FILTER", "").lower().strip()
out = [{k: e.get(k) for k in ("id", "urlId", "name", "path")}
       for e in paginate("files", "list", params={"typeFilters": "folder"})
       if not name_lc or name_lc in (e.get("name") or "").lower()]
json.dump(out, sys.stdout, indent=2)
print()
'
