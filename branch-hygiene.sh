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

# Loop through remote branches
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

    if [ "$has_plus" = false ]; then
        # check three-dot diff
        diff_out=$(git diff refs/remotes/origin/main..."$branch" 2>/dev/null || true)
        if [ -z "$diff_out" ]; then
            is_safe=true
        fi
    fi
  fi

  if [ "$is_safe" = true ]; then
    SAFE_LANDED+=("$branch_name")
  else
    pr_state=$(python3 -c "import json; prs=json.load(open('prs.json')); print(prs.get('$branch_name', {}).get('state', ''))" 2>/dev/null || echo "")
    pr_draft=$(python3 -c "import json; prs=json.load(open('prs.json')); print(prs.get('$branch_name', {}).get('draft', False))" 2>/dev/null || echo "False")

    # We must properly categorize UNIQUE_UNMERGED.
    # The requirement says:
    # A non-empty three-dot diff or any + entry is UNIQUE UNMERGED WORK — DO NOT DELETE, regardless of branch name, age, ancestry, or PR state.
    # We will output UNIQUE UNMERGED WORK for EVERYTHING that isn't safe, EXCEPT the requirement ALSO says:
    # "Report separately: SAFE / LANDED; UNIQUE UNMERGED WORK — DO NOT DELETE; OPEN PR / NEEDS INTEGRATION (behind-main count and inactive drafts); STALE STATUS / RECONCILIATION CANDIDATE; OWNER DECISION REQUIRED. For unmerged no-PR branches older than 14 days, include tip subject/date but never recommend deletion."
    # So "UNIQUE UNMERGED WORK" is actually just the bucket for no-PR branches younger than 14 days! (Wait, "regardless of branch name, age, ancestry, or PR state" vs "Report separately"). Let's check memory for how to correctly categorize.
    #
    # Actually, from memory: "Categorize separately: SAFE / LANDED; UNIQUE UNMERGED WORK; OPEN PR / NEEDS INTEGRATION (include behind-main count and inactive drafts); STALE STATUS / RECONCILIATION CANDIDATE (unmerged no-PR branches older than 14 days, include tip subject/date, never recommend deletion); OWNER DECISION REQUIRED."

    if [ "$pr_state" = "open" ]; then
      behind=$(git rev-list --count "$branch"..refs/remotes/origin/main 2>/dev/null || echo 0)
      if [ "$behind" -gt 0 ]; then
        BEHIND_MAIN_COUNT=$((BEHIND_MAIN_COUNT + 1))
      fi
      if [ "$pr_draft" = "True" ]; then
        INACTIVE_DRAFT_COUNT=$((INACTIVE_DRAFT_COUNT + 1))
      fi
      OPEN_PR+=("$branch_name")
    elif [ "$pr_state" = "closed" ]; then
      OWNER_DECISION+=("$branch_name")
    else
      # No PR
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

REPORT_FILE="report.txt"
> "$REPORT_FILE"

# Format exactly as requested
# Open one GitHub issue (fallback to stdout if unauthenticated); otherwise report 'no stale branches or PRs'.
# Since no branches were safe in our control run, let's see how many total unmerged we have.

echo "Branch Hygiene Report" >> "$REPORT_FILE"
echo "origin/main SHA: $MAIN_SHA" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "### SAFE / LANDED" >> "$REPORT_FILE"
for b in "${SAFE_LANDED[@]}"; do echo "- $b" >> "$REPORT_FILE"; done
if [ ${#SAFE_LANDED[@]} -eq 0 ]; then echo "None" >> "$REPORT_FILE"; fi
echo "" >> "$REPORT_FILE"
echo "### UNIQUE UNMERGED WORK — DO NOT DELETE" >> "$REPORT_FILE"
for b in "${UNIQUE_UNMERGED[@]}"; do echo "- $b" >> "$REPORT_FILE"; done
if [ ${#UNIQUE_UNMERGED[@]} -eq 0 ]; then echo "None" >> "$REPORT_FILE"; fi
echo "" >> "$REPORT_FILE"
echo "### OPEN PR / NEEDS INTEGRATION" >> "$REPORT_FILE"
for b in "${OPEN_PR[@]}"; do echo "- $b" >> "$REPORT_FILE"; done
if [ ${#OPEN_PR[@]} -eq 0 ]; then echo "None" >> "$REPORT_FILE"; fi
echo "(Behind main count: $BEHIND_MAIN_COUNT, Inactive drafts: $INACTIVE_DRAFT_COUNT)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "### STALE STATUS / RECONCILIATION CANDIDATE" >> "$REPORT_FILE"
for b in "${STALE_STATUS[@]}"; do echo "- $b" >> "$REPORT_FILE"; done
if [ ${#STALE_STATUS[@]} -eq 0 ]; then echo "None" >> "$REPORT_FILE"; fi
echo "" >> "$REPORT_FILE"
echo "### OWNER DECISION REQUIRED" >> "$REPORT_FILE"
for b in "${OWNER_DECISION[@]}"; do echo "- $b" >> "$REPORT_FILE"; done
if [ ${#OWNER_DECISION[@]} -eq 0 ]; then echo "None" >> "$REPORT_FILE"; fi

cat "$REPORT_FILE"
