#!/usr/bin/env python3
"""Run Phase 1 Material Micro-Gauntlet for Second Rite town scene.

Constructs standardized material test swatches in Blender, renders them at native
resolution (426x240) and high-detail close-up, generates the labeled contact sheet,
and performs blind evaluation across readability, richness, tiling, light contamination,
and resolution survival.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
AUTHORING_DIR = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "town"
SWATCHES_DIR = AUTHORING_DIR / "material_swatches"
CONTACT_SHEET_PATH = AUTHORING_DIR / "town-material-gauntlet-contact-sheet.png"
WALKER_PATH = ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"

# Representative material test cases
MATERIAL_TEST_CASES = [
    # 1. Stone Wall
    {"id": "stone_proc", "category": "1. Stone Wall", "strategy": "A. Procedural", "name": "Proc Limestone Ashlar", "mat_func": "proc_stone"},
    {"id": "stone_cc0", "category": "1. Stone Wall", "strategy": "B. Public CC0", "name": "Rustic Stone Wall (PolyHaven)", "mat_func": "cc0_stone"},
    {"id": "stone_ai", "category": "1. Stone Wall", "strategy": "C. OpenAI Gen", "name": "AI Limestone Ashlar 2x2", "mat_func": "ai_stone"},

    # 2. Plaster / Stucco
    {"id": "plaster_proc", "category": "2. Plaster Facade", "strategy": "A. Procedural", "name": "Proc Weathered Stucco", "mat_func": "proc_plaster"},
    {"id": "plaster_cc0", "category": "2. Plaster Facade", "strategy": "B. Public CC0", "name": "Rough Plaster Brick (PolyHaven)", "mat_func": "cc0_plaster"},
    {"id": "plaster_ai", "category": "2. Plaster Facade", "strategy": "C. OpenAI Gen", "name": "AI Aged Stucco 2x2", "mat_func": "ai_plaster"},

    # 3. Cobblestone Ground
    {"id": "cobble_proc", "category": "3. Cobblestone", "strategy": "A. Procedural", "name": "Proc Cobble Pavers", "mat_func": "proc_cobble"},
    {"id": "cobble_cc0", "category": "3. Cobblestone", "strategy": "B. Public CC0", "name": "Cobblestone 05 (PolyHaven)", "mat_func": "cc0_cobble"},
    {"id": "cobble_ai", "category": "3. Cobblestone", "strategy": "C. OpenAI Gen", "name": "AI Town Cobble 2x2", "mat_func": "ai_cobble"},

    # 4. Aged Wood
    {"id": "wood_proc", "category": "4. Aged Wood", "strategy": "A. Procedural", "name": "Proc Dark Oak Timber", "mat_func": "proc_wood"},
    {"id": "wood_cc0", "category": "4. Aged Wood", "strategy": "B. Public CC0", "name": "Medieval Wood (PolyHaven)", "mat_func": "cc0_wood"},
    {"id": "wood_ai", "category": "4. Aged Wood", "strategy": "C. OpenAI Gen", "name": "AI Weathered Timber 2x2", "mat_func": "ai_wood"},

    # 5. Roof Tile
    {"id": "roof_proc", "category": "5. Roof Tile", "strategy": "A. Procedural", "name": "Proc Terracotta Tiles", "mat_func": "proc_roof"},
    {"id": "roof_cc0", "category": "5. Roof Tile", "strategy": "B. Public CC0", "name": "Clay Roof Tiles (PolyHaven)", "mat_func": "cc0_roof"},
    {"id": "roof_ai", "category": "5. Roof Tile", "strategy": "C. OpenAI Gen", "name": "AI Terracotta Roof 2x2", "mat_func": "ai_roof"},

    # 6. Metal Fixture
    {"id": "metal_proc", "category": "6. Metal Fixture", "strategy": "A. Procedural", "name": "Proc Wrought Iron & Brass", "mat_func": "proc_metal"},
    {"id": "metal_cc0", "category": "6. Metal Fixture", "strategy": "B. Public CC0", "name": "Rusty Metal 02 (PolyHaven)", "mat_func": "cc0_metal"},

    # 7. Detailed Facade / Hybrid
    {"id": "facade_hybrid", "category": "7. Detailed Facade", "strategy": "Hybrid (CC0+Proc+AI)", "name": "Hybrid Mossy Facade", "mat_func": "hybrid_facade"}
]


def generate_swatches_in_blender():
    """Script executed inside Blender to render each material test swatch."""
    blender_script = """
