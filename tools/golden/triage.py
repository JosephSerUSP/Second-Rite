#!/usr/bin/env python3
"""G5/G6 triage -- classify a red pixel gate before touching a reference.

check-screens.ps1 and check-editor.ps1 answer *which* frames differ and write
the actual frames next to the references for eyeballing. Neither answers the
question that actually decides what to do next: **is this a regression, or is
it the machine?** Both gates byte-compare pixels on one GPU/browser, so a
driver, font or Chrome update legitimately shifts them (AGENTS.md, SPEC 3) --
and telling that apart from a real visual regression has so far been done by
hand, per frame, every time a pixel gate went red.

The distinction is measurable, and it is the whole point of this script:

  * A *regression* changes something specific. The changed pixels cluster in a
    bounding box notably smaller than the frame, and/or the channel deltas are
    large -- a window moved, a sprite resolved wrong, a bar drew at the wrong
    width.
  * *Machine drift* changes everything a little. Resampling, dithering and
    font rasterisation shift a large fraction of the frame by a channel step
    or two, with a bounding box covering nearly the whole image.

So this reports, per differing frame: how many pixels changed, what fraction
of the frame that is, the bounding box of the change, and the largest channel
delta. The classification is a *reading*, not a verdict -- the numbers behind
it are always printed, because the call to recapture a reference is
owner-signed and must be made on evidence rather than on this script's guess.

The `*-actual/` trees are run-scoped by `actual_run.py`. A marked tree contains
only evidence from the latest G5/G6 invocation. An older tree without that
marker is reported as ORPHAN output instead of being mistaken for current NEW
coverage or a current regression; rerun the owning gate to obtain scoped
triage evidence.

This is a REPORT, NOT A GATE: it always exits 0, exactly as `lovec .
reachability` does and for the same reason. The gate is check-screens.ps1 /
check-editor.ps1; a second thing that can fail would only invite silencing it.

Usage:
    python tools/golden/triage.py            # both gates, whatever is present
    python tools/golden/triage.py --gate g5
    python tools/golden/triage.py --gate g6 --heatmaps
"""

import argparse
import os

from actual_run import read_marker

try:
    import numpy as np
    from PIL import Image
except ImportError:  # pragma: no cover - environment problem, not a frame problem
    raise SystemExit(
        "triage.py needs Pillow and numpy (already required by the asset-gen\n"
        "tooling): python -m pip install pillow numpy")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GATES = {
    "g5": ("G5 screens", "tools/golden/screens", "tools/golden/screens-actual"),
    "g6": ("G6 editor", "tools/golden/editor-screens", "tools/golden/editor-screens-actual"),
}

# A channel step or two across a large area is what resampling and font
# rasterisation do; a real regression that subtle would be invisible to a
# player anyway. Both halves of the drift reading must hold.
DRIFT_MAX_CHANNEL_DELTA = 8
DRIFT_MIN_CHANGED_FRACTION = 0.20
LOCALIZED_MAX_BBOX_FRACTION = 0.60


def png_paths(directory):
    """Relative slash-separated paths of every PNG below `directory`."""
    found = set()
    for dirpath, _, filenames in os.walk(directory):
        for name in filenames:
            if name.endswith(".png"):
                rel = os.path.relpath(os.path.join(dirpath, name), directory)
                found.add(rel.replace("\\", "/"))
    return found


def compare(ref_path, actual_path):
    """Measure one frame pair. Returns a dict, or None when byte-identical."""
    ref = Image.open(ref_path).convert("RGB")
    actual = Image.open(actual_path).convert("RGB")

    if ref.size != actual.size:
        return {
            "reading": "LAYOUT",
            "detail": "frame size changed: %dx%d -> %dx%d" % (
                ref.size[0], ref.size[1], actual.size[0], actual.size[1]),
        }

    a = np.asarray(ref, dtype=np.int16)
    b = np.asarray(actual, dtype=np.int16)
    delta = np.abs(a - b)
    changed = delta.any(axis=2)
    changed_count = int(changed.sum())
    if changed_count == 0:
        return None

    height, width = changed.shape
    total = height * width
    rows = np.flatnonzero(changed.any(axis=1))
    cols = np.flatnonzero(changed.any(axis=0))
    top, bottom = int(rows[0]), int(rows[-1])
    left, right = int(cols[0]), int(cols[-1])
    bbox_area = (bottom - top + 1) * (right - left + 1)

    changed_fraction = changed_count / total
    bbox_fraction = bbox_area / total
    max_delta = int(delta.max())

    if max_delta <= DRIFT_MAX_CHANNEL_DELTA and changed_fraction >= DRIFT_MIN_CHANGED_FRACTION:
        reading = "DRIFT?"
    elif bbox_fraction <= LOCALIZED_MAX_BBOX_FRACTION:
        reading = "LOCALIZED"
    else:
        reading = "BROAD"

    return {
        "reading": reading,
        "changed": changed_count,
        "total": total,
        "changed_fraction": changed_fraction,
        "bbox": (left, top, right, bottom),
        "bbox_fraction": bbox_fraction,
        "max_delta": max_delta,
        "delta": delta,
    }


