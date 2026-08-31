#!/usr/bin/env bash
# Publish workbook specs to Sigma — create, update, GET back the spec, fetch
# URL/metadata. Wraps the publish pipeline so callers don't compose eval/export
# chains by hand.
#
# Usage:
#   scripts/api/publish-workbook.sh verify   <spec-file>
#   scripts/api/publish-workbook.sh post     <spec-file>
#   scripts/api/publish-workbook.sh put      <workbook-id> <spec-file>
#   scripts/api/publish-workbook.sh get-spec <workbook-id> [--yaml]
#   scripts/api/publish-workbook.sh get-meta <workbook-id>
#   scripts/api/publish-workbook.sh assert   <workbook-id> <spec-file>
#
# TRANSPORT: the `sigma` CLI (`sigma api workbooks spec …`), not hand-rolled curl.
# The CLI owns credentials, refresh, base URL and the Accept header, so there is
# nothing to wire up here. Two concrete reasons this is not just a style rule:
#
#   1. Cloudflare. The raw-curl path gets an HTML "Just a moment..." challenge
#      (HTTP 403) on specs carrying large base64 SVG data-URIs — which is most of
#      image-heavy builds. Verified 2026-08-11: a spec that curl could
#      not verify returned a clean structured error list through the CLI.
#   2. The CLI returns parseable JSON instead of the multi-MB union-type dump the
#      raw endpoint emits on a shape mismatch (a 150 KB spec produced 10 MB).
#
# FALLBACK: `--json` passes the body as one argv entry, so a spec near ARG_MAX
# (`getconf ARG_MAX`, 1 MB on macOS) cannot go that way. Specs over $ARG_LIMIT
# fall back to curl with `sigma auth token` — still CLI-owned credentials, just a
# different pipe. Only our largest exemplar (cold-provisions, 1.05 MB) needs it.
#
# No `delete` subcommand here — deletion stays on the direct-curl path so it
# always hits the DELETE ask pattern in .claude/settings.json.
#
# `post` runs two checks first, because Sigma accepts broken specs:
#   1. scripts/validate-spec.py  — cross-reference + known-trap checks (local). BLOCKS.
#   2. POST /v2/workbooks/spec/verify — the server's structural validation. ADVISORY:
#      it has documented false negatives (see verify_spec below), so it blocks only on a
#      clean structured `errors[]` list and warns otherwise.
# Neither catches what the other does; see validate-spec.py's docstring.
# Set SKIP_VERIFY=1 to bypass stage 2 (offline work only).
#
# After a successful POST, run `assert` to confirm the build survived the
# round-trip — HTTP 200 is not proof. Unknown or wrong-shaped keys POST fine and
# then vanish from the GET-back.
set -euo pipefail
source "$(dirname "$0")/_env.sh"

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"

# Body size above which --json can't be used (one argv entry vs ARG_MAX). Leave
# headroom for the rest of argv + the environment.
ARG_LIMIT=${ARG_LIMIT:-800000}

# Upstream validators, referenced from the INSTALLED sigma-workbooks-cli skill — not
# vendored, because vendoring is what made our own spec docs go stale. Override with
# SIGMA_WB_SKILL if yours lives elsewhere.
SIGMA_WB_SKILL="${SIGMA_WB_SKILL:-$HOME/.claude/skills/sigma-workbooks-cli}"