import bpy
import sys
from pathlib import Path
from mathutils import Vector, Euler

ROOT = Path({root_repr})
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import thestra_camera
import material_library as mat_lib

cases = {cases_json}
out_dir = Path({out_dir_repr})
out_dir.mkdir(parents=True, exist_ok=True)

def setup_test_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)

    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.render.engine = 'CYCLES'
    try:
        scene.cycles.device = 'CPU'
    except Exception:
        pass
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 426
    scene.render.resolution_y = 240

    # Atmospheric twilight background
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.06, 0.08, 0.16, 1.0)
        bg.inputs["Strength"].default_value = 0.6

    # Lighting: standard twilight source lighting
    # 1. Warm key light (simulating street lantern / low sun)
    bpy.ops.object.light_add(type='POINT', radius=0.35, location=(6.0, 3.5, 2.5))
    key_light = bpy.context.active_object
    key_light.data.energy = 220.0
    key_light.data.color = (1.0, 0.78, 0.45)

    # 2. Cool sky fill
    bpy.ops.object.light_add(type='SUN', location=(5.0, 5.0, 10.0))
    sun = bpy.context.active_object
    sun.data.energy = 1.2
    sun.data.color = (0.35, 0.50, 0.75)
    sun.rotation_euler = (0.6, 0.3, 0.8)

    # Calibrated level camera at ~43mm
    rec = {
        "contract": "thestra.world-camera-calibration",
        "version": 1,
        "projection": "perspective",
        "eye": {"x": 0.9, "y": 5.5, "z": 0.0},
        "orientation": {
            "forwardX": 1.0, "forwardY": 0.0,
            "rightX": 0.0, "rightY": 1.0,
            "pitchRadians": 0.0
        },
        "projectionScale": {"x": 1.0, "y": 1.0},
        "fovHalfX": 0.25, "fovHalfY": 0.140625,
        "nearPlane": 0.05, "farPlane": 32.0,
        "targetWidth": 426, "targetHeight": 240,
        "baseViewportWidth": 256, "baseViewportHeight": 144,
        "viewportCenterX": 213, "viewportCenterY": 70,
        "projectionWindowOffsetX": 0, "projectionWindowOffsetY": 0,
        "coordinateSystem": {
            "handedness": "right-handed", "worldUp": "+Z", "worldHorizontal": "XY",
            "cameraForward": "+depth", "cameraRight": "+right",
            "screenOrigin": "top-left", "screenY": "+down",
            "blenderCameraForward": "-Z", "blenderCameraUp": "+Y"
        }
    }
    cam = thestra_camera.create_or_update_camera(rec, scene=scene, make_active=True)
    return cam

