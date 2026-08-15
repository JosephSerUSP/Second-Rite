"""Run the one-shot C source bootstrap with legacy C migration adapters.

Batch C wrote authored coordinates directly to OBJ, where +Y is up. Production
Blender source is +Z-up and the shared exporter converts Blender -> OBJ as
``(x, y, z) -> (x, z, -y)``, so preserved C points map into Blender as
``(x, -z, y)``.

Batch C also authored sphere-map sheen in its shared MTL. The editable sources
store those effects on Blender materials as ``sr_runtime_passes_json`` so the
production compiler, rather than this one-shot bootstrap, owns MTL emission.

These adapters disappear after the initial .blend documents are materialized;
the resulting files contain ordinary Blender-space geometry plus explicit
material metadata and become source authority after visual review.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

source_path = SCRIPT_DIR / "bootstrap_c_item_sources.py"
source = source_path.read_text(encoding="utf-8")

coordinate_needle = "        point.co = (*co, 1.0)\n"
coordinate_replacement = (
    "        x, y, z = co\n"
    "        point.co = (x, -z, y, 1.0)  # legacy C/OBJ -> Blender +Z-up\n"
)
if source.count(coordinate_needle) != 1:
    raise RuntimeError("C bootstrap coordinate assignment changed; review migration adapter")
source = source.replace(coordinate_needle, coordinate_replacement)

materials_needle = (
    "def mats():\n"
    "    return {mid: asset_core.make_material(mid, semantic_id=mid) for mid in MATERIAL_IDS}\n"
)
materials_replacement = (
    "def mats():\n"
    "    result = {mid: asset_core.make_material(mid, semantic_id=mid) for mid in MATERIAL_IDS}\n"
    "    result['ritual_gold']['sr_runtime_passes_json'] = "
    "'[{\"uvSource\":\"sphere\",\"blend\":\"add\",\"strength\":1.0,\"texture\":\"assets/models/matcaps/gold.png\"}]'\n"
    "    result['crystal']['sr_runtime_passes_json'] = "
    "'[{\"uvSource\":\"sphere\",\"blend\":\"add\",\"strength\":1.0,\"texture\":\"assets/models/matcaps/ruby.png\"}]'\n"
    "    return result\n"
)
if source.count(materials_needle) != 1:
    raise RuntimeError("C bootstrap material factory changed; review migration adapter")
source = source.replace(materials_needle, materials_replacement)

exec(compile(source, str(source_path), "exec"), {"__name__": "__main__", "__file__": str(source_path)})
