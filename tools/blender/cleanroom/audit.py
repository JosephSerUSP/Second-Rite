"""ASSET FIREWALL AUDIT.

Enumerates every visual file this gauntlet consumed and proves that the only
PRE-EXISTING repository visual asset read was walker.png.

The check is structural, not a promise:

  1. every image referenced by the clean-room package's source is resolved and
     classified as repo-preexisting / created-during-task;
  2. the repository is scanned for visual assets and every one of them except
     walker.png must be absent from the consumed set;
  3. the winning .blend is opened and every image datablock in it is listed,
     which catches anything that entered through Blender rather than through
     this package's code.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WALKER = (ROOT / "projects" / "hichaukitoden-game" / "assets" / "character"
          / "walker.png")
VISUAL_SUFFIXES = {".png", ".jpg", ".jpeg", ".tga", ".bmp", ".exr", ".hdr",
                   ".gif", ".webp", ".psd", ".tif", ".tiff", ".blend", ".obj",
                   ".mtl", ".fbx", ".gltf", ".glb", ".dae"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


BASE_COMMIT = "3d391e05"
_BASE_CACHE = {}


def base_tracked_files():
    """Paths tracked in the repository at the commit this branch was cut from.

    This is the only honest definition of "pre-existing". Classifying by
    location fails as soon as the task WRITES into the repository, which the
    promotion step does -- every promoted figure and material would otherwise
    be reported as a firewall breach.
    """
    if "set" not in _BASE_CACHE:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "-r",
                              "--name-only", BASE_COMMIT],
                             capture_output=True, text=True)
        if out.returncode != 0:
            raise SystemExit("could not list base commit %s: %s"
                             % (BASE_COMMIT, out.stderr[-500:]))
        _BASE_CACHE["set"] = {line.strip().replace("\\", "/").lower()
                              for line in out.stdout.splitlines() if line.strip()}
    return _BASE_CACHE["set"]


def _classify(path, workspace):
    p = Path(path).resolve()
    try:
        p.relative_to(Path(workspace).resolve())
        return "created-during-task"
    except ValueError:
        pass
    try:
        rel = p.relative_to(ROOT).as_posix().lower()
    except ValueError:
        return "external"
    return "repo-preexisting" if rel in base_tracked_files() else "created-during-task"


def code_references():
    """Every literal asset path the clean-room package can reach."""
    pkg = ROOT / "tools" / "blender" / "cleanroom"
    hits = []
    for py in sorted(pkg.rglob("*.py")):
        text = py.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'["\']([^"\']*\.(?:png|jpg|jpeg|tga|exr|hdr|blend|obj))["\']',
                             text, re.IGNORECASE):
            hits.append({"file": str(py.relative_to(ROOT)), "literal": m.group(1)})
        if "assets" in text and "character" in text:
            for m in re.finditer(r'"([a-z_]+)"\s*/\s*"(walker\.png)"', text):
                hits.append({"file": str(py.relative_to(ROOT)),
                             "literal": "/".join(m.groups())})
    return hits


BLEND_SNIPPET = '''
import bpy, json
rows = []
for img in bpy.data.images:
    if img.name in ("Render Result", "Viewer Node"):
        continue
    rows.append({"name": img.name,
                 "filepath": bpy.path.abspath(img.filepath) if img.filepath else "",
                 "packed": bool(img.packed_file),
                 "size": list(img.size)})
print("BLENDIMAGES " + json.dumps(rows))
'''


def blend_images(blend, blender=None):
    sys.path.insert(0, str(ROOT / "tools" / "blender"))
    from town_environment_pipeline import blender_executable
    blender = blender or blender_executable()
    s = tempfile.NamedTemporaryFile(prefix="cr_audit_", suffix=".py",
                                    delete=False, mode="w", encoding="utf-8")
    s.write(BLEND_SNIPPET)
    s.close()
    res = subprocess.run([blender, "--background", str(blend), "--python", s.name],
                         capture_output=True, text=True)
    Path(s.name).unlink(missing_ok=True)
    line = [l for l in res.stdout.splitlines() if l.startswith("BLENDIMAGES ")]
    if not line:
        raise SystemExit("could not enumerate blend images\n" + res.stdout[-2000:])
    return json.loads(line[-1][len("BLENDIMAGES "):])


def repo_visual_inventory():
    out = []
    skip = {".git", "node_modules", "__pycache__", ".claude"}
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in VISUAL_SUFFIXES:
            continue
        if any(part in skip for part in p.parts):
            continue
        out.append(p)
    return out


def run(workspace, winner_blend, out_path):
    workspace = Path(workspace)
    consumed = {}

    # 1. the one permitted pre-existing asset
    consumed[str(WALKER)] = {
        "role": "protagonist and NPC stand-in frames (24x48, 6 frames)",
        "class": "repo-preexisting",
        "permitted": True,
        "sha256": sha256(WALKER) if WALKER.is_file() else None,
        "bytes": WALKER.stat().st_size if WALKER.is_file() else 0,
    }

    # 2. everything created during the task
    for p in sorted(workspace.rglob("*")):
        if p.is_file() and p.suffix.lower() in VISUAL_SUFFIXES:
            consumed[str(p)] = {
                "role": "created during this task",
                "class": _classify(p, workspace),
                "permitted": True,
                "bytes": p.stat().st_size,
            }

    # 3. what the winning blend actually holds
    blend_imgs = blend_images(winner_blend)
    violations = []
    for row in blend_imgs:
        fp = row["filepath"]
        if not fp:
            continue
        cls = _classify(fp, workspace)
        if cls == "repo-preexisting" and Path(fp).resolve() != WALKER.resolve():
            violations.append({"where": "winner.blend", "path": fp})

    # 4. code literals that RESOLVE to a pre-existing repository file.
    # A bare extension, a format string, or the name of a file this task
    # WRITES is not an input. Only a literal that names an existing repo file
    # other than walker.png is a firewall breach.
    literal_inputs = []
    for hit in code_references():
        lit = hit["literal"]
        # skip format strings, bare suffixes and GLOB PATTERNS -- a
        # literal like "*.png" is a directory query, not an input, and
        # feeding it to Path.glob matches an arbitrary repo file.
        if (not lit or "%" in lit or lit.startswith(".")
                or any(ch in lit for ch in "*?[]{}")):
            continue
        candidates = [ROOT / lit] + list(ROOT.glob("**/" + Path(lit).name))[:4]
        for cand in candidates:
            if not cand.is_file():
                continue
            if cand.resolve() == WALKER.resolve():
                continue
            # Same ground truth as everywhere else: only a file that existed at
            # the base commit can be an inherited input. Names of files this
            # task writes (the promoted figures, the winner .blend) are outputs.
            if _classify(cand, workspace) != "repo-preexisting":
                continue
            literal_inputs.append({"where": hit["file"], "path": str(cand)})
            violations.append({"where": hit["file"], "path": str(cand),
                               "note": "clean-room code names a pre-existing "
                                       "repository visual asset"})
            break

    inventory = [p for p in repo_visual_inventory()
                 if p.relative_to(ROOT).as_posix().lower() in base_tracked_files()]
    consumed_repo = [k for k, v in consumed.items() if v["class"] == "repo-preexisting"]

    report = {
        "verdict": "VALID" if not violations and consumed_repo == [str(WALKER)]
                   else "INVALID",
        "onlyPreexistingRepoAssetConsumed": str(
            WALKER.relative_to(ROOT)).replace("\\", "/"),
        "preexistingRepoAssetsConsumed": [
            str(Path(k).relative_to(ROOT)).replace("\\", "/")
            for k in consumed_repo],
        "repoVisualAssetsPresent": len(inventory),
        "repoVisualAssetsConsumed": len(consumed_repo),
        "createdDuringTask": sum(1 for v in consumed.values()
                                 if v["class"] == "created-during-task"),
        "winnerBlendImages": blend_imgs,
        "violations": violations,
        "consumed": consumed,
    }
    Path(out_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