# ref_scan <spec-file> — ADVISORY. Their regex scan for bare [Column] refs that don't
# resolve to a declared column of the same element (renders 'Unknown column').
#
# Deliberately non-blocking: it models neither control references nor an input-table's
# linked key columns, so it false-positives on both. Measured on a real spec
# (2026-08-13) all 4 flags were false: [DateGrain]/[ColorBy] are real controls, and
# [Revenue]/[Margin] bind through linked columns whose names come from the source
# element. `verify-built` below is the authoritative version of this check.
ref_scan() {
  local spec="$1" sh="$SIGMA_WB_SKILL/scripts/validate-spec.sh" out
  if [ ! -f "$sh" ]; then
    echo "publish-workbook: ref-scan SKIPPED — no validate-spec.sh at $sh" >&2
    echo "  (install the sigma-workbooks-cli skill, or set SIGMA_WB_SKILL)" >&2
    return 0
  fi
  out="$(bash "$sh" "$spec" 2>&1)" && { echo "ref-scan: no unresolved bare refs"; return 0; }
  echo "publish-workbook: ref-scan flagged possible unresolved bare refs (ADVISORY —" >&2
  echo "  it can't see controls or linked input-table columns, so check before fixing):" >&2
  printf '%s\n' "$out" | grep -E 'Element:|Column:|Unresolved bare refs:' | head -24 >&2
  return 0
}

# verify_built <workbook-id> — AUTHORITATIVE post-create check.
#
# CREATE is generous: it accepts specs whose column formulas don't resolve, then embeds
# the failure as a string literal in the compiled SQL ('Unknown column "[X]"',
# 'Circular column reference to [Y]') and renders those elements EMPTY. Only Sigma's
# compiler knows, so this asks the server per element. This is the check we could not
# build ourselves and the one that would have caught the render bugs that cost a session.
verify_built() {
  local wid="$1" sh="$SIGMA_WB_SKILL/scripts/verify-workbook.sh"
  if [ ! -f "$sh" ]; then
    echo "publish-workbook: verify-built SKIPPED — no verify-workbook.sh at $sh" >&2
    echo "  (install the sigma-workbooks-cli skill, or set SIGMA_WB_SKILL)" >&2
    return 0
  fi
  if [ -n "${SIGMA_PROFILE:-}" ]; then
    bash "$sh" "$wid" -p "$SIGMA_PROFILE"
  else
    bash "$sh" "$wid"
  fi
}

# spec_call <op> <spec-file> [params-json] — submit a spec body via the CLI.
#
# Routes to `sigma api workbooks spec <op>`, or to curl with the CLI's own token
# when the body is too large to pass as an argument. Prints the response body.
spec_call() {
  local op="$1" spec="$2" params="${3:-}" size
  size=$(wc -c <"$spec" | tr -d ' ')
  if [ "$size" -le "$ARG_LIMIT" ]; then
    if [ -n "$params" ]; then
      sigma_cli api workbooks spec "$op" --params "$params" --json "$(cat "$spec")"
    else
      sigma_cli api workbooks spec "$op" --json "$(cat "$spec")"
    fi
    return
  fi
  # Oversized body: same credentials, different pipe.
  echo "publish-workbook: spec is ${size} bytes (> ARG_LIMIT ${ARG_LIMIT}) — using the" >&2
  echo "  curl fallback with \`sigma auth token\`; --json cannot carry a body this large." >&2
  local url method="POST"
  case "$op" in
    create) url="$SIGMA_BASE_URL/v2/workbooks/spec" ;;
    verify) url="$SIGMA_BASE_URL/v2/workbooks/spec/verify" ;;
    update) method="PUT"
            url="$SIGMA_BASE_URL/v2/workbooks/$(printf '%s' "$params" \
                 | python3 -c 'import json,sys;print(json.load(sys.stdin)["workbookId"])')/spec" ;;
    *) echo "publish-workbook: no curl fallback for op '$op'" >&2; return 2 ;;
  esac
  sigma_curl -X "$method" -H "Content-Type: application/json" \
    --data-binary "@$spec" "$url"
}

