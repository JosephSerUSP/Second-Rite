"""Create a tiny CI-only authoritative item .blend for compiler smoke tests.

This file is executed inside Blender. The resulting .blend is transient test
state under the real production source directory so the production compiler's
path and metadata rules are exercised without committing a fake game asset.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import second_rite_asset_core as asset_core

ROOT = SCRIPT_DIR.parents[1]
DEFAULT_PATH = ROOT / "assets" / "authoring" / "items" / "ci_item_source_fixture.blend"


def main():
    asset_core.reset_scene(factory=True)

    root = bpy.data.objects.new("ITEM_ci_item_source_fixture", None)
    bpy.context.scene.collection.objects.link(root)
    root["item_export"] = True
    root["item_export_name"] = "ci_item_source_fixture"
    root["sr_source_authority"] = "blend"
    asset_core.tag_asset_target(
        root,
        asset_id="ci_item_source_fixture",
        representation="full_model",
        role="item_display",
        authoring_space="item_display",
        placement_frame="item_viewport",
    )

    mesh = bpy.data.meshes.new("fixture_body_mesh")
    mesh.from_pydata(
        [
            (-0.55, -0.38, -0.32),
            (0.55, -0.38, -0.32),
            (0.55, 0.38, -0.32),
            (-0.55, 0.38, -0.32),
            (-0.42, -0.30, 0.42),
            (0.42, -0.30, 0.42),
            (0.42, 0.30, 0.42),
            (-0.42, 0.30, 0.42),
        ],
        [],
        [
            (0, 1, 2, 3),
            (4, 7, 6, 5),
            (0, 4, 5, 1),
            (1, 5, 6, 2),
            (2, 6, 7, 3),
            (4, 0, 3, 7),
        ],
    )
    mesh.update()
    body = bpy.data.objects.new("fixture_body", mesh)
    bpy.context.scene.collection.objects.link(body)
    body.parent = root
    asset_core.assign_material(
        body,
        asset_core.make_material("fixture_wrought_iron", semantic_id="wrought_iron"),
    )
    asset_core.add_bevel_modifier(body, width=0.07, segments=1)
    asset_core.flat_shade(body)

    destination = Path(os.environ.get("SECOND_RITE_ITEM_FIXTURE_PATH", DEFAULT_PATH)).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    print(f"WROTE ITEM SOURCE FIXTURE {destination}")


if __name__ == "__main__":
    main()
