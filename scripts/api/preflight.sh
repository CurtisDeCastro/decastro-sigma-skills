#!/usr/bin/env bash
# Preflight: confirm the `sigma` CLI is installed and authenticated, and print
# the resolved profile / org / API host. Run this ONCE at the start of any
# session that will touch the Sigma API — it is the only auth check needed.
#
# Usage:
#   scripts/api/preflight.sh
#   SIGMA_PROFILE=staging scripts/api/preflight.sh
#
# Exit: 0 when authed; 1 when the CLI is missing or not logged in.
#
# Never prints the bearer token.
set -uo pipefail

if ! command -v sigma >/dev/null 2>&1; then
  echo "FAIL: \`sigma\` CLI not on PATH. Install it, then run \`sigma auth login\`." >&2
  exit 1
fi

if [ -n "${SIGMA_PROFILE:-}" ]; then
  status="$(sigma -p "$SIGMA_PROFILE" auth status 2>&1)"
else
  status="$(sigma auth status 2>&1)"
fi
rc=$?

if [ "$rc" -ne 0 ] || ! printf '%s' "$status" | grep -q '^Auth: *OK'; then
  echo "FAIL: sigma CLI is not authenticated." >&2
  printf '%s\n' "$status" >&2
  echo "  Run \`sigma auth login\` (or \`sigma auth login -p <profile>\` to refresh one)." >&2
  exit 1
fi

# Echo everything except the client-ID line; drop the token countdown noise.
printf '%s\n' "$status" | grep -vE '^(Client ID|Token):'
echo "OK: sigma CLI authenticated. scripts/api/*.sh will use this profile."
