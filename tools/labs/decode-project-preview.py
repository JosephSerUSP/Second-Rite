#!/usr/bin/env python3
"""Decode one Thestra PREVIEW payload into a disposable review PNG.

Lab review captures are human-inspection evidence, not G5 golden references.
The input is the stdout produced by `lovec . preview-scene ...` or
`lovec . preview-map ...`.

Beyond decoding, this asserts on evidence the preview already produces and
previously discarded (#920 Rung 1). `preview-scene` runs `on_enter` through
the real interpreter, so a scene whose windows bind unresolvable formulas
prints `[formula] error ...` on stdout and then exits 0 with a perfectly good
PNG of a scene that never resolved. Treating "a PNG exists" as the whole
assertion is what let four broken specimens through an owner playtest with
reports claiming success.

A specimen may be quarantined while a known defect is open; see
`tools/labs/known-unplayable.json`. Quarantine is deliberately noisy and
self-cleaning: a quarantined specimen that stops failing also fails, so the
list cannot rot into a permanent exemption.
"""

import argparse
import base64
import json
import pathlib
import re

BEGIN = "PREVIEW BEGIN"
END = "PREVIEW END"

# Emitted by engine/formula.lua warnOnce when an authored formula cannot be
# resolved. Matching the literal prefix keeps this tied to the one producer
# rather than to any line that happens to contain the word "error".
FORMULA_ERROR = re.compile(r"^\[formula\] error in .*$", re.MULTILINE)

QUARANTINE_DEFAULT = pathlib.Path(__file__).with_name("known-unplayable.json")


def load_quarantine(path, scene_id):
    """Return (quarantined, reason) for scene_id under the `preview` rung."""
    if not path or not path.exists():
        return False, None
    data = json.loads(path.read_text(encoding="utf-8"))
    entry = (data.get("preview") or {}).get(scene_id)
    if not entry:
        return False, None
    return True, entry.get("reason") or "(no reason recorded)"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--quarantine",
        default=str(QUARANTINE_DEFAULT),
        help="path to known-unplayable.json; pass an empty string to enforce with no exemptions",
    )
    args = parser.parse_args()

    text = pathlib.Path(args.input).read_text(encoding="utf-8", errors="replace")
    try:
        start = text.index(BEGIN) + len(BEGIN)
        end = text.index(END)
    except ValueError:
        raise SystemExit("decode-project-preview: no PREVIEW BEGIN/END payload; inspect runtime output")

    payload = json.loads(text[start:end].strip())
    if payload.get("error"):
        raise SystemExit(f"decode-project-preview: runtime preview error: {payload['error']}")
    if payload.get("imageError"):
        raise SystemExit(f"decode-project-preview: image render error: {payload['imageError']}")
    image = payload.get("image")
    if not image:
        raise SystemExit("decode-project-preview: preview produced no image")

    # Formula errors are printed by the runtime OUTSIDE the payload markers.
    # Scan only that region so a scene legitimately containing the string in
    # authored text cannot trip the check.
    outside = text[: text.index(BEGIN)] + text[text.index(END) + len(END) :]
    formula_errors = FORMULA_ERROR.findall(outside)

    scene_id = str(payload.get("sceneId") or "")
    quarantine_path = pathlib.Path(args.quarantine) if args.quarantine else None
    quarantined, reason = load_quarantine(quarantine_path, scene_id)

    if formula_errors and not quarantined:
        listed = "\n".join("    " + line for line in formula_errors)
        raise SystemExit(
            f"decode-project-preview: scene '{scene_id}' resolved {len(formula_errors)} "
            f"unresolvable formula(s) during on_enter:\n{listed}\n"
            "  The preview still produced a PNG; the scene did not resolve. Fix the scene,\n"
            "  or quarantine it in tools/labs/known-unplayable.json with an open issue."
        )

    if quarantined and not formula_errors:
        raise SystemExit(
            f"decode-project-preview: scene '{scene_id}' is quarantined in "
            f"{quarantine_path} ({reason}) but emitted no formula errors.\n"
            "  Quarantine is for currently-failing specimens only. Remove the entry."
        )

    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base64.b64decode(image))
    meta = output.with_suffix(output.suffix + ".json")
    meta.write_text(json.dumps({k: v for k, v in payload.items() if k != "image"}, indent=2) + "\n", encoding="utf-8")

    if quarantined:
        print(
            f"LAB PREVIEW QUARANTINED -> {output} "
            f"({len(formula_errors)} formula error(s); {reason})"
        )
    else:
        print(f"LAB PREVIEW OK -> {output}")


if __name__ == "__main__":
    main()
