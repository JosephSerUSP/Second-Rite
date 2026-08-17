#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("branch_hygiene", HERE / "branch_hygiene.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def run(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode != 0:
        raise AssertionError(f"command failed ({p.returncode}): {' '.join(args)}\n{p.stdout}\n{p.stderr}")
    return p


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(cwd, "git", *args, check=check)


class BranchHygieneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="branch-hygiene-test-"))
        self.origin = self.tmp / "origin.git"
        self.seed = self.tmp / "seed"
        self.worker = self.tmp / "worker"
        git(self.tmp, "init", "--bare", "-q", str(self.origin))
        git(self.origin, "symbolic-ref", "HEAD", "refs/heads/main")
        git(self.tmp, "init", "-q", "-b", "main", str(self.seed))
        git(self.seed, "config", "user.email", "test@example.com")
        git(self.seed, "config", "user.name", "Branch Hygiene Test")
        (self.seed / "base.txt").write_text("base\n", encoding="utf-8")
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-qm", "base")
        git(self.seed, "remote", "add", "origin", str(self.origin))
        git(self.seed, "push", "-q", "-u", "origin", "main")
        git(self.tmp, "clone", "-q", str(self.origin), str(self.worker))
        git(self.worker, "switch", "-q", "main")
        git(self.worker, "config", "user.email", "test@example.com")
        git(self.worker, "config", "user.name", "Branch Hygiene Test")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def push_branch(self, name: str) -> None:
        git(self.seed, "push", "-q", "-u", "origin", f"HEAD:{name}")

    def refresh(self) -> None:
        mod.refresh(self.worker, "origin")

    def classify(self, branch: str):
        return mod.classify(
            self.worker,
            "refs/remotes/origin/main",
            f"refs/remotes/origin/{branch}",
            branch,
        )

    def test_literal_ancestor_is_landed(self) -> None:
        git(self.seed, "switch", "-qc", "ancestor")
        (self.seed / "ancestor.txt").write_text("landed\n", encoding="utf-8")
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-qm", "ancestor work")
        self.push_branch("ancestor")
        git(self.seed, "switch", "-q", "main")
        git(self.seed, "merge", "-q", "--ff-only", "ancestor")
        git(self.seed, "push", "-q", "origin", "main")
        self.refresh()
        self.assertEqual(mod.LANDED, self.classify("ancestor").category)

    def test_multi_commit_squash_landed_is_content_represented(self) -> None:
        git(self.seed, "switch", "-qc", "squash")
        base = git(self.seed, "merge-base", "main", "squash").stdout.strip()
        (self.seed / "squash-a.txt").write_text("a\n", encoding="utf-8")
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-qm", "squash a")
        (self.seed / "squash-b.txt").write_text("b\n", encoding="utf-8")
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-qm", "squash b")
        tip = git(self.seed, "rev-parse", "HEAD").stdout.strip()
        self.push_branch("squash")
        git(self.seed, "switch", "-q", "main")
        patch = git(self.seed, "diff", f"{base}..{tip}").stdout
        p = subprocess.run(
            ["git", "apply"],
            cwd=self.seed,
            text=True,
            input=patch,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(0, p.returncode, p.stderr)
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-qm", "squash landed")
        (self.seed / "later-main.txt").write_text("later\n", encoding="utf-8")
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-qm", "later main")
        git(self.seed, "push", "-q", "origin", "main")
        self.refresh()
        result = self.classify("squash")
        self.assertEqual(mod.LANDED, result.category)
        self.assertIn("virtual merge contributes no tree change", result.reason)
        # git-cherry is not a complete squash proof: one squash commit is not
        # patch-id equivalent to either original commit, although the total tree
        # contribution is already on main.
        cherry = git(self.worker, "cherry", "origin/main", "origin/squash").stdout
        self.assertIn("+", cherry)
        self.assertNotEqual("empty", result.three_dot_stat)

    def test_unique_file_is_unmerged(self) -> None:
        git(self.seed, "switch", "-qc", "unique-file")
        (self.seed / "unique.txt").write_text("unique\n", encoding="utf-8")
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-qm", "unique file")
        self.push_branch("unique-file")
        self.refresh()
        self.assertEqual(mod.UNMERGED, self.classify("unique-file").category)

    def test_modified_content_is_unmerged(self) -> None:
        git(self.seed, "switch", "-q", "main")
        (self.seed / "shared.txt").write_text("shared\n", encoding="utf-8")
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-qm", "shared base")
        git(self.seed, "push", "-q", "origin", "main")
        git(self.seed, "switch", "-qc", "modified")
        (self.seed / "shared.txt").write_text("shared\nbranch addition\n", encoding="utf-8")
        git(self.seed, "commit", "-qam", "modify shared")
        self.push_branch("modified")
        self.refresh()
        self.assertEqual(mod.UNMERGED, self.classify("modified").category)

    def test_conflicting_content_needs_review(self) -> None:
        git(self.seed, "switch", "-q", "main")
        (self.seed / "conflict.txt").write_text("base\n", encoding="utf-8")
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-qm", "conflict base")
        git(self.seed, "push", "-q", "origin", "main")
        git(self.seed, "switch", "-qc", "conflict")
        (self.seed / "conflict.txt").write_text("branch\n", encoding="utf-8")
        git(self.seed, "commit", "-qam", "branch conflict")
        self.push_branch("conflict")
        git(self.seed, "switch", "-q", "main")
        (self.seed / "conflict.txt").write_text("main\n", encoding="utf-8")
        git(self.seed, "commit", "-qam", "main conflict")
        git(self.seed, "push", "-q", "origin", "main")
        self.refresh()
        self.assertEqual(mod.REVIEW, self.classify("conflict").category)

    def test_stale_remote_main_can_change_answer_but_default_refresh_fixes_it(self) -> None:
        git(self.seed, "switch", "-qc", "stale-case")
        (self.seed / "stale.txt").write_text("eventually landed\n", encoding="utf-8")
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-qm", "stale branch")
        self.push_branch("stale-case")
        self.refresh()
        stale_main = git(self.worker, "rev-parse", "origin/main").stdout.strip()
        self.assertEqual(mod.UNMERGED, self.classify("stale-case").category)

        git(self.seed, "switch", "-q", "main")
        git(self.seed, "merge", "-q", "--ff-only", "stale-case")
        git(self.seed, "push", "-q", "origin", "main")
        self.assertEqual(stale_main, git(self.worker, "rev-parse", "origin/main").stdout.strip())
        self.assertEqual(mod.UNMERGED, self.classify("stale-case").category)
        self.refresh()
        fresh_main = git(self.worker, "rev-parse", "origin/main").stdout.strip()
        self.assertNotEqual(stale_main, fresh_main)
        self.assertEqual(mod.LANDED, self.classify("stale-case").category)

    def test_report_names_exact_main_sha_and_never_softens_unsafe_categories(self) -> None:
        git(self.seed, "switch", "-qc", "report-unique")
        (self.seed / "report-unique.txt").write_text("unique\n", encoding="utf-8")
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-qm", "report unique")
        self.push_branch("report-unique")
        self.refresh()
        main_sha = git(self.worker, "rev-parse", "origin/main").stdout.strip()
        result = self.classify("report-unique")
        report = mod.render_report("origin/main", main_sha, [result], "2026-08-17T00:00:00Z")
        self.assertIn(main_sha, report)
        self.assertIn(mod.UNMERGED, report)
        self.assertIn("Two-dot", report)
        self.assertIn("Three-dot", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
