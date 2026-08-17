#!/usr/bin/env python3
"""Conservative remote branch hygiene classifier.

A branch is mechanically deletion-safe only when merging it into the freshly
fetched main tree would contribute no content. Literal ancestry is a fast-path;
non-ancestor branches are checked with Git's real three-way merge machinery via
`git merge-tree --write-tree`.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import subprocess
import sys
from pathlib import Path
from typing import Iterable

LANDED = "LANDED / CONTENT REPRESENTED — SAFE TO DELETE"
UNMERGED = "UNMERGED CONTENT — DO NOT DELETE"
REVIEW = "NEEDS REVIEW / CANNOT DETERMINE — DO NOT DELETE"


@dataclasses.dataclass(frozen=True)
class Result:
    branch: str
    tip: str
    main_sha: str
    merge_base: str | None
    category: str
    reason: str
    three_dot_stat: str = ""
    two_dot_stat: str = ""


class GitError(RuntimeError):
    pass


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed with {proc.returncode}: {proc.stderr.strip()}"
        )
    return proc


def refresh(repo: Path, remote: str) -> None:
    # Force-update the complete remote-tracking namespace. This avoids trusting a
    # shallow/stale checkout's configured fetch refspec when deletion safety is at stake.
    refspec = f"+refs/heads/*:refs/remotes/{remote}/*"
    git(repo, "fetch", "--prune", "--no-tags", remote, refspec)


def resolve(repo: Path, ref: str) -> str:
    return git(repo, "rev-parse", "--verify", ref).stdout.strip()


def list_remote_branches(repo: Path, remote: str, main_branch: str) -> list[tuple[str, str]]:
    prefix = f"refs/remotes/{remote}/"
    proc = git(
        repo,
        "for-each-ref",
        "--format=%(refname:strip=3)%09%(objectname)",
        prefix,
    )
    rows: list[tuple[str, str]] = []
    for raw in proc.stdout.splitlines():
        if not raw.strip():
            continue
        branch, sha = raw.split("\t", 1)
        if branch in {"HEAD", main_branch}:
            continue
        rows.append((branch, sha))
    return sorted(rows)


def shortstat(repo: Path, *diff_args: str) -> str:
    return git(repo, "diff", "--shortstat", *diff_args).stdout.strip() or "empty"


def classify(repo: Path, main_ref: str, branch_ref: str, branch_name: str | None = None) -> Result:
    name = branch_name or branch_ref
    main_sha = resolve(repo, main_ref)
    tip = resolve(repo, branch_ref)

    ancestor = git(repo, "merge-base", "--is-ancestor", branch_ref, main_ref, check=False)
    if ancestor.returncode == 0:
        base = resolve(repo, branch_ref)
        return Result(
            branch=name,
            tip=tip,
            main_sha=main_sha,
            merge_base=base,
            category=LANDED,
            reason="branch tip is a literal ancestor of current main",
            three_dot_stat="empty (ancestry fast-path)",
            two_dot_stat=shortstat(repo, main_ref, branch_ref),
        )
    if ancestor.returncode not in (0, 1):
        return Result(name, tip, main_sha, None, REVIEW, "git merge-base --is-ancestor failed")

    base_proc = git(repo, "merge-base", main_ref, branch_ref, check=False)
    if base_proc.returncode != 0 or not base_proc.stdout.strip():
        return Result(name, tip, main_sha, None, REVIEW, "no reliable merge base")
    merge_base = base_proc.stdout.strip().splitlines()[0]

    three_dot = shortstat(repo, f"{main_ref}...{branch_ref}")
    two_dot = shortstat(repo, main_ref, branch_ref)

    merged = git(repo, "merge-tree", "--write-tree", main_ref, branch_ref, check=False)
    if merged.returncode != 0:
        detail = merged.stderr.strip() or "virtual merge reported conflicts or failed"
        return Result(
            name,
            tip,
            main_sha,
            merge_base,
            REVIEW,
            f"virtual merge was not clean: {detail}",
            three_dot,
            two_dot,
        )

    merged_lines = [line.strip() for line in merged.stdout.splitlines() if line.strip()]
    if not merged_lines:
        return Result(name, tip, main_sha, merge_base, REVIEW, "virtual merge returned no tree", three_dot, two_dot)
    merged_tree = merged_lines[0]
    main_tree = resolve(repo, f"{main_ref}^{{tree}}")

    if merged_tree == main_tree:
        return Result(
            name,
            tip,
            main_sha,
            merge_base,
            LANDED,
            "clean virtual merge contributes no tree change to current main",
            three_dot,
            two_dot,
        )

    contribution = shortstat(repo, main_tree, merged_tree)
    return Result(
        name,
        tip,
        main_sha,
        merge_base,
        UNMERGED,
        f"clean virtual merge would change current main ({contribution})",
        three_dot,
        two_dot,
    )


def render_report(main_ref: str, main_sha: str, results: Iterable[Result], generated_at: str) -> str:
    grouped = {LANDED: [], UNMERGED: [], REVIEW: []}
    for result in results:
        grouped[result.category].append(result)

    lines = [
        f"# Branch Hygiene Census — {generated_at}",
        "",
        f"Evaluated against freshly fetched `{main_ref}` at **`{main_sha}`**.",
        "",
        "## Safety rule",
        "",
        "This report never infers deletion safety from age, PR state, ahead/behind counts, or branch naming.",
        "",
        "- **Two-dot** `git diff A B` compares the two endpoint trees. It is useful evidence, but later unrelated work on main makes it too strict to prove squash landing.",
        "- **Three-dot** `git diff A...B` compares the merge base to B. It describes the branch delta, but remains non-empty after a normal squash merge, so it is not a landed test.",
        "- The classifier first accepts literal ancestry. Otherwise it performs `git merge-tree --write-tree <main> <branch>` using Git's merge base. Only when that clean virtual merge produces exactly the current main tree is the branch **CONTENT REPRESENTED**.",
        "- Squash-landed and rebased branches therefore do not need ancestral identity. They are judged by what their content would contribute to the current main tree. A branch whose history was rewritten but still carries unique content remains unsafe.",
        "- A clean virtual merge that changes the main tree is **UNMERGED CONTENT**. A conflict, missing merge base, or Git error is **NEEDS REVIEW / CANNOT DETERMINE**. Neither may be deleted from this report.",
        "",
    ]

    for category in (LANDED, UNMERGED, REVIEW):
        rows = grouped[category]
        lines.extend([f"## {category}", ""])
        if not rows:
            lines.extend(["No branches.", ""])
            continue
        for r in rows:
            base = r.merge_base[:12] if r.merge_base else "n/a"
            lines.extend(
                [
                    f"- `{r.branch}` — tip `{r.tip[:12]}`, merge base `{base}`",
                    f"  - {r.reason}",
                    f"  - three-dot branch delta: {r.three_dot_stat}",
                    f"  - two-dot endpoint delta: {r.two_dot_stat}",
                ]
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--main-branch", default="main")
    parser.add_argument("--no-fetch", action="store_true", help="test-only: classify existing refs without refreshing remote state")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    if not args.no_fetch:
        refresh(repo, args.remote)

    main_ref = f"refs/remotes/{args.remote}/{args.main_branch}"
    try:
        main_sha = resolve(repo, main_ref)
    except GitError as exc:
        print(f"ERROR: cannot resolve freshly fetched main: {exc}", file=sys.stderr)
        return 2

    results = [
        classify(repo, main_ref, f"refs/remotes/{args.remote}/{branch}", branch)
        for branch, _ in list_remote_branches(repo, args.remote, args.main_branch)
    ]
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    report = render_report(f"{args.remote}/{args.main_branch}", main_sha, results, generated_at)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
