"""delegate -- hand a bounded job to a cheap external agent, in isolation.

    python tools/delegate/delegate.py run doc-currency --task-file task.md
    python tools/delegate/delegate.py run doc-currency --task "..." --dry-run
    python tools/delegate/delegate.py ledger
    python tools/delegate/delegate.py clean doc-currency

The expensive agent stays the epistemic authority; this buys labour, not
judgement. Every run happens in its own `.codex-work-<slug>/` git worktree on a
`codex/<slug>` branch, so a delegate can never write to the primary checkout --
which matters here specifically, because the editor dev server live-writes
`data/*.json` and a stray `sed -i` converts CRLF to LF across a whole file.

What this does NOT do: judge the result. `run` prints the raw diff and the raw
agent transcript. Read them. A cheap model reporting "all gates pass" is a
sentence it generated, not an observation it made.

The real spend ceiling is the cap you set on the provider's billing page.
`--timeout` bounds one run's wall clock; it is not a token budget, and this
script deliberately does not pretend otherwise.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
LEDGER = HERE / "ledger.jsonl"

# Tracked, not gitignored, and deliberately so: this file is the only record of
# which task classes survive delegation. Accumulated evidence that lives under a
# gitignored directory gets destroyed by routine cleanup -- that has already
# happened twice in this repo with the asset-gen ratings store.

DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_TIMEOUT = 1800


def run(cmd, cwd=None, timeout=None, capture=True):
    return subprocess.run(
        cmd, cwd=cwd, timeout=timeout, text=True, encoding="utf-8",
        errors="replace", capture_output=capture,
    )


def git(*args, cwd=ROOT, check=True):
    proc = run(["git", *args], cwd=cwd)
    if check and proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{proc.stderr.strip()}")
    return proc.stdout.strip()


def codex_binary():
    """Locate the Codex CLI, which is a different thing from the Codex app.

    The app installs ~/.codex/ (sessions, skills, plugins) without putting an
    executable on PATH. Only the CLI gives a scriptable `codex exec`.
    """
    found = shutil.which("codex")
    if found:
        return found
    raise SystemExit(
        "codex CLI not found on PATH.\n"
        "  The Codex *app* (~/.codex/) does not provide a scriptable entry point;\n"
        "  the CLI is a separate install:  npm install -g @openai/codex\n"
        "  Then set OPENAI_API_KEY in your environment."
    )


def agent_env():
    """Environment for the delegate, with a Windows-only key resolution step.

    A process inherits its environment when it starts, so a variable set after
    this session began is invisible here even though it is correctly persisted.
    Rather than requiring a restart, read the persisted User-scope value and
    inject it. The value is passed straight into the child's environment and is
    never printed, logged, or written to the ledger.
    """
    env = dict(os.environ)
    if env.get("OPENAI_API_KEY") or os.name != "nt":
        return env
    probe = run([
        "powershell", "-NoProfile", "-Command",
        '[System.Environment]::GetEnvironmentVariable("OPENAI_API_KEY","User")',
    ])
    value = probe.stdout.strip()
    if value:
        env["OPENAI_API_KEY"] = value
    return env


def worktree_path(slug):
    return ROOT / f".codex-work-{slug}"


def cmd_run(args):
    slug = args.slug
    branch = f"codex/{slug}"
    wt = worktree_path(slug)

    if args.task_file:
        task = Path(args.task_file).read_text(encoding="utf-8")
    elif args.task:
        task = args.task
    else:
        raise SystemExit("provide --task or --task-file")

    binary = codex_binary() if not args.dry_run else "<codex>"

    if wt.exists():
        raise SystemExit(
            f"{wt} already exists. Inspect it, then:  "
            f"python tools/delegate/delegate.py clean {slug}"
        )

    existing = git("branch", "--list", branch)
    if existing:
        raise SystemExit(f"branch {branch} already exists; pick another slug or delete it")

    base_sha = git("rev-parse", args.base)
    print(f"base   {args.base} @ {base_sha[:8]}")
    print(f"branch {branch}")
    print(f"tree   {wt}")
    print(f"model  {args.model}")

    if args.dry_run:
        print(f"sandbox {args.sandbox}")
        print("\n--- dry run, nothing created ---")
        print(f"would run: {binary} exec -m {args.model} -s {args.sandbox} "
              f"-C {wt} --add-dir {ROOT / '.git' / 'worktrees' / wt.name} -"
              f"   (task on stdin, {len(task)} chars)")
        return 0

    git("worktree", "add", "-b", branch, str(wt), base_sha)

    # -s workspace-write is the load-bearing flag, not a default worth trusting.
    # The user's ~/.codex/config.toml sets sandbox_mode = "danger-full-access",
    # which is fine for a human driving Codex interactively and completely wrong
    # for an unattended delegate: with full disk access the worktree stops being
    # isolation and becomes merely a starting directory, since nothing prevents
    # an absolute-path write straight into the primary checkout. Passing it
    # explicitly overrides the config per run and leaves their setup alone.
    #
    # The prompt goes over stdin ("-") rather than argv: task briefs are long,
    # and Windows caps a command line around 32k characters.
    # A linked worktree keeps its index and HEAD in the MAIN repo's
    # .git/worktrees/<name>/, outside the worktree directory -- so under
    # workspace-write the agent can edit files but cannot commit them
    # (Permission denied on index.lock). Granting exactly that one directory
    # restores committing without widening the sandbox to the whole checkout.
    gitdir = ROOT / ".git" / "worktrees" / wt.name

    cmd = [
        binary, "exec",
        "-m", args.model,
        "-s", args.sandbox,
        "-C", str(wt),
        "--add-dir", str(gitdir),
        "-",
    ]

    # The wrapper buffers the child's output until it exits, so this is the only
    # way to observe a run in flight. Printed before launch, not after.
    print("\nwatch it live:  python tools/delegate/watch.py")

    started = time.time()
    timed_out = False
    try:
        proc = subprocess.run(
            cmd, cwd=str(wt), input=task, env=agent_env(),
            text=True, encoding="utf-8", errors="replace",
            capture_output=True, timeout=args.timeout,
        )
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\n[delegate] timed out after {args.timeout}s"
        code = -1
    duration = time.time() - started

    log = wt / "delegate-transcript.txt"
    log.write_text(stdout + "\n---stderr---\n" + stderr, encoding="utf-8")

    print(f"\n--- agent transcript ({len(stdout)} chars) -> {log} ---")
    print(stdout[-4000:] if len(stdout) > 4000 else stdout)
    if stderr.strip():
        print(f"--- stderr ---\n{stderr[-2000:]}")

    changed = git("status", "--porcelain", cwd=wt, check=False)
    diffstat = run(["git", "diff", "--stat", base_sha], cwd=wt).stdout
    print(f"\n--- diff vs {base_sha[:8]} ---\n{diffstat or '(no committed changes)'}")
    if changed:
        print(f"--- uncommitted in worktree ---\n{changed}")

    crlf = crlf_check(wt, base_sha)
    if crlf:
        print("\n!! line-ending damage suspected in:")
        for name in crlf:
            print(f"   {name}")
        print("   (diff shrinks dramatically under --ignore-cr-at-eol: a tool "
              "rewrote CRLF as LF rather than making the small edit it claims)")

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "slug": slug,
        "branch": branch,
        "model": args.model,
        "sandbox": args.sandbox,
        "base": base_sha,
        "duration_s": round(duration, 1),
        "exit_code": code,
        "timed_out": timed_out,
        "task_chars": len(task),
        "transcript_chars": len(stdout),
        "files_changed": diffstat.strip().splitlines()[-1] if diffstat.strip() else "",
        "crlf_suspect": crlf,
        "verdict": None,
    }
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")

    print(f"\nledger += {slug}  ({duration:.0f}s, exit {code})")
    print("Set \"verdict\" on that ledger row once you have reviewed the diff -- "
          "the whole point is knowing later which task classes actually worked.")
    return 0 if code == 0 else 1


def crlf_check(wt, base_sha):
    """Flag files whose diff mostly vanishes when line endings are ignored.

    `sed -i` and similar silently normalise CRLF to LF on Windows, which turns a
    two-line edit into a whole-file rewrite. Comparing the two diffstats catches
    it before the change is reviewed as if it were real.
    """
    normal = run(["git", "diff", "--numstat", base_sha], cwd=wt).stdout
    ignored = run(["git", "diff", "--numstat", "--ignore-cr-at-eol", base_sha], cwd=wt).stdout

    def parse(text):
        out = {}
        for line in text.strip().splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and parts[0].isdigit():
                out[parts[2]] = int(parts[0]) + int(parts[1])
        return out

    a, b = parse(normal), parse(ignored)
    suspect = []
    for name, total in a.items():
        real = b.get(name, 0)
        if total >= 20 and real * 4 < total:
            suspect.append(f"{name}  ({total} lines changed, {real} ignoring CR)")

    # Whole-file rewrites are the loud failure; mixed endings are the quiet one.
    # An agent that edits individual lines with an LF-writing tool leaves a file
    # that is mostly CRLF with LF on exactly the lines it touched. The diffstat
    # looks perfectly normal, so the check above cannot see it.
    for name in a:
        f = wt / name
        try:
            raw = f.read_bytes()
        except OSError:
            continue
        crlf = raw.count(b"\r\n")
        lf = raw.count(b"\n") - crlf
        if crlf and lf:
            suspect.append(f"{name}  (mixed endings: {crlf} CRLF, {lf} bare LF)")
    return suspect


def cmd_ledger(args):
    if not LEDGER.exists():
        print("no runs yet")
        return 0
    rows = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"{'date':<17} {'slug':<24} {'model':<16} {'secs':>6} {'exit':>5}  verdict")
    for r in rows:
        print(f"{r['ts'][:16]:<17} {r['slug']:<24} {r['model']:<16} "
              f"{r['duration_s']:>6.0f} {r['exit_code']:>5}  {r.get('verdict') or '-'}")
    graded = [r for r in rows if r.get("verdict")]
    print(f"\n{len(rows)} runs, {len(graded)} graded.")
    if graded:
        good = sum(1 for r in graded if r["verdict"] in ("good", "usable"))
        print(f"usable: {good}/{len(graded)}")
    return 0


def cmd_clean(args):
    wt = worktree_path(args.slug)
    branch = f"codex/{args.slug}"
    if wt.exists():
        git("worktree", "remove", "--force", str(wt))
        print(f"removed worktree {wt}")
    git("worktree", "prune")
    if args.delete_branch:
        git("branch", "-D", branch, check=False)
        print(f"deleted branch {branch}")
    else:
        print(f"kept branch {branch} (pass --delete-branch to drop it)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="delegate a job to an isolated worktree")
    r.add_argument("slug", help="short kebab-case name; becomes codex/<slug>")
    r.add_argument("--task", help="the task text")
    r.add_argument("--task-file", help="file containing the task text")
    r.add_argument("--model", default=DEFAULT_MODEL)
    r.add_argument("--base", default="main")
    r.add_argument("--sandbox", default="workspace-write",
                   choices=["read-only", "workspace-write", "danger-full-access"],
                   help="passed to codex -s; overrides the user's global config")
    r.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                   help="wall-clock seconds; not a token budget")
    r.add_argument("--dry-run", action="store_true")
    r.set_defaults(func=cmd_run)

    l = sub.add_parser("ledger", help="show past runs and their graded verdicts")
    l.set_defaults(func=cmd_ledger)

    c = sub.add_parser("clean", help="remove a delegate worktree")
    c.add_argument("slug")
    c.add_argument("--delete-branch", action="store_true")
    c.set_defaults(func=cmd_clean)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
