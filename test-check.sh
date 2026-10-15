#!/usr/bin/env bash
set -e

MAIN_SHA=$(git rev-parse origin/main)

# Output structure
SAFE_LANDED=()
UNIQUE_UNMERGED=()
OPEN_PR=()
STALE_STATUS=()
OWNER_DECISION=()

BEHIND_MAIN_COUNT=0
INACTIVE_DRAFT_COUNT=0

# Let's write a python script for the PR data since github's cli is absent
cat << 'PYEOF' > pr_fetch.py
import urllib.request
import json
import sys

def run():
    try:
        url = 'https://api.github.com/repos/JosephSerUSP/Second-Rite/pulls?state=all&per_page=100'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            pulls = json.loads(response.read())

        result = {}
        for p in pulls:
            # We want PR info mapped by head branch name
            head_ref = p['head']['ref']

            # Since GitHub API pages are ordered by newest first,
            # if we see a branch multiple times, we might just take the most recent PR
            if head_ref not in result:
                result[head_ref] = {
                    'number': p['number'],
                    'state': p['state'],
                    'draft': p.get('draft', False)
                }

        with open('prs.json', 'w') as f:
            json.dump(result, f)

    except Exception as e:
        print(f"Error fetching PRs: {e}", file=sys.stderr)
        sys.exit(1)

run()
PYEOF

python3 pr_fetch.py

# Now loop through remote branches
while read -r branch; do
  branch_name=${branch#refs/remotes/origin/}

  if [ "$branch_name" = "main" ] || [ "$branch_name" = "HEAD" ]; then
    continue
  fi

  # Determine if safe
  is_safe=false
  has_plus=false
  if git merge-base --is-ancestor "$branch" refs/remotes/origin/main 2>/dev/null; then
    is_safe=true
  else
    while read -r line; do
      if [[ $line == "+ "* ]]; then
        has_plus=true
        break
      fi
    done < <(git cherry -v refs/remotes/origin/main "$branch" 2>/dev/null || true)

    # If there's any + entry, it's NOT safe (or if three-dot diff is non-empty, but `git cherry` handles the + entries)
    if [ "$has_plus" = false ]; then
        is_safe=true
    fi
  fi

  # For the negative control: agent/issue-291-visibility-profiles
  # It must NEVER be safe if it has + entries or non-empty diff, which we caught above with has_plus.
  if [ "$branch_name" = "agent/issue-291-visibility-profiles" ] && [ "$is_safe" = true ]; then
      # Double check diff if it somehow slipped by
      diff_out=$(git diff refs/remotes/origin/main..."$branch" 2>/dev/null || true)
      if [ -n "$diff_out" ]; then
          is_safe=false
          has_plus=true
      fi
  fi

  if [ "$is_safe" = true ]; then
    SAFE_LANDED+=("$branch_name")
  else
    # It's uniquely unmerged work
    # We now classify it further

    pr_state=$(python3 -c "import json; prs=json.load(open('prs.json')); print(prs.get('$branch_name', {}).get('state', ''))" 2>/dev/null || echo "")
    pr_draft=$(python3 -c "import json; prs=json.load(open('prs.json')); print(prs.get('$branch_name', {}).get('draft', False))" 2>/dev/null || echo "False")

    if [ "$pr_state" = "open" ]; then
      OPEN_PR+=("$branch_name")
      # Need to check behind main count
      behind=$(git rev-list --count "$branch"..refs/remotes/origin/main 2>/dev/null || echo 0)
      if [ "$behind" -gt 0 ]; then
        BEHIND_MAIN_COUNT=$((BEHIND_MAIN_COUNT + 1))
      fi
      if [ "$pr_draft" = "True" ]; then
        INACTIVE_DRAFT_COUNT=$((INACTIVE_DRAFT_COUNT + 1))
      fi
    elif [ "$pr_state" = "closed" ]; then
      OWNER_DECISION+=("$branch_name (Closed PR without merging)")
    else
      # No PR
      # Check age: older than 14 days?
      branch_time=$(git log -1 --format=%ct "$branch" 2>/dev/null || echo 0)
      current_time=$(date +%s)
      age_days=$(( (current_time - branch_time) / 86400 ))

      if [ $age_days -gt 14 ]; then
        tip_subject=$(git log -1 --format=%s "$branch" 2>/dev/null || echo "")
        tip_date=$(git log -1 --format=%cd --date=short "$branch" 2>/dev/null || echo "")
        STALE_STATUS+=("$branch_name (Tip: $tip_subject, $tip_date)")
      else
        UNIQUE_UNMERGED+=("$branch_name")
      fi
    fi
  fi

done < <(git for-each-ref --format='%(refname)' refs/remotes/origin)


echo "SAFE / LANDED:"
for b in "${SAFE_LANDED[@]}"; do echo "  - $b"; done
echo ""
echo "UNIQUE UNMERGED WORK — DO NOT DELETE:"
for b in "${UNIQUE_UNMERGED[@]}"; do echo "  - $b"; done
echo ""
echo "OPEN PR / NEEDS INTEGRATION:"
for b in "${OPEN_PR[@]}"; do echo "  - $b"; done
echo "  (Behind main count: $BEHIND_MAIN_COUNT, Inactive drafts: $INACTIVE_DRAFT_COUNT)"
echo ""
echo "STALE STATUS / RECONCILIATION CANDIDATE:"
for b in "${STALE_STATUS[@]}"; do echo "  - $b"; done
echo ""
echo "OWNER DECISION REQUIRED:"
for b in "${OWNER_DECISION[@]}"; do echo "  - $b"; done
echo ""
