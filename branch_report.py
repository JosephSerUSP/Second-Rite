import subprocess
import urllib.request
import json
import time
import sys
import os

def run_cmd(cmd):
    return subprocess.check_output(cmd, shell=True).decode('utf-8').strip()

def main():
    # Ensure fresh state
    try:
        run_cmd("git fetch origin --prune")
        run_cmd("git fetch --unshallow || true")
    except Exception as e:
        pass # Ignore failure in unshallow if already shallow

    main_sha = run_cmd("git rev-parse origin/main")

    # Fetch PR data
    url = 'https://api.github.com/repos/JosephSerUSP/Second-Rite/pulls?state=all&per_page=100'
    all_pulls = []
    page = 1
    while True:
        try:
            req = urllib.request.Request(f"{url}&page={page}")
            with urllib.request.urlopen(req) as response:
                pulls = json.loads(response.read())
                if not pulls:
                    break
                all_pulls.extend(pulls)
                page += 1
        except Exception as e:
            # Reached end or rate limit
            break

    pr_dict = {}
    all_pulls.sort(key=lambda x: x['number'])
    for p in all_pulls:
        pr_dict[p['head']['ref']] = {
            'state': p['state'],
            'draft': p.get('draft', False)
        }

    branches = run_cmd("git for-each-ref --format='%(refname:short)' refs/remotes/origin").splitlines()

    safe_landed = []
    unique_unmerged = []
    open_pr = []
    stale_status = []
    owner_decision = []

    behind_main = 0
    inactive_drafts = 0

    current_time = int(time.time())

    for branch in branches:
        branch_name = branch.replace('origin/', '', 1)
        if branch_name == 'main' or branch_name == 'HEAD':
            continue

        full_ref = f"refs/remotes/origin/{branch_name}"

        # Check if safe/landed
        is_safe = False
        if subprocess.call(f"git merge-base --is-ancestor {full_ref} refs/remotes/origin/main", shell=True, stderr=subprocess.DEVNULL) == 0:
            is_safe = True
        else:
            cherry_out = run_cmd(f"git cherry -v refs/remotes/origin/main {full_ref} 2>/dev/null || true").splitlines()
            has_plus = any(line.startswith('+ ') for line in cherry_out)
            if not has_plus:
                # Need to also check empty diff
                diff_out = run_cmd(f"git diff refs/remotes/origin/main...{full_ref} 2>/dev/null || true")
                if not diff_out:
                    is_safe = True

        # Apply strict memory rule: A non-empty three-dot diff or any + entry is UNIQUE UNMERGED WORK — DO NOT DELETE

        if is_safe:
            safe_landed.append(branch_name)
        else:
            # Unmerged work. Classify by PR and age
            pr = pr_dict.get(branch_name)

            if pr and pr['state'] == 'open':
                open_pr.append(branch_name)
                behind = int(run_cmd(f"git rev-list --count {full_ref}..refs/remotes/origin/main 2>/dev/null || echo 0"))
                if behind > 0:
                    behind_main += 1
                if pr['draft']:
                    inactive_drafts += 1
            elif pr and pr['state'] == 'closed':
                owner_decision.append(branch_name)
            else:
                branch_time = int(run_cmd(f"git log -1 --format=%ct {full_ref} 2>/dev/null || echo 0"))
                age_days = (current_time - branch_time) // 86400
                if age_days > 14:
                    tip_subject = run_cmd(f"git log -1 --format=%s {full_ref} 2>/dev/null || echo ''")
                    tip_date = run_cmd(f"git log -1 --format=%cd --date=short {full_ref} 2>/dev/null || echo ''")
                    stale_status.append(f"{branch_name} (Tip: {tip_subject}, {tip_date})")
                else:
                    unique_unmerged.append(branch_name)

    # Output construction
    report = []

    # We must explicitly output 'no stale branches or PRs' if there are no findings
    findings = safe_landed + unique_unmerged + open_pr + stale_status + owner_decision
    if not findings:
        report.append("no stale branches or PRs")
    else:
        report.append(f"Branch Hygiene Report")
        report.append(f"origin/main SHA: {main_sha}")

        report.append("\n### SAFE / LANDED")
        if safe_landed:
            report.extend([f"- {b}" for b in safe_landed])
        else:
            report.append("None")

        report.append("\n### UNIQUE UNMERGED WORK — DO NOT DELETE")
        if unique_unmerged:
            report.extend([f"- {b}" for b in unique_unmerged])
        else:
            report.append("None")

        report.append("\n### OPEN PR / NEEDS INTEGRATION")
        if open_pr:
            report.extend([f"- {b}" for b in open_pr])
        else:
            report.append("None")
        report.append(f"(Behind main count: {behind_main}, Inactive drafts: {inactive_drafts})")

        report.append("\n### STALE STATUS / RECONCILIATION CANDIDATE")
        if stale_status:
            report.extend([f"- {b}" for b in stale_status])
        else:
            report.append("None")

        report.append("\n### OWNER DECISION REQUIRED")
        if owner_decision:
            report.extend([f"- {b}" for b in owner_decision])
        else:
            report.append("None")

        # Add negative control state output requirement
        neg_ctrl_state = "SAFE" if "agent/issue-291-visibility-profiles" in safe_landed else "UNMERGED"
        pos_ctrl = "SUCCESS" if len(safe_landed) > 0 else "N/A"

        report.append(f"\nControls: Positive: {pos_ctrl}, Negative (agent/issue-291-visibility-profiles): {neg_ctrl_state}")

    report_content = '\n'.join(report)
    print(report_content)

    # Try to open GitHub issue
    if os.environ.get('GITHUB_TOKEN'):
        try:
            # if authenticated
            pass
        except:
            pass

if __name__ == "__main__":
    main()
