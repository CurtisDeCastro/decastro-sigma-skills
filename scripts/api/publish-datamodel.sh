#!/usr/bin/env bash
# Publish data model specs to Sigma — create a new data model, update an existing
# one, or GET the spec back. Mirrors publish-workbook.sh.
#
# Usage:
#   scripts/api/publish-datamodel.sh post     <spec-file>
#   scripts/api/publish-datamodel.sh put      <dataModelId> <spec-file>
#   scripts/api/publish-datamodel.sh get-spec <dataModelId> [--yaml]
#
# TRANSPORT: `sigma api data-models spec …`. The CLI owns credentials, refresh, base
# URL and headers. Specs over ARG_LIMIT fall back to curl with `sigma auth token`,
# because --json passes the body as a single argv entry (see _env.sh).
#
# `put` is a FULL replacement — anything omitted from the spec is dropped.
#
# No `delete` subcommand — deletion stays on the direct-curl path so it always hits
# the DELETE ask pattern in .claude/settings.json.
set -euo pipefail
source "$(dirname "$0")/_env.sh"

ARG_LIMIT=${ARG_LIMIT:-800000}

# dm_submit <create|update> <spec-file> [dataModelId]
dm_submit() {
  local op="$1" spec="$2" dm_id="${3:-}" size
  size=$(wc -c <"$spec" | tr -d ' ')
  if [ "$size" -le "$ARG_LIMIT" ]; then
    if [ -n "$dm_id" ]; then
      sigma_cli api data-models spec "$op" \
        --params "{\"dataModelId\":\"$dm_id\"}" --json "$(cat "$spec")"
    else
      sigma_cli api data-models spec "$op" --json "$(cat "$spec")"
    fi
    return
  fi
  echo "publish-datamodel: spec is ${size} bytes (> ARG_LIMIT ${ARG_LIMIT}) — using the" >&2
  echo "  curl fallback with \`sigma auth token\`; --json cannot carry a body this large." >&2
  if [ -n "$dm_id" ]; then
    sigma_curl -X PUT -H "Content-Type: application/json" \
      --data-binary "@$spec" "$SIGMA_BASE_URL/v2/dataModels/$dm_id/spec"
  else
    sigma_curl -X POST -H "Content-Type: application/json" \
      --data-binary "@$spec" "$SIGMA_BASE_URL/v2/dataModels/spec"
  fi
}

cmd="${1:-}"
case "$cmd" in
  post)
    spec="${2:?usage: publish-datamodel.sh post <spec-file>}"
    [ -f "$spec" ] || { echo "publish-datamodel: spec file not found: $spec" >&2; exit 2; }
    dm_submit create "$spec"
    ;;
  put)
    dm_id="${2:?usage: publish-datamodel.sh put <dataModelId> <spec-file>}"
    spec="${3:?usage: publish-datamodel.sh put <dataModelId> <spec-file>}"
    [ -f "$spec" ] || { echo "publish-datamodel: spec file not found: $spec" >&2; exit 2; }
    dm_submit update "$spec" "$dm_id"
    ;;
  get-spec)
    dm_id="${2:?usage: publish-datamodel.sh get-spec <dataModelId> [--yaml]}"
    if [ "${3:-}" = "--yaml" ]; then
      sigma_cli api data-models spec get --params "{\"dataModelId\":\"$dm_id\"}" --yaml
    else
      sigma_cli api data-models spec get --params "{\"dataModelId\":\"$dm_id\"}"
    fi
    ;;
  *)
    cat >&2 <<'USAGE'
usage:
  publish-datamodel.sh post     <spec-file>
  publish-datamodel.sh put      <dataModelId> <spec-file>   # FULL replacement
  publish-datamodel.sh get-spec <dataModelId> [--yaml]

Transport is the `sigma` CLI (`sigma api data-models spec …`).
USAGE
    exit 2
    ;;
esac
