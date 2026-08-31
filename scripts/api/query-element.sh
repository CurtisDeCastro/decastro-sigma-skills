#!/usr/bin/env bash
# Fetch the rendered data behind a published workbook element.
# Wraps Sigma's async export: `workbooks export` -> queryId -> `query download get`.
# Output goes to stdout — pipe to jq/python3.
#
# Usage:
#   scripts/api/query-element.sh <workbookId> <elementId> [format] [maxWaitSec]
#
# format defaults to "json" (was "csv" before the CLI move — see below). maxWaitSec
# defaults to 60, polling every 1s.
#
# Examples:
#   scripts/api/query-element.sh <wb> chart-monthly-revenue | jq '.[0]'
#   scripts/api/query-element.sh <wb> kpi-revenue csv
#
# TRANSPORT: `sigma api workbooks export` + `sigma api query download get`.
#
# ONE REAL CLI LIMITATION, verified 2026-08-11: the CLI parses every response as
# JSON, so a CSV download fails with
#   {"error":"internal","message":"Failed to parse response JSON: expected value at
#    line 1 column 1"}
# regardless of `-f csv`. JSON is therefore the default and the CLI-native path;
# `csv` falls back to curl with `sigma auth token`. If you only need the data, prefer
# json — it comes back already parsed.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"

wb_id="${1:?usage: query-element.sh <workbookId> <elementId> [format] [maxWaitSec]}"
el_id="${2:?usage: query-element.sh <workbookId> <elementId> [format] [maxWaitSec]}"
fmt="${3:-json}"
max_wait="${4:-60}"

if [ "$fmt" = "csv" ]; then
  # Fallback path: the CLI can't carry a non-JSON body. Same credentials, different pipe.
  source "$(dirname "$0")/_env.sh"
  resp=$(sigma_curl -X POST -H "Content-Type: application/json" \
    --data "{\"elementId\":\"$el_id\",\"format\":{\"type\":\"csv\"}}" \
    "$SIGMA_BASE_URL/v2/workbooks/$wb_id/export")
  query_id=$(printf '%s' "$resp" | python3 -c 'import sys,json; print(json.load(sys.stdin)["queryId"])')
  waited=0
  while :; do
    out=$(sigma_curl "$SIGMA_BASE_URL/v2/query/$query_id/download")
    # bash substring, not `head -c 1` — piping a multi-KB $out through head SIGPIPEs
    # printf under `set -o pipefail`. CSV starts with a column name; status JSON with '{'.
    if [ -n "$out" ] && [ "${out:0:1}" != "{" ]; then
      printf '%s' "$out"; exit 0
    fi
    waited=$((waited + 1))
    [ "$waited" -ge "$max_wait" ] && {
      echo "query-element: timed out after ${max_wait}s (queryId=$query_id)" >&2; exit 1; }
    sleep 1
  done
fi

REPO_ROOT="$repo_root" python3 -c '
import os, sys, json, time
sys.path.insert(0, os.path.join(os.environ["REPO_ROOT"], "scripts"))
from sigma_api import api, SigmaApiError

wb_id, el_id, fmt, max_wait = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])

d = api("workbooks", "export", params={"workbookId": wb_id},
        body={"elementId": el_id, "format": {"type": fmt}})
query_id = d.get("queryId")
if not query_id:
    sys.exit(f"query-element: no queryId in export response: {json.dumps(d)[:300]}")

# The download returns a status object until the job finishes, then the data itself.
for _ in range(max_wait):
    try:
        out = api("query", "download", "get", params={"queryId": query_id})
    except SigmaApiError as e:
        sys.exit(f"query-element: download failed: {e}")
    # A pending job yields literal `null`; a finished one yields the rows (or an object
    # carrying jobComplete). Anything else means keep waiting.
    if isinstance(out, list) or (isinstance(out, dict) and out.get("jobComplete") is True):
        json.dump(out, sys.stdout, indent=2); print()
        sys.exit(0)
    time.sleep(1)
sys.exit(f"query-element: timed out after {max_wait}s (queryId={query_id})")
' "$wb_id" "$el_id" "$fmt" "$max_wait"
