#!/usr/bin/env bash
# Self-bootstrap for scripts in scripts/api/. Sourced (not executed).
#
# Auth comes from the `sigma` CLI — nothing else. No .env, no client-secret
# handling, no /tmp token cache. The CLI owns credentials (encrypted profiles)
# and refreshes its own token.
#
# After sourcing, the calling script always has:
#   sigma_cli        the CLI, invoked against $SIGMA_PROFILE if one is set
#
# and — unless SIGMA_ENV_CLI_ONLY=1 — also:
#   SIGMA_BASE_URL   from `sigma auth status` ("API host:" line)
#   SIGMA_API_TOKEN  from `sigma auth token`
#   sigma_curl       curl with the auth header + 401 retry
#
# Either var is skipped if already exported, so a caller can override it.
# Set SIGMA_PROFILE to target a non-default CLI profile (staging, another org).
#
# PREFER `sigma_cli api …` over sigma_curl. Every endpoint this repo touches has a
# CLI operation, the CLI owns credentials and refresh, and raw HTTP additionally
# trips a Cloudflare challenge on large image-heavy spec bodies (verified
# 2026-08-11). sigma_curl remains for DELETE and for spec bodies too large to pass
# as an argv entry — see publish-workbook.sh.
#
# Usage from a script in scripts/api/:
#   set -euo pipefail
#   SIGMA_ENV_CLI_ONLY=1 source "$(dirname "$0")/_env.sh"   # CLI only — no token fetch
#   source "$(dirname "$0")/_env.sh"                        # also base URL + token

# Don't impose `set -euo pipefail` here — inherit the caller's shell options.

# sigma_cli — invoke the CLI against the selected profile, if any.
sigma_cli() {
  if [ -n "${SIGMA_PROFILE:-}" ]; then
    command sigma -p "$SIGMA_PROFILE" "$@"
  else
    command sigma "$@"
  fi
}
# `export -f` is bash-only; under zsh it prints function bodies instead.
[ -n "${BASH_VERSION:-}" ] && export -f sigma_cli

if ! command -v sigma >/dev/null 2>&1; then
  cat >&2 <<'MISSING'
_env.sh: the `sigma` CLI is not on PATH.
  Install it, then authenticate:  sigma auth login
MISSING
  return 1 2>/dev/null || exit 1
fi

# CLI-only callers stop here: they never touch $SIGMA_API_TOKEN, so resolving it
# would just cost two extra CLI round-trips per invocation.
if [ "${SIGMA_ENV_CLI_ONLY:-0}" = "1" ]; then
  return 0 2>/dev/null || exit 0
fi

# 1. Base URL — parse the "API host:" line out of `sigma auth status`.
if [ -z "${SIGMA_BASE_URL:-}" ]; then
  if ! _sigma_status="$(sigma_cli auth status 2>&1)"; then
    echo "_env.sh: \`sigma auth status\` failed:" >&2
    printf '%s\n' "$_sigma_status" >&2
    echo "  Run \`sigma auth login\`, or set SIGMA_PROFILE to an authed profile." >&2
    return 1 2>/dev/null || exit 1
  fi
  _sigma_host="$(printf '%s\n' "$_sigma_status" \
    | awk -F': *' '/^API host:/ { print $2; exit }' \
    | tr -d '[:space:]')"
  if [ -z "$_sigma_host" ]; then
    echo "_env.sh: could not read the API host from \`sigma auth status\`:" >&2
    printf '%s\n' "$_sigma_status" >&2
    return 1 2>/dev/null || exit 1
  fi
  case "$_sigma_host" in
    http://*|https://*) SIGMA_BASE_URL="$_sigma_host" ;;
    *)                  SIGMA_BASE_URL="https://$_sigma_host" ;;
  esac
fi

# 2. Bearer token — the CLI mints and refreshes it.
if [ -z "${SIGMA_API_TOKEN:-}" ]; then
  SIGMA_API_TOKEN="$(sigma_cli auth token 2>/dev/null | tr -d '[:space:]')"
  if [ -z "$SIGMA_API_TOKEN" ]; then
    echo "_env.sh: \`sigma auth token\` returned nothing — run \`sigma auth login\`." >&2
    return 1 2>/dev/null || exit 1
  fi
fi

export SIGMA_BASE_URL SIGMA_API_TOKEN

# sigma_curl — wrap curl with auth header, Accept: application/json, and 401
# auto-retry. Use this from scripts/api/*.sh instead of raw curl for any call
# to the Sigma REST API.
#
# Usage:  sigma_curl [curl args...] <url>
# Output: response body to stdout (HTTP status suffix stripped).
# Exit:   0 if HTTP < 400, 1 otherwise.
#
# On HTTP 401, drops the in-shell token, re-asks the CLI for a fresh one, and
# retries the call once — covers a token that expired mid-run.
sigma_curl() {
  local _resp _body _status _retries=0
  while :; do
    _resp=$(curl -sS \
      -H "Authorization: Bearer $SIGMA_API_TOKEN" \
      -H "Accept: application/json" \
      -w '\nHTTP_STATUS:%{http_code}' \
      "$@")
    _status="${_resp##*HTTP_STATUS:}"
    _body="${_resp%HTTP_STATUS:*}"
    _body="${_body%$'\n'}"
    if [ "$_status" = "401" ] && [ "$_retries" -eq 0 ]; then
      unset SIGMA_API_TOKEN
      source "${BASH_SOURCE[0]}"
      _retries=1
      continue
    fi
    printf '%s' "$_body"
    [ "$_status" -lt 400 ] && return 0 || return 1
  done
}
[ -n "${BASH_VERSION:-}" ] && export -f sigma_curl

unset _sigma_status _sigma_host
true
