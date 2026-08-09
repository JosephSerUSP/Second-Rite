"""watch -- see what a delegated agent is actually doing, live.

    python tools/delegate/watch.py              # follow the newest session
    python tools/delegate/watch.py --once       # snapshot and exit
    python tools/delegate/watch.py --session <path-to-rollout.jsonl>

Codex writes a JSONL rollout per session under ~/.codex/sessions/ as it works,
so a run is observable while it is still going even when the wrapper that
launched it is buffering. This renders the interesting events -- shell commands,
file patches, agent prose, token spend -- and skips the transport noise.

Reading this is the point. A delegate's summary is a sentence it generated; the
exec log is what it did.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SESSIONS = Path(os.path.expanduser("~")) / ".codex" / "sessions"


def newest_session():
    files = sorted(SESSIONS.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise SystemExit(f"no session files under {SESSIONS}")
    return files[-1]


def trim(text, limit):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit] + " ..."


def render(event, state, width):
    """Return a line to print, or None to stay quiet about this event."""
    kind = event.get("type")
    p = event.get("payload") or {}
    ptype = p.get("type")

    if ptype == "custom_tool_call" and p.get("name") == "exec":
        raw = p.get("input")
        cmd = raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                cmd = parsed.get("command", raw)
            except Exception:
                pass
        if isinstance(cmd, list):
            cmd = " ".join(str(c) for c in cmd)
        state["execs"] += 1
        return f"  $ {trim(cmd, width)}"

    if ptype == "patch_apply_end":
        changes = p.get("changes") or {}
        names = [Path(k).name for k in changes] or ["(no files)"]
        ok = "ok" if p.get("success") else "FAILED"
        state["patches"] += 1
        for k in changes:
            state["files"].add(k)
        return f"  ~ patch {ok}: {trim(', '.join(names), width)}"

    if ptype == "agent_message" or (ptype == "message" and p.get("role") == "assistant"):
        content = p.get("content") or p.get("text") or ""
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "") for c in content if isinstance(c, dict)
            )
        content = content.strip()
        if content:
            return f"\n[agent] {trim(content, width * 3)}\n"
        return None

    if ptype == "token_count":
        info = p.get("info") or {}
        total = info.get("total_token_usage") or {}
        n = total.get("total_tokens")
        if isinstance(n, int) and n > state["tokens"]:
            state["tokens"] = n
        return None

    if ptype == "reasoning":
        summary = p.get("summary")
        if isinstance(summary, list) and summary:
            texts = [s.get("text", "") for s in summary if isinstance(s, dict)]
            joined = " ".join(t for t in texts if t).strip()
            if joined:
                return f"  . {trim(joined, width)}"
        return None

    if ptype == "error" or kind == "error":
        return f"  ! {trim(p.get('message') or p, width)}"

    return None


def status(state):
    return (f"[{state['execs']} commands, {state['patches']} patches, "
            f"{len(state['files'])} files touched, {state['tokens']:,} tokens]")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--session", help="rollout jsonl path; default is newest")
    ap.add_argument("--once", action="store_true", help="snapshot and exit")
    ap.add_argument("--width", type=int, default=140)
    args = ap.parse_args()

    path = Path(args.session) if args.session else newest_session()
    print(f"watching {path.name}\n")

    state = {"execs": 0, "patches": 0, "tokens": 0, "files": set()}
    offset = 0
    idle = 0

    while True:
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            print("session file vanished")
            return 1

        if size > offset:
            idle = 0
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                fh.seek(offset)
                chunk = fh.read()
                # A final partial line means the writer is mid-flush; leave it
                # for the next pass rather than dropping or mangling it.
                if not chunk.endswith("\n"):
                    cut = chunk.rfind("\n")
                    chunk = chunk[: cut + 1] if cut != -1 else ""
                offset += len(chunk.encode("utf-8", errors="replace"))
            for line in chunk.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                out = render(event, state, args.width)
                if out:
                    print(out, flush=True)
        else:
            idle += 1

        if args.once:
            break
        if idle >= 60:
            print(f"\nno new events for 2 minutes. {status(state)}")
            break
        time.sleep(2)

    print(f"\n{status(state)}")
    if state["files"]:
        print("files touched:")
        for f in sorted(state["files"]):
            print(f"  {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
