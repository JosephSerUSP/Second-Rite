"""A worked exterior that is deliberately NOT a place (#1350).

Copy this file for its STRUCTURE, never for its look. It is the exterior
counterpart of the Gate Room: every move a modelled street needs is here, and
nothing a street could be recognised by is. There is no story, no cast, no
trade, and only generic stone, wood and paving. A place built from it must
replace every facade, prop and material choice with ones its own brief earns.

What it does show, in the order an exterior is built:

1. **The ground runs off the frame.** `Exterior.ground()` starts the slab where
   the floor plane leaves the bottom of the frame (row 240), because the player
   stands IN a street, not in front of a cutaway.
2. **The far side varies in DEPTH, not height.** Rooflines leave the top of the
   frame at this camera, so a taller facade looks the same. A facade stepped
   forward or back off the terrace line reads at once.
3. **The near stack has three ranks** (`docs/design/st-maria-exterior-authoring.md`):
   NEAR masonry low enough to sit under the translucent menu, FOREGROUND
   posts the player passes behind, and PROPS at the action plane built inside
   `Exterior.props()` so they do not count as near.
4. **Heights come from the camera, not from taste.** The near wall's height is
   `dock_cover_height(x)`, so it just reaches the top of the menu band at its
   own depth.
5. **The sky is the light.** `sky_rig()`: soft dome, weak sun, no key.
6. **It measures itself and fails loud.** `boards()` must be empty, and the
   near stack must cover the menu band at every lane position.

The camera comes from the vocabulary (`Exterior` reads it through
`interior.camera_record()`). This file contains no camera number of its own, so
when #1298 changes how an exterior resolves its owning map's camera, the
example follows without an edit. A real place resolves its own map's camera
and walk profile; it does not inherit this lane or span.

It is guarded against shipping: the asset id carries `example_`, the default
output is the gitignored `out/`, a save under `projects/` is refused, and
`environment_sources.py --check` rejects any `example_*` file recorded as a
source.

    python tools/blender/run.py tools/blender/recipes/examples/exterior_reference.py -- \\
        [--blend out/examples/example_exterior_reference.blend] [--render out/examples/frames]

One machine-readable line is printed: `EXTERIOR_EXAMPLE {json}`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.shared.project_paths import project_root
PROJECT = project_root()
sys.path.insert(0, str(ROOT / "tools" / "blender"))
sys.path.insert(0, str(ROOT / "tools" / "blender" / "recipes"))

from exterior import Exterior, dock_cover_height  # noqa: E402
from interior import material  # noqa: E402

ASSET_ID = "example_exterior_reference"
DEFAULT_BLEND = ROOT / "out" / "examples" / f"{ASSET_ID}.blend"

# A lane long enough that the camera pans, so coverage is tested at many
# positions and not only where the composition looks good.
SPAN = 24.0

# The far side: (lane centre, width, terrace offset). The offsets are the
# variation. A real street chooses them from its brief.
FACADES = (
    (-2.5, 7.0, 0.0),
    (4.6, 6.2, -0.8),   # stepped forward: catches light, breaks the run
    (10.8, 5.0, 0.0),   # the gap before it is an alley
    (17.0, 6.6, 0.6),   # set back
    (23.6, 6.0, 0.0),
    (29.8, 6.0, -0.5),
)
FACADE_HEIGHT = 7.5     # its top is out of frame on purpose

# NEAR rank. It sits under the menu band and does not touch the player.
NEAR_X = -10.0
NEAR_RUNS = ((-4.0, 5.0), (6.2, 15.5), (16.7, 28.0))  # gaps keep it a street edge, not a wall

# FOREGROUND rank: posts the player passes behind. Tall but narrow, which is
# the rule: tall or continuous, never both.
POST_X = -5.0
POST_LANE = (2.0, 9.0, 16.0, 23.0)

# Smallest share of the menu band the near stack must cover at every lane
# position the camera can stand at. Measured once on this composition, and
# kept as a floor so an edit that opens a hole fails here, not in review.
MIN_DOCK_COVERAGE = 0.6


def build():
    ext = Exterior(ASSET_ID, SPAN)
    stone = material("old_limestone")
    rough = material("rough_limestone")
    wood = material("dark_wood")

    # 1. ground: from the frame bottom back past the facades.
    ext.ground(material_value=rough)

    # 2. far side: masses on the terrace line, varied in depth.
    for index, (lane, width, offset) in enumerate(FACADES):
        name = f"facade_{index}"
        x = ext.back_x + offset
        ext.facade(name, lane, width=width, height=FACADE_HEIGHT, x=x,
                   material_value=stone)
        ext.doorway(f"{name}_door", lane - width * 0.22, x=x)
        ext.window(f"{name}_window", lane + width * 0.2, x=x, shutters=True)
        ext.window(f"{name}_upper", lane, sill_z=3.9, x=x, shutters=False)

    # 3a. PROPS at the action plane: known-size objects belong where they read
    #     at their true size, and they are not measured as near.
    with ext.props():
        ext.crate("prop_crate", 6.0, x=1.2)
        ext.barrel("prop_barrel", 7.0, x=1.4)
        ext.crate("prop_crate_far", 19.5, x=2.0, size=(0.6, 0.6, 0.5))

    # 3b. FOREGROUND posts the player passes behind.
    for index, lane in enumerate(POST_LANE):
        ext.foreground(f"post_{index}", lane, size=(0.28, 0.28, 2.9),
                       x=POST_X, material_value=wood)

    # 3c. NEAR masonry. Its height is the camera's answer at this depth, plus
    #     a coping course that the vocabulary adds.
    height = dock_cover_height(NEAR_X, ext.record) + 0.05
    for index, (lane_from, lane_to) in enumerate(NEAR_RUNS):
        ext.low_wall(f"near_wall_{index}", lane_from, lane_to, x=NEAR_X,
                     height=height)

    # 5. light.
    ext.sky_rig()
    return ext


def measure(ext):
    """The checks a real exterior must also pass. Failures raise."""
    lanes = [round(0.5 * i, 2) for i in range(int(SPAN / 0.5) + 1)]
    coverage = {lane: round(ext.dock_coverage(lane), 3) for lane in lanes}
    worst_lane = min(coverage, key=coverage.get)
    boards = ext.boards()
    report = {
        "asset": ASSET_ID,
        "span": SPAN,
        "boards": boards,
        "dockCoverageMin": coverage[worst_lane],
        "dockCoverageWorstLane": worst_lane,
        "foregroundScale": ext.foreground_scale()[:3],
        "parts": len(ext.parts),
    }
    problems = []
    if boards:
        problems.append(f"occluders break tall-or-continuous: {boards}")
    if coverage[worst_lane] < MIN_DOCK_COVERAGE:
        problems.append(f"near stack covers {coverage[worst_lane]} of the menu band "
                        f"at lane {worst_lane}; need {MIN_DOCK_COVERAGE}")
    return report, problems


def render(ext, out_dir, lanes=(SPAN / 2.0,)):
    """Native frames through the vocabulary's camera, each with a walker."""
    import thestra_camera

    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    camera = thestra_camera.create_or_update_camera(ext.record, make_active=True)
    sheet = PROJECT / 'assets/character/npc_alicia.png'
    frames = []
    for lane in lanes:
        camera.location.y = ext.y(lane)
        walker = thestra_camera.create_actor_preview(
            sheet, camera, anchor=(0.0, ext.y(lane), 0.0), world_height=1.75,
            name=f"PREVIEW_walker_{lane:g}")
        walker.hide_render = False
        path = out_dir / f"{ASSET_ID}_lane_{lane:g}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        walker.hide_render = True
        frames.append(str(path))
    return frames


def save(blend):
    blend = Path(blend).resolve()
    if (ROOT / "projects") in blend.parents:
        raise SystemExit(f"refusing to save the worked example into a Project: {blend}")
    blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    return blend


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog=ASSET_ID)
    parser.add_argument("--blend", type=Path, default=DEFAULT_BLEND)
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--render", type=Path, default=None,
                        help="write native frames (with a walker) into this folder")
    args = parser.parse_args(argv)

    ext = build()
    bpy.context.view_layer.update()
    report, problems = measure(ext)
    if args.render:
        report["frames"] = render(ext, args.render, lanes=(4.0, SPAN / 2.0, 20.0))
    if not args.no_save:
        report["blend"] = str(save(args.blend))
    report["problems"] = problems
    print("EXTERIOR_EXAMPLE " + json.dumps(report, sort_keys=True))
    if problems:
        raise SystemExit("; ".join(problems))


if __name__ == "__main__":
    main()