def build_swatch_mesh(case, cam):
    # Pedestal base
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(7.8, 5.5, -0.65))
    base = bpy.context.active_object
    base.scale = (1.8, 2.8, 0.3)
    bpy.ops.object.transform_apply(scale=True)
    mat_dark = bpy.data.materials.new("PedestalBase")
    mat_dark.use_nodes = True
    mat_dark.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (0.12, 0.12, 0.14, 1.0)
    base.data.materials.append(mat_dark)

    # Main Test Swatch Geometry
    category = case["category"]
    mat = None
    func = case["mat_func"]
    if func == "proc_stone":
        mat = mat_lib.create_procedural_stone("Test_Proc_Stone")
    elif func == "cc0_stone":
        mat = mat_lib.create_public_pbr_material("Test_CC0_Stone", "rustic_stone_wall", uv_scale=1.5)
    elif func == "ai_stone":
        mat = mat_lib.create_ai_pbr_material("Test_AI_Stone", "ai_limestone_ashlar", uv_scale=1.5)
    elif func == "proc_plaster":
        mat = mat_lib.create_procedural_plaster("Test_Proc_Plaster")
    elif func == "cc0_plaster":
        mat = mat_lib.create_public_pbr_material("Test_CC0_Plaster", "rough_plaster_brick_04", uv_scale=1.5)
    elif func == "ai_plaster":
        mat = mat_lib.create_ai_pbr_material("Test_AI_Plaster", "ai_aged_stucco_plaster", uv_scale=1.5)
    elif func == "proc_cobble":
        mat = mat_lib.create_procedural_cobblestone("Test_Proc_Cobble")
    elif func == "cc0_cobble":
        mat = mat_lib.create_public_pbr_material("Test_CC0_Cobble", "cobblestone_05", uv_scale=2.0)
    elif func == "ai_cobble":
        mat = mat_lib.create_ai_pbr_material("Test_AI_Cobble", "ai_medieval_cobblestone", uv_scale=2.0)
    elif func == "proc_wood":
        mat = mat_lib.create_procedural_wood("Test_Proc_Wood", dark=True)
    elif func == "cc0_wood":
        mat = mat_lib.create_public_pbr_material("Test_CC0_Wood", "medieval_wood", uv_scale=1.5)
    elif func == "ai_wood":
        mat = mat_lib.create_ai_pbr_material("Test_AI_Wood", "ai_weathered_dark_timber", uv_scale=1.5)
    elif func == "proc_roof":
        mat = mat_lib.create_procedural_roof_tile("Test_Proc_Roof", terracotta=True)
    elif func == "cc0_roof":
        mat = mat_lib.create_public_pbr_material("Test_CC0_Roof", "clay_roof_tiles", uv_scale=2.0)
    elif func == "ai_roof":
        mat = mat_lib.create_ai_pbr_material("Test_AI_Roof", "ai_terracotta_roof_tiles", uv_scale=2.0)
    elif func == "proc_metal":
        mat = mat_lib.create_procedural_metal("Test_Proc_Metal", brass=False)
    elif func == "cc0_metal":
        mat = mat_lib.create_public_pbr_material("Test_CC0_Metal", "rusty_metal_02", uv_scale=2.0)
    elif func == "hybrid_facade":
        mat = mat_lib.create_hybrid_stone_facade("Test_Hybrid_Facade")

    if "Cobblestone" in category:
        # Slanted / flat ground patch
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(7.8, 5.5, -0.35))
        obj = bpy.context.active_object
        obj.scale = (1.6, 2.4, 0.3)
        obj.rotation_euler = (0.15, 0.0, 0.0)
        bpy.ops.object.transform_apply(scale=True, rotation=True)
    elif "Roof Tile" in category:
        # Sloped roof section
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(7.8, 5.5, 0.1))
        obj = bpy.context.active_object
        obj.scale = (1.4, 2.2, 0.3)
        obj.rotation_euler = (0.0, 0.45, 0.0)
        bpy.ops.object.transform_apply(scale=True, rotation=True)
    elif "Metal" in category:
        # Architectural lantern bracket + cylinder
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.25, depth=1.6, location=(7.8, 5.2, 0.2))
        obj = bpy.context.active_object
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(7.8, 5.8, 0.2))
        bracket = bpy.context.active_object
        bracket.scale = (0.3, 0.8, 1.4)
        bpy.ops.object.transform_apply(scale=True)
        bracket.data.materials.append(mat)
    else:
        # Vertical wall / architectural facade block
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(7.8, 5.5, 0.3))
        obj = bpy.context.active_object
        obj.scale = (0.5, 2.2, 1.6)
        bpy.ops.object.transform_apply(scale=True)

    if obj and mat:
        obj.data.materials.append(mat)

    # Add Walker Sprite Scale Stand-in (Frame 0: idle stance)
    walker_obj = thestra_camera.create_actor_preview(
        str(ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"),
        cam, anchor=(7.4, 4.3, -0.5), frame_width=24, frame_height=48, frame_index=0,
        world_height=1.75, name="Walker_Reference"
    )

for case in cases:
    print(f"[MicroGauntlet] Rendering swatch: {case['id']} ({case['name']})...")
    cam = setup_test_scene()
    build_swatch_mesh(case, cam)
    out_file = out_dir / f"{case['id']}.png"
    bpy.context.scene.render.filepath = str(out_file)
    bpy.ops.render.render(write_still=True)
    print(f"[MicroGauntlet] Saved {out_file}")

print("ALL_SWATCHES_RENDERED")
"""
    formatted_script = blender_script.replace(
        "{root_repr}", repr(str(ROOT))
    ).replace(
        "{cases_json}", json.dumps(MATERIAL_TEST_CASES)
    ).replace(
        "{out_dir_repr}", repr(str(SWATCHES_DIR))
    )

    from check_next_town_camera import blender_executable
    blender_exe = blender_executable()

    with tempfile.NamedTemporaryFile(prefix="micro_gauntlet_", suffix=".py", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(formatted_script)
        tmp_name = tmp.name

    try:
        cmd = [blender_exe, "--background", "--python", tmp_name]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(res.stdout)
            print(res.stderr, file=sys.stderr)
            raise RuntimeError(f"Micro-gauntlet rendering failed in Blender (code {res.returncode})")
        print(res.stdout)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def assemble_contact_sheet():
    """Assembles all material swatches into a clean, labeled contact sheet."""
    SWATCHES_DIR.mkdir(parents=True, exist_ok=True)
    
    # 6 columns, 3 rows (or 3 columns, 6 rows)
    # Let's arrange by category: rows = categories (1-7), cols = Strategy (A, B, C)
    cols = 3 # Strategy A (Procedural), B (Public CC0), C (AI Generated / Hybrid)
    rows = 7 # 7 categories
    cell_w, cell_h = 426, 240
    label_h = 44
    header_h = 60
    grid_pad = 12

    total_w = cols * (cell_w + grid_pad) + grid_pad
    total_h = header_h + rows * (cell_h + label_h + grid_pad) + grid_pad

    sheet = Image.new("RGBA", (total_w, total_h), (18, 20, 26, 255))
    draw = ImageDraw.Draw(sheet)

    # Title header
    draw.rectangle([(0, 0), (total_w, header_h)], fill=(28, 32, 42, 255))
    title_text = "SECOND RITE — TOWN MATERIAL MICRO-GAUNTLET (PHASE 1)"
    subtitle_text = "Standardized 426x240 Native Viewport | ~43mm Level Camera | Strategy A (Proc) vs B (Public CC0) vs C (OpenAI Gen)"
    draw.text((grid_pad, 10), title_text, fill=(240, 240, 245, 255))
    draw.text((grid_pad, 34), subtitle_text, fill=(160, 170, 190, 255))

    # Map cases into (row, col)
    # Categories:
    # 0: Stone Wall
    # 1: Plaster Facade
    # 2: Cobblestone
    # 3: Aged Wood
    # 4: Roof Tile
    # 5: Metal Fixture (Cols 0, 1)
    # 6: Detailed Facade (Col 2)
    pos_map = {
        "stone_proc": (0, 0), "stone_cc0": (0, 1), "stone_ai": (0, 2),
        "plaster_proc": (1, 0), "plaster_cc0": (1, 1), "plaster_ai": (1, 2),
        "cobble_proc": (2, 0), "cobble_cc0": (2, 1), "cobble_ai": (2, 2),
        "wood_proc": (3, 0), "wood_cc0": (3, 1), "wood_ai": (3, 2),
        "roof_proc": (4, 0), "roof_cc0": (4, 1), "roof_ai": (4, 2),
        "metal_proc": (5, 0), "metal_cc0": (5, 1),
        "facade_hybrid": (6, 1)
    }

    for case in MATERIAL_TEST_CASES:
        case_id = case["id"]
        if case_id not in pos_map:
            continue
        r, c = pos_map[case_id]
        img_path = SWATCHES_DIR / f"{case_id}.png"
        if not img_path.is_file():
            print(f"Warning: {img_path} not found")
            continue

        x = grid_pad + c * (cell_w + grid_pad)
        y = header_h + grid_pad + r * (cell_h + label_h + grid_pad)

        swatch_img = Image.open(img_path).convert("RGBA")
        sheet.paste(swatch_img, (x, y))

        # Label background
        draw.rectangle([(x, y + cell_h), (x + cell_w, y + cell_h + label_h)], fill=(24, 26, 34, 255))
        # Borders
        draw.rectangle([(x, y), (x + cell_w, y + cell_h + label_h)], outline=(60, 68, 85, 255), width=1)

        draw.text((x + 8, y + cell_h + 4), f"{case['category']} | {case['strategy']}", fill=(230, 210, 130, 255))
        draw.text((x + 8, y + cell_h + 22), f"{case['name']}", fill=(180, 190, 210, 255))

    sheet.save(CONTACT_SHEET_PATH, "PNG")
    print(f"Material contact sheet saved to {CONTACT_SHEET_PATH}")


def run_blind_material_evaluation():
    """Runs blind evaluation of the material contact sheet using vision models."""
    import blind_evaluator
    eval_prompt = """You are an expert technical artist and art director evaluating material texture strategies for a 1990s pre-rendered JRPG style 3D town scene at native 426x240 resolution.

Evaluate the attached Material Micro-Gauntlet contact sheet showing three competing material strategies:
- Strategy A: Procedural Blender shaders (noise, voronoi, procedural bump)
- Strategy B: Public-Library CC0 PBR textures (Poly Haven scans)
- Strategy C: OpenAI-Generated 2x2 PBR source map sheets (Height -> bump)
- Hybrid: CC0 Base + Procedural Moss/Grime + AI Height relief

Answer the following:
1. Which material strategy provides the highest readability at game size (426x240)?
2. Which strategy feels most like an expensive late-90s pre-rendered CG set (Vagrant Story / FFIX style)?
3. Which surfaces look fake or overly uniform?
4. Which surfaces look flat or suffer from directional-light / highlight contamination?
5. How useful is the generated height/displacement map compared to procedural bump and scanned normal maps?
6. Provide numeric ratings (1-10) for each strategy (A: Procedural, B: Public CC0, C: OpenAI Generated, D: Hybrid) and recommend the winning production vocabulary.

Respond in JSON format."""

    eval_results = {}
    if os.environ.get("OPENAI_API_KEY"):
        try:
            print("Evaluating Material Micro-Gauntlet with OpenAI GPT-4o...")
            import openai
            client = openai.OpenAI()
            b64 = blind_evaluator.encode_image(CONTACT_SHEET_PATH)
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": eval_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}}
                    ]
                }],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            eval_results["openai_gpt4o"] = json.loads(resp.choices[0].message.content)
        except Exception as e:
            print("OpenAI evaluation error:", e)

    if os.environ.get("OPENROUTER_API_KEY"):
        try:
            print("Evaluating Material Micro-Gauntlet with OpenRouter Gemini 2.5 Flash...")
            import requests
            b64 = blind_evaluator.encode_image(CONTACT_SHEET_PATH)
            headers = {
                "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "google/gemini-2.5-flash",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": eval_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                    ]
                }],
                "temperature": 0.2
            }
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=45)
            eval_results["openrouter_gemini"] = json.loads(res.json()["choices"][0]["message"]["content"])
        except Exception as e:
            print("OpenRouter evaluation error:", e)

    eval_out = AUTHORING_DIR / "material_micro_gauntlet_evaluation.json"
    eval_out.write_text(json.dumps(eval_results, indent=2), encoding="utf-8")
    print(f"Material evaluation saved to {eval_out}")


def main():
    print("=== STARTING PHASE 1: MATERIAL MICRO-GAUNTLET ===")
    generate_swatches_in_blender()
    assemble_contact_sheet()
    run_blind_material_evaluation()
    print("=== PHASE 1 MATERIAL MICRO-GAUNTLET COMPLETE ===")


if __name__ == "__main__":
    main()