# verify_spec <spec-file> — server-side structural validation, persists nothing.
#
# Three outcomes, because this endpoint has two very different failure channels:
#   0  valid            {"valid":true}
#   1  real rejection    {"valid":false,"errors":[{summary}]} — actionable, blocks
#   0  INCONCLUSIVE      a giant union-type dump, or a transport failure — warns only
#
# Going through the CLI makes the common case clean: it returns parseable JSON where
# raw curl returned either a Cloudflare challenge page (on specs with large base64
# SVGs) or a multi-MB union-type cascade listing every schema branch it tried — a
# 150 KB spec produced 10 MB, measured 2026-07-30. That dump also fires on specs that
# demonstrably work, so it can never be trusted as a rejection; we summarise it and
# continue, leaving validate-spec.py and the post-create `assert` as the checks that
# actually hold.
#
# Known false negative to read past: a `warehouse-agent` tool (Cortex Agent / Genie)
# yields {"valid":false,"errors":[{"summary":"invocable inodes are not supported by this
# host: ..."}]} even when the tool works.
verify_spec() {
  local spec="$1" body err size
  body="$(mktemp -t wbc-verify)"; err="$(mktemp -t wbc-verifyerr)"
  # Keep the streams apart: merging them buries spec_call's own diagnostics (the
  # oversized-body notice) inside what looks like a server response.
  spec_call verify "$spec" >"$body" 2>"$err" || true
  [ -s "$err" ] && cat "$err" >&2
  # The CLI reports HTTP errors on either stream depending on the failure; match both.
  cat "$err" >>"$body"; rm -f "$err"
  size=$(wc -c <"$body" | tr -d ' ')

  if grep -q '"valid": *true' "$body" 2>/dev/null; then
    printf 'spec/verify: valid\n'; rm -f "$body"; return 0
  fi

  if grep -q '"errors"' "$body" 2>/dev/null && [ "$size" -le 20000 ]; then
    if grep -q 'invocable inodes are not supported' "$body" 2>/dev/null; then
      echo "publish-workbook: spec/verify flagged a warehouse-agent tool — KNOWN FALSE" >&2
      echo "  NEGATIVE (it can't evaluate Cortex/Genie paths). Continuing." >&2
      head -c 300 "$body" >&2; echo >&2
      rm -f "$body"; return 0
    fi
    echo "publish-workbook: spec/verify rejected the spec:" >&2
    python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
for e in d.get("errors",[])[:12]: print("  -",e.get("summary",e), file=sys.stderr)' "$body" 2>/dev/null \
      || head -c 600 "$body" >&2
    rm -f "$body"; return 1
  fi

  echo "publish-workbook: spec/verify INCONCLUSIVE (${size} bytes; union-type dumps and" >&2
  echo "  WAF challenges both fire on working specs). Continuing; rely on" >&2
  echo "  validate-spec.py and the post-create \`assert\`." >&2
  head -c 300 "$body" >&2; echo >&2
  rm -f "$body"; return 0
}

cmd="${1:-}"
case "$cmd" in
  verify)
    spec="${2:?usage: publish-workbook.sh verify <spec-file>}"
    [ -f "$spec" ] || { echo "publish-workbook: spec file not found: $spec" >&2; exit 2; }
    # Three layers, cheapest first. They catch disjoint classes — see the header.
    python3 "$repo_root/scripts/validate-spec.py" "$spec"   # ours, BLOCKS
    ref_scan "$spec"                                        # theirs, ADVISORY
    verify_spec "$spec"                                     # server, blocks on clean errors
    ;;
  post)
    spec="${2:?usage: publish-workbook.sh post <spec-file>}"
    if [ ! -f "$spec" ]; then
      echo "publish-workbook: spec file not found: $spec" >&2
      exit 2
    fi
    python3 "$repo_root/scripts/validate-spec.py" "$spec"
    ref_scan "$spec"
    if [ "${SKIP_VERIFY:-0}" = "1" ]; then
      echo "publish-workbook: SKIP_VERIFY=1 — skipping server-side spec/verify" >&2
    else
      verify_spec "$spec"
    fi
    # Capture the response so the built workbook can be compile-checked, then echo it.
    created="$(spec_call create "$spec")"
    printf '%s\n' "$created"
    new_id="$(printf '%s' "$created" \
      | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("workbookId") or "")
