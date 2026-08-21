"""Promote only the deliberately selected artifacts out of the temp workspace.

Rejected .blends, rejected material downloads and every intermediate render
stay in the scratchpad. What lands in the repository is the minimum needed to
(a) look at the result, (b) run the winner, and (c) reproduce it.

The winner .blend is repathed as part of promotion: while it lives in the
scratchpad its image datablocks point at absolute temp paths, so copying the
file alone would produce a .blend that cannot be reopened.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEST = (ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring"
        / "town-cleanroom")
PKG_DEST = (ROOT / "projects" / "hichaukitoden-game" / "assets" / "environments"
            / "town_cleanroom")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


REPATH = '''
import bpy, json, sys, os
mapping = json.loads({mapping!r})
missing = []
for img in bpy.data.images:
    if not img.filepath:
        continue
    src = os.path.normcase(os.path.abspath(bpy.path.abspath(img.filepath)))
    new = mapping.get(src)
    if new:
        # Absolute here, then let save_as_mainfile(relative_remap=True) do the
        # conversion. bpy.path.relpath() raises when the open .blend and the
        # destination sit on different Windows drives, which is exactly the
        # scratchpad (C:) -> repository (D:) promotion this performs.
        img.filepath = new
    else:
        missing.append(img.filepath)
bpy.ops.wm.save_as_mainfile(filepath={out!r}, relative_remap=True)
print("REPATH_OK " + json.dumps({{"unmapped": missing}}))
'''


def promote(workspace, winner_id="07", *, blender=None):
    sys.path.insert(0, str(ROOT / "tools" / "blender"))
    from town_environment_pipeline import blender_executable
    blender = blender or blender_executable()
    ws = Path(workspace)
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "materials").mkdir(parents=True, exist_ok=True)
    PKG_DEST.mkdir(parents=True, exist_ok=True)

    record = json.loads((ws / "attempts" / (winner_id + ".json"))
                        .read_text(encoding="utf-8"))

    # --- material sources the winner actually needs ----------------------
    mapping, provenance = {}, {"materials": [], "note": (
        "Only the material sources the winning scene uses are kept. Sources "
        "acquired during the task but not used by the winner remain in the "
        "temporary workspace and are listed in the report.")}
    for src in sorted(list((ws / "public").rglob("*.png"))
                      + list((ws / "generated").glob("*.png"))):
        if src.name.endswith("_raw.png"):
            continue
        dest = DEST / "materials" / src.name
        shutil.copyfile(src, dest)
        mapping[str(src).lower()] = str(dest)

    for prov in sorted((ws / "public").rglob("provenance.json")):
        provenance["materials"].append(json.loads(prov.read_text(encoding="utf-8")))
    for meta in sorted((ws / "generated").glob("*_maps.json")):
        d = json.loads(meta.read_text(encoding="utf-8"))
        d.update({"id": meta.stem.replace("_maps", ""),
                  "strategy": "generated",
                  "model": "gpt-image-2",
                  "channels": ("one flat albedo generated; height, ambient "
                               "occlusion and roughness derived numerically "
                               "from it"),
                  "license": "generated during this task"})
        provenance["materials"].append(d)
    for m in provenance["materials"]:
        for f in (m.get("files") or {}).values():
            p = DEST / "materials" / f["file"]
            if p.is_file():
                f["sha256"] = sha256(p)
                f["bytes"] = p.stat().st_size

    # --- the winner .blend, repathed -------------------------------------
    out_blend = DEST / "town-cleanroom.blend"
    s = tempfile.NamedTemporaryFile(prefix="cr_promote_", suffix=".py",
                                    delete=False, mode="w", encoding="utf-8")
    s.write(REPATH.format(
        mapping=json.dumps({k: str(v) for k, v in mapping.items()}),
        out=str(out_blend)))
    s.close()
    res = subprocess.run([blender, "--background",
                          str(ws / "attempts" / (winner_id + ".blend")),
                          "--python", s.name], capture_output=True, text=True)
    Path(s.name).unlink(missing_ok=True)
    line = [l for l in res.stdout.splitlines() if l.startswith("REPATH_OK ")]
    if res.returncode != 0 or not line:
        raise SystemExit("repath failed\n%s\n%s"
                         % (res.stdout[-3000:], res.stderr[-2000:]))
    unmapped = json.loads(line[-1][len("REPATH_OK "):])["unmapped"]

    # --- runtime package ---------------------------------------------------
    for f in sorted((ws / "package").glob("*")):
        if f.is_file():
            shutil.copyfile(f, PKG_DEST / f.name)

    # --- figures -----------------------------------------------------------
    for name in ("town-cleanroom-gauntlet-contact-sheet.png",
                 "town-cleanroom-source-vs-baked.png",
                 "town-cleanroom-projection-strip.png",
                 "town-cleanroom-material-vocabulary.png"):
        src = ws / name
        if src.is_file():
            shutil.copyfile(src, DEST / name)

    (DEST / "material-provenance.json").write_text(
        json.dumps(provenance, indent=2), encoding="utf-8")

    return {
        "blend": str(out_blend),
        "unmappedImages": unmapped,
        "materialFiles": len(list((DEST / "materials").glob("*.png"))),
        "materialBytes": sum(p.stat().st_size
                             for p in (DEST / "materials").glob("*.png")),
        "packageFiles": sorted(p.name for p in PKG_DEST.glob("*")),
        "winner": record,
    }
