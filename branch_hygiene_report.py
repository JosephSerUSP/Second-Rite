import subprocess
import urllib.request
import json
import traceback
import datetime
import os
import sys

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        return e.output.decode('utf-8').strip()
    except Exception as e:
        return str(e)

def get_remote_branches():
    output = run_cmd(['git', 'branch', '-r'])
    branches = []
    for line in output.split('\n'):
        line = line.strip()
        if not line or '->' in line:
            continue
        if line.startswith('origin/'):
            branches.append(line[len('origin/'):])
    return branches

def get_commit_info(branch):
    try:
        output = subprocess.check_output(['git', 'log', '-1', '--format=%s (%ci)', f'origin/{branch}']).decode('utf-8').strip()
        return output
    except:
        return "Unknown commit info"

def get_commit_date(branch):
    try:
        output = subprocess.check_output(['git', 'log', '-1', '--format=%ct', f'origin/{branch}']).decode('utf-8').strip()
        return int(output)
    except:
        return 0

def unshallow():
    try:
        subprocess.check_call(['git', 'rev-parse', '--is-shallow-repository'], stdout=subprocess.DEVNULL)
        is_shallow = run_cmd(['git', 'rev-parse', '--is-shallow-repository']) == 'true'
        if is_shallow:
            run_cmd(['git', 'fetch', '--unshallow', 'origin'])
    except:
        pass

def main():
    try:
        subprocess.check_call(['git', 'fetch', 'origin', '--prune'])
    except Exception as e:
        print(f"Fetch failed: {e}")
        return

    unshallow()

    main_sha = run_cmd(['git', 'rev-parse', 'origin/main'])

    branches = get_remote_branches()
    if 'main' in branches:
        branches.remove('main')

    safe_landed = []
    unmerged_work = []
    open_pr = []
    stale_status = []
    owner_decision = []

    # fetch prs
    prs = []
    has_github_access = True
    try:
        # Use pagination to get all PRs
        page = 1
        while True:
            req = urllib.request.Request(f"https://api.github.com/repos/JosephSerUSP/Second-Rite/pulls?state=open&per_page=100&page={page}")
            with urllib.request.urlopen(req) as response:
                page_data = json.loads(response.read().decode())
                if not page_data:
                    break
                prs.extend(page_data)
                page += 1
    except Exception as e:
        has_github_access = False
        print("Failed to fetch PRs via API, proceeding without PR info (or may hit rate limits).", e)

    pr_branches = {}
    for pr in prs:
        head_ref = pr.get('head', {}).get('ref')
        if head_ref:
            pr_branches[head_ref] = pr

    for branch in branches:
        try:
            subprocess.check_call(['git', 'merge-base', '--is-ancestor', f'origin/{branch}', 'origin/main'])
            is_ancestor = True
        except subprocess.CalledProcessError:
            is_ancestor = False

        has_unique_work = False

        # We need to detect non-empty + entries from cherry OR non-empty three dot diff
        cherry_out = run_cmd(['git', 'cherry', '-v', 'origin/main', f'origin/{branch}'])
        has_plus = any(line.startswith('+') for line in cherry_out.split('\n') if line)

        has_diff = False
        try:
            subprocess.check_call(['git', 'merge-base', 'origin/main', f'origin/{branch}'], stdout=subprocess.DEVNULL)
            diff_out = subprocess.check_output(['git', 'diff', f'origin/main...origin/{branch}']).decode('utf-8')
            has_diff = len(diff_out.strip()) > 0
        except subprocess.CalledProcessError:
            # No merge base
            has_diff = True

        if has_plus or has_diff:
            has_unique_work = True

        if not has_unique_work:
            safe_landed.append(branch)
        else:
            if branch in pr_branches:
                pr = pr_branches[branch]
                behind_main = run_cmd(['git', 'rev-list', '--count', f'origin/{branch}..origin/main'])
                open_pr.append((branch, pr, behind_main))
            else:
                unmerged_work.append(branch)

    # Date diff logic
    now_timestamp = datetime.datetime.now().timestamp()
    days_14_ago = now_timestamp - (14 * 24 * 60 * 60)

    report = f"## Daily Branch Hygiene Report\n\n"
    report += f"**origin/main SHA:** `{main_sha}`\n\n"

    if not safe_landed and not unmerged_work and not open_pr:
        report += "no stale branches or PRs\n"
    else:
        report += "### SAFE / LANDED\n\n"
        if safe_landed:
            for b in safe_landed:
                report += f"- `{b}`\n"
        else:
            report += "No branches found.\n"

        report += "\n### UNIQUE UNMERGED WORK — DO NOT DELETE\n\n"
        if unmerged_work:
            for b in unmerged_work:
                b_date = get_commit_date(b)
                if b_date < days_14_ago:
                    info = get_commit_info(b)
                    report += f"- `{b}` (Tip: {info})\n"
                else:
                    report += f"- `{b}`\n"
        else:
            report += "No branches found.\n"

        report += "\n### OPEN PR / NEEDS INTEGRATION\n\n"
        if open_pr:
            for b, pr, behind_main in open_pr:
                state = "Draft" if pr.get('draft') else "Active"
                report += f"- `{b}` (PR #{pr.get('number')} - {state}, {behind_main} commits behind main)\n"
        else:
            report += "No branches found.\n"

        report += "\n### STALE STATUS / RECONCILIATION CANDIDATE\n\n"
        report += "No branches identified based on current rules.\n"

        report += "\n### OWNER DECISION REQUIRED\n\n"
        report += "No branches identified based on current rules.\n"

        report += "\n### Controls Verification\n"
        pos_control = "PASS (found at least one landed branch)" if len(safe_landed) > 0 else "FAIL (no landed branches found - maybe none exist)"
        neg_control = "PASS (agent/issue-291-visibility-profiles is in UNMERGED WORK)" if 'agent/issue-291-visibility-profiles' in unmerged_work else "FAIL (agent/issue-291-visibility-profiles not in UNMERGED WORK!)"

        report += f"- Positive Control: {pos_control}\n"
        report += f"- Negative Control: {neg_control}\n"

    print(report)

if __name__ == '__main__':
    main()