def write_heatmap(rel, result, actual_dir):
    """Red-over-grey overlay of exactly which pixels moved."""
    dest = os.path.join(actual_dir, os.path.dirname(rel), "_heatmap")
    os.makedirs(dest, exist_ok=True)
    magnitude = result["delta"].max(axis=2).astype(np.uint8)
    overlay = np.zeros(magnitude.shape + (3,), dtype=np.uint8)
    overlay[..., 0] = np.where(magnitude > 0, 255, 0)
    overlay[..., 1] = np.where(magnitude > 0, 255 - np.minimum(magnitude * 8, 255), 0)
    path = os.path.join(dest, os.path.basename(rel))
    Image.fromarray(overlay).save(path)
    return os.path.relpath(path, ROOT).replace("\\", "/")


def report_orphans(label, actual_rel, actuals):
    """Report unscoped legacy output without interpreting its pixels."""
    print("%s: %d unscoped frame(s) in %s" % (label, len(actuals), actual_rel))
    print("  No current-run marker exists for this actual-output tree.")
    print("  These files may be leftovers from an older harness shape; rerun the gate")
    print("  before using them to make a regression or recapture decision.")
    print("")
    for rel in sorted(actuals):
        print("  ORPHAN     %s" % rel)
        print("             unscoped actual output; not evidence from the latest marked run.")
    print("")
    print("  ORPHAN x%d" % len(actuals))
    print("")


def triage_gate(key, heatmaps):
    label, ref_rel, actual_rel = GATES[key]
    ref_dir = os.path.join(ROOT, *ref_rel.split("/"))
    actual_dir = os.path.join(ROOT, *actual_rel.split("/"))

    if not os.path.isdir(actual_dir) or not png_paths(actual_dir):
        print("%s: nothing in %s -- the gate is green, or has not been run." % (
            label, actual_rel))
        return

    refs, actuals = png_paths(ref_dir), png_paths(actual_dir)
    if read_marker(actual_dir, expected_scope=key) is None:
        report_orphans(label, actual_rel, actuals)
        return

    print("%s: %d current-run frame(s) written to %s" % (label, len(actuals), actual_rel))
    print("")

    readings = {}
    for rel in sorted(actuals):
        if rel not in refs:
            print("  NEW        %s" % rel)
            print("             captured by the latest scoped gate run; no reference exists.")
            readings["NEW"] = readings.get("NEW", 0) + 1
            continue

        result = compare(os.path.join(ref_dir, *rel.split("/")),
                         os.path.join(actual_dir, *rel.split("/")))
        if result is None:
            # The current gates clear actual output before each run, so a matching
            # frame here is unusual (for example, a manually copied current-run
            # artifact), but keep the reading explicit rather than guessing.
            print("  STALE      %s (matches its reference; leftover output)" % rel)
            readings["STALE"] = readings.get("STALE", 0) + 1
            continue

        readings[result["reading"]] = readings.get(result["reading"], 0) + 1
        print("  %-10s %s" % (result["reading"], rel))
        if "detail" in result:
            print("             %s" % result["detail"])
            continue
        left, top, right, bottom = result["bbox"]
        print("             %d/%d px changed (%.2f%%), max channel delta %d" % (
            result["changed"], result["total"],
            result["changed_fraction"] * 100.0, result["max_delta"]))
        print("             bbox x%d..%d y%d..%d (%.1f%% of frame)" % (
            left, right, top, bottom, result["bbox_fraction"] * 100.0))
        if heatmaps:
            print("             heatmap: %s" % write_heatmap(rel, result, actual_dir))

    print("")
    print("  %s" % ", ".join("%s x%d" % (k, v) for k, v in sorted(readings.items())))
    print("")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gate", choices=sorted(GATES) + ["both"], default="both")
    parser.add_argument("--heatmaps", action="store_true",
                        help="write a red overlay of the changed pixels per frame")
    args = parser.parse_args()

    keys = sorted(GATES) if args.gate == "both" else [args.gate]
    for key in keys:
        triage_gate(key, args.heatmaps)

    print("Readings, not verdicts. LOCALIZED and BROAD are regressions until you")
    print("have found the change that explains them. DRIFT? is a candidate for a")
    print("machine shift -- confirm by checking whether the same frames drift on")
    print("an unrelated commit, and recapture only with owner sign-off.")
    print("ORPHAN means the actual-output tree is not scoped to a current gate run;")
    print("rerun that gate before interpreting or recapturing those frames.")


if __name__ == "__main__":
    main()
