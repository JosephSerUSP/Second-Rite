#!/usr/bin/env bash
set -e

MAIN_SHA=$(git rev-parse origin/main)
echo "Origin main SHA: $MAIN_SHA"

SAFE_LANDED=()
UNIQUE_UNMERGED=()

for branch in $(git for-each-ref --format='%(refname)' refs/remotes/origin); do
  branch_name=${branch#refs/remotes/origin/}

  if [ "$branch_name" = "main" ]; then
    continue
  fi

  if git merge-base --is-ancestor "$branch" refs/remotes/origin/main 2>/dev/null; then
    SAFE_LANDED+=("$branch_name")
    continue
  fi

  # Check cherry -v
  has_plus=false
  while read -r line; do
    if [[ $line == "+ "* ]]; then
      has_plus=true
      break
    fi
  done < <(git cherry -v refs/remotes/origin/main "$branch" 2>/dev/null || true)

  if [ "$has_plus" = false ]; then
    SAFE_LANDED+=("$branch_name")
  else
    UNIQUE_UNMERGED+=("$branch_name")
  fi
done

echo "SAFE / LANDED:"
for b in "${SAFE_LANDED[@]}"; do echo "  - $b"; done
echo ""
echo "UNIQUE UNMERGED WORK — DO NOT DELETE:"
for b in "${UNIQUE_UNMERGED[@]}"; do echo "  - $b"; done
echo ""
