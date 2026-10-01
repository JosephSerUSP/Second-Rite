"""Raise the backstreet roofline so the court reads within a lived-in quarter."""
from __future__ import annotations

import bpy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend"
sys.path.insert(0, str(ROOT / "tools/blender/recipes"))
from first_stratum.common import box_geometry


def main():
    if not bpy.data.filepath:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene = bpy.context.scene
    if Path(bpy.data.filepath).resolve() != SOURCE.resolve() or scene.get("courtyard_revision") != 5:
        raise RuntimeError("Expected Passage House courtyard revision 5")
    source = bpy.data.collections["TH_SOURCE"]
    plaster = bpy.data.materials["Cortico chalk limewash"]
    trim = bpy.data.materials["Court threshold stone"]
    wood = bpy.data.materials["Court tropical hardwood"]
    root = bpy.data.objects["Passage House arrival court"]

    def box(name, size, location, material):
        mesh = bpy.data.meshes.new(name + "_mesh")
        verts, faces = box_geometry(size)
        mesh.from_pydata(verts, [], faces)
        mesh.materials.append(material)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        source.objects.link(obj)
        obj.parent = root
        obj.location = location
        obj["sr_bake_source"] = True
        return obj

    # The centre house stands behind the Passage House roof. Its extra, narrower
    # upper storey creates an unmistakable skyline through the central lightwell.
    # Recessed bays and projecting sills keep the extension from reading as a box.
    front_x, centre_y, width = 12.15, 7.8, 10.8
    bottom, top = 9.55, 12.5
    window_centres = (4.2, 7.8, 11.4)
    spans = [centre_y-width/2, *[c-.62 for c in window_centres],
             *[c+.62 for c in window_centres], centre_y+width/2]
    # Three continuous masonry piers make deep, dark openings in the upper wall.
    ordered = sorted(set(spans))
    for i, (lo, hi) in enumerate(zip(ordered, ordered[1:])):
        mid = (lo+hi)/2
        if any(abs(mid-c) < .62 for c in window_centres):
            box(f"skyline_upper_masonry_{i}", (.58, hi-lo, top-bottom),
                (front_x+.29, mid, (bottom+top)/2), plaster)
    for i, cy in enumerate(window_centres):
        box(f"skyline_upper_lintel_{i}", (.74, 1.45, .18),
            (front_x-.04, cy, top-.12), trim)
        box(f"skyline_upper_sill_{i}", (.82, 1.52, .16),
            (front_x-.08, cy, bottom+.28), trim)
        box(f"skyline_upper_louver_{i}", (.10, .94, 1.62),
            (front_x-.015, cy, bottom+1.47), wood)
    box("skyline_upper_floor_band", (.74, width+.32, .24),
        (front_x-.05, centre_y, bottom+.02), trim)
    # A shallow hipped roof and parapet cap step the silhouette above the lower
    # pantile roof. The existing shared building rows remain visible at either side.
    box("skyline_upper_eave", (.94, width+.70, .22),
        (front_x-.14, centre_y, top+.05), wood)
    box("skyline_upper_roof_cap", (4.1, width+.16, .20),
        (front_x+1.62, centre_y, top+.34), bpy.data.materials["Court terracotta"])
    box("skyline_upper_ridge", (.32, width+.36, .28),
        (front_x+1.62, centre_y, top+.53), bpy.data.materials["Court terracotta"])
    scene["courtyard_revision"] = 6
    scene["roof_context"] = "split lodging roof and raised backstreet skyline visible through the lightwell"
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
    print("PASSAGE COURTYARD SKYLINE OK", SOURCE)


if __name__ == "__main__":
    main()
