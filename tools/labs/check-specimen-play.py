#!/usr/bin/env python3
"""#920 Rung 2 — assert that lab specimens are machine-played to a terminal state.

`MACHINE VALIDATED` used to mean: validate passes, a preview PNG exists, and the
staged game survives four seconds on the title screen. None of that plays the
game. Four broken specimens passed all of it and reached an owner playtest with
reports claiming success — a crash guarded behind `v.lost or v.win`, a board with
no solution, and a scene that renders nothing are each invisible to a gate that
never finishes a game.

This drives every `draw: windows` specimen through `lovec . play-scene <id>`,
which replays the authored input script through the same `scene_host.keypressed`
path real input uses, and then evaluates the terminal condition the specimen
itself declares:

    "terminal": { "reached": "v.win == true" }
    "terminal": { "none": "conversation, no scored loop" }

A specimen with no `terminal` declaration fails. "This one never ends" is a claim
an author makes on the record, so that a conversation can be told apart from a
game nobody can finish.

Exit code 0 only when every specimen either reached its declared terminal state,
declared `none`, or is quarantined in known-unplayable.json against an open issue.
"""

import argparse
import json
import pathlib
import subprocess
import sys

BEGIN = "PLAY BEGIN"
END = "PLAY END"

QUARANTINE_DEFAULT = pathlib.Path(__file__).with_name("known-unplayable.json")


def load_quarantine(path):
    if not path or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("play") or {}


def run_play(lovec, stage, scene_id, timeout):
    """Run one play-scene and return its payload dict.

    An unknown CLI token is silently ignored by main.lua and boots the game
    normally, which would sit here until the timeout and read as a hang rather
    than as a typo. Asserting on the PLAY BEGIN marker turns that into a clear
    failure instead of a mystery.
    """
    try:
        proc = subprocess.run(
            [lovec, ".", "play-scene", scene_id],
            cwd=stage,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, f"play-scene timed out after {timeout}s"

    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if BEGIN not in text or END not in text:
        tail = "\n".join(text.strip().splitlines()[-12:])
        return None, (
            "no PLAY BEGIN/END payload — the runtime never reached the play harness.\n"
            f"  last output:\n{tail}"
        )
    body = text[text.index(BEGIN) + len(BEGIN) : text.index(END)].strip()
    try:
        return json.loads(body), None
    except json.JSONDecodeError as exc:
        return None, f"unparseable PLAY payload: {exc}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, help="staged Project root to run against")
    parser.add_argument("--project", required=True, help="source lab Project root (for the scene index)")
    parser.add_argument("--lovec", default="lovec")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument(
        "--quarantine",
        default=str(QUARANTINE_DEFAULT),
        help="path to known-unplayable.json",
    )
    parser.add_argument(
        "--no-quarantine",
        action="store_true",
        help="enforce with no exemptions. This is the negative control: it must go red, "
        "naming exactly the specimens known-unplayable.json claims are broken.",
    )
    args = parser.parse_args()
    if args.no_quarantine:
        args.quarantine = ""

    project = pathlib.Path(args.project)
    index_path = project / "data" / "scenes" / "index.json"
    if not index_path.exists():
        raise SystemExit(f"check-specimen-play: no scene index at {index_path}")

    quarantine = load_quarantine(pathlib.Path(args.quarantine) if args.quarantine else None)

    scenes = []
    for name in json.loads(index_path.read_text(encoding="utf-8"))["files"]:
        data = json.loads((index_path.parent / name).read_text(encoding="utf-8"))
        if data.get("draw") == "windows" and data.get("id") != "title":
            scenes.append(data)

    if not scenes:
        raise SystemExit("check-specimen-play: no `draw: windows` specimens found — refusing to report a pass")

    failures, results = [], []
    for scene in scenes:
        scene_id = str(scene.get("id"))
        payload, err = run_play(args.lovec, args.stage, scene_id, args.timeout)
        entry = quarantine.get(scene_id)

        if err:
            verdict, detail = "HARNESS-FAIL", err
        elif payload.get("error"):
            verdict, detail = "FAIL", payload["error"]
        elif payload.get("terminalKind") == "none":
            verdict, detail = "NONE-DECLARED", payload.get("terminalReason", "")
        elif payload.get("reached"):
            verdict = "PLAYED"
            detail = (
                f"reached '{payload.get('terminalFormula')}' at step "
                f"{payload.get('reachedAtStep')}/{payload.get('stepsTotal')}"
            )
        else:
            verdict = "NOT-REACHED"
            detail = (
                f"ran {payload.get('stepsRun')}/{payload.get('stepsTotal')} steps from "
                f"{payload.get('scriptSource')}; '{payload.get('terminalFormula')}' never became true"
            )

        bad = verdict in ("FAIL", "NOT-REACHED", "HARNESS-FAIL")

        # Quarantine covers a specimen that is failing for a known, open reason.
        # It deliberately does NOT cover a harness failure: that means the check
        # itself could not run, which no issue excuses.
        if bad and entry and verdict != "HARNESS-FAIL":
            results.append((scene_id, "QUARANTINED", f"#{entry['issue']}: {entry['reason']}"))
            continue

        # A quarantined specimen that has started passing must not stay listed,
        # or the file rots into a permanent allowlist nobody rereads.
        if not bad and entry:
            failures.append(
                f"{scene_id}: quarantined against #{entry['issue']} but now {verdict}. "
                f"Remove its entry from {args.quarantine}."
            )
            results.append((scene_id, "STALE-QUARANTINE", verdict))
            continue

        if bad:
            failures.append(f"{scene_id}: {verdict} — {detail}")
        results.append((scene_id, verdict, detail))

    width = max(len(r[0]) for r in results)
    for scene_id, verdict, detail in results:
        print(f"  {scene_id:<{width}}  {verdict:<16} {detail}")

    played = sum(1 for r in results if r[1] == "PLAYED")
    none_declared = sum(1 for r in results if r[1] == "NONE-DECLARED")
    quarantined = sum(1 for r in results if r[1] == "QUARANTINED")
    print(
        f"\n{len(results)} specimens: {played} machine-played to a terminal state, "
        f"{none_declared} declared no terminal state, {quarantined} quarantined."
    )

    if failures:
        print("\nSPECIMEN PLAY FAILED:", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        return 1

    print("SPECIMEN PLAY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