except Exception: print("")' 2>/dev/null)"
    if [ -n "$new_id" ] && [ "${SKIP_VERIFY_BUILT:-0}" != "1" ]; then
      # HTTP 200 is not proof. Elements whose formulas do not resolve render EMPTY.
      verify_built "$new_id"
    fi
    ;;
  put)
    wb_id="${2:?usage: publish-workbook.sh put <workbook-id> <spec-file>}"
    spec="${3:?usage: publish-workbook.sh put <workbook-id> <spec-file>}"
    [ -f "$spec" ] || { echo "publish-workbook: spec file not found: $spec" >&2; exit 2; }
    # PUT is a FULL replacement — anything omitted from the spec is dropped.
    python3 "$repo_root/scripts/validate-spec.py" "$spec"
    ref_scan "$spec"
    if [ "${SKIP_VERIFY:-0}" = "1" ]; then
      echo "publish-workbook: SKIP_VERIFY=1 — skipping server-side spec/verify" >&2
    else
      verify_spec "$spec"
    fi
    spec_call update "$spec" "{\"workbookId\":\"$wb_id\"}"
    [ "${SKIP_VERIFY_BUILT:-0}" = "1" ] || verify_built "$wb_id"
    ;;
  verify-built)
    wb_id="${2:?usage: publish-workbook.sh verify-built <workbook-id>}"
    verify_built "$wb_id"
    ;;
  get-spec)
    wb_id="${2:?usage: publish-workbook.sh get-spec <workbook-id> [--yaml]}"
    if [ "${3:-}" = "--yaml" ]; then
      sigma_cli api workbooks spec get --params "{\"workbookId\":\"$wb_id\"}" --yaml
    else
      sigma_cli api workbooks spec get --params "{\"workbookId\":\"$wb_id\"}"
    fi
    ;;
  get-meta)
    wb_id="${2:?usage: publish-workbook.sh get-meta <workbook-id>}"
    sigma_cli api workbooks get --params "{\"workbookId\":\"$wb_id\"}"
    ;;
  assert)
    wb_id="${2:?usage: publish-workbook.sh assert <workbook-id> <spec-file>}"
    spec="${3:?usage: publish-workbook.sh assert <workbook-id> <spec-file>}"
    [ -f "$spec" ] || { echo "publish-workbook: spec file not found: $spec" >&2; exit 2; }
    tmp="$(mktemp -t wbc-getback)"
    trap 'rm -f "$tmp"' EXIT
    sigma_cli api workbooks spec get --params "{\"workbookId\":\"$wb_id\"}" > "$tmp"
    python3 "$repo_root/scripts/assert-spec.py" "$spec" "$tmp"
    ;;
  *)
    cat >&2 <<'USAGE'
usage:
  publish-workbook.sh verify       <spec-file>        # all three pre-submit checks
  publish-workbook.sh post         <spec-file>        # verify, create, compile-check
  publish-workbook.sh put          <workbook-id> <spec-file>   # same, FULL replace
  publish-workbook.sh verify-built <workbook-id>      # compile-check an existing workbook
  publish-workbook.sh get-spec     <workbook-id> [--yaml]
  publish-workbook.sh get-meta     <workbook-id>
  publish-workbook.sh assert       <workbook-id> <spec-file>   # did the build survive?

Four checks, disjoint failure classes, cheapest first:
  validate-spec.py   (ours)    envelope, layout<->element parity, agent wiring,
                               image form, plugin config, WAF trap        BLOCKS
  validate-spec.sh   (theirs)  bare [Column] refs that don't bind         ADVISORY
  spec/verify        (server)  structural validation, persists nothing    blocks on
                               a clean errors[] list
  verify-workbook.sh (theirs)  POST-CREATE: formulas that compile to
                               'Unknown column' and render empty          reports

SKIP_VERIFY=1 skips spec/verify; SKIP_VERIFY_BUILT=1 skips the post-create compile check.
Their two live in the installed sigma-workbooks-cli skill — override with SIGMA_WB_SKILL.

Transport is the `sigma` CLI (`sigma api workbooks spec …`). Specs over ARG_LIMIT
(default 800000 bytes) fall back to curl with `sigma auth token`.
USAGE
    exit 2
    ;;
esac
