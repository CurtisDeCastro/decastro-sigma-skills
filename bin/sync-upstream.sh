#!/usr/bin/env bash
# Sync the skills we vendor from Sigma's official repo.
#
# This repository began as a fork of sigmacomputing/sigma-agent-skills, but it is NOT
# maintained by merging upstream: our README, CHANGELOG and the four plugin manifests
# have deliberately diverged, so `git merge upstream/main` conflicts on all of them
# every single time. Instead we vendor: copy specific skill directories, leave
# everything else alone.
#
#   bin/sync-upstream.sh            # report drift, change nothing
#   bin/sync-upstream.sh --apply    # copy upstream's version over ours
#
# Vendored skills are marked with a .upstream file naming their source.
set -euo pipefail
cd "$(dirname "$0")/.."

UPSTREAM_URL="https://github.com/sigmacomputing/sigma-agent-skills.git"
VENDORED=(sigma-api sigma-cli sigma-data-models)   # add a name here to start vendoring it
APPLY=0; [[ "${1:-}" == "--apply" ]] && APPLY=1

git remote get-url upstream >/dev/null 2>&1 || git remote add upstream "$UPSTREAM_URL"
echo "fetching upstream…"
# NOTE: the GitHub API is SAML-gated for the sigmacomputing org, but plain git is not.
git fetch -q upstream

drift=0
for s in "${VENDORED[@]}"; do
  if ! git cat-file -e "upstream/main:skills/$s" 2>/dev/null; then
    printf '  %-22s gone from upstream (kept locally)\n' "$s"; continue
  fi
  # compare content only — our own .upstream marker never exists upstream
  if [[ -d "skills/$s" ]] && git diff --quiet HEAD "upstream/main" \
       -- "skills/$s" ":(exclude)skills/$s/.upstream" 2>/dev/null; then
    printf '  %-22s up to date\n' "$s"; continue
  fi
  drift=1
  if [[ $APPLY -eq 1 ]]; then
    rm -rf "skills/$s"
    git archive "upstream/main" "skills/$s" | tar -x
    printf 'source: sigmacomputing/sigma-agent-skills (skills/%s)\nsynced: %s\n' \
      "$s" "$(git rev-parse --short upstream/main)" > "skills/$s/.upstream"
    printf '  %-22s UPDATED\n' "$s"
  else
    printf '  %-22s DRIFTED — run with --apply\n' "$s"
    git diff --stat HEAD "upstream/main" -- "skills/$s" ":(exclude)skills/$s/.upstream" | tail -1 | sed 's/^/      /'
  fi
done

echo
echo "skills only in this repo (never touched by sync):"
for d in skills/*/; do
  s=$(basename "$d")
  [[ " ${VENDORED[*]} " == *" $s "* ]] || printf '  %s\n' "$s"
done
[[ $APPLY -eq 0 && $drift -eq 1 ]] && echo && echo "run: bin/sync-upstream.sh --apply"
exit 0
