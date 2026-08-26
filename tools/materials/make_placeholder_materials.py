"""High-fidelity procedural PBR textures for the Second Gate material library.

Generates complete PBR texture sets (Albedo, Normal Map, Height, Roughness, Metallic)
with physically structured surface relief for authentic colonial Portuguese architecture:
- dark_wood: Bevelled plank runs with wood grain pores, sawmill chatters, and anisotropic sheen.
- terracotta: Rectangular floor tile courses with recessed grout, clay pitting, and edge bevels.
- azulejo: Vitreous tin-glaze (faianca) with gloss, cobalt motifs, and bevelled tile grout.
- whitewash: Caiacao brushed lime plaster with directional brushwork and chalky texture.
- rough_limestone: Chiseled stone masonry blocks with deep mortar recesses and mineral grain.
- old_limestone: Troweled interior lime mortar with smooth float marks and micro-cavities.
- wrought_iron: Hammered iron with ball-peen dimpling, scale pitting, and metallic highlights.
- forge_scale: Heat-treated iron with flaky slag oxidation relief.
- charcoal: Fractured carbon lumps with sharp cleavage planes and ash dusting.
- bread_crust: Blistered crust with deep oven scoring fissures and flour dusting.
- aged_cloth: Interlocking linen/burlap weave with slub fibers.

Generates byte-identically from fixed seeds with CC0-1.0 licensing and SHA-256 provenance.

Run:
    python tools/materials/make_placeholder_materials.py
    python tools/materials/make_placeholder_materials.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import material_library  # noqa: E402

SIZE = 512
LICENSE = "CC0-1.0"


def rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def tiling_noise(seed: int, frequency: int, octaves: int = 4) -> np.ndarray:
    """Periodic value noise: built at low resolution and tiled by wrapping."""
    total = np.zeros((SIZE, SIZE), dtype=np.float64)
    amplitude, weight = 1.0, 0.0
    generator = rng(seed)
    for octave in range(octaves):
        cells = frequency * (2 ** octave)
        grid = generator.random((cells, cells))
        ys = np.linspace(0, cells, SIZE, endpoint=False)
        xs = np.linspace(0, cells, SIZE, endpoint=False)
        y0 = np.floor(ys).astype(int) % cells
        x0 = np.floor(xs).astype(int) % cells
        y1, x1 = (y0 + 1) % cells, (x0 + 1) % cells
        fy = (ys - np.floor(ys))[:, None]
        fx = (xs - np.floor(xs))[None, :]
        sy, sx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
        top = grid[np.ix_(y0, x0)] * (1 - sx) + grid[np.ix_(y0, x1)] * sx
        bottom = grid[np.ix_(y1, x0)] * (1 - sx) + grid[np.ix_(y1, x1)] * sx
        total += (top * (1 - sy) + bottom * sy) * amplitude
        weight += amplitude
        amplitude *= 0.5
    return total / weight


def compute_normal_map(height: np.ndarray, strength: float = 3.5) -> np.ndarray:
    """Compute tangent space Normal Map (RGB) from height field via Sobel filter."""
    h = height.astype(np.float64) / 255.0
    # Wrap-around central difference gradient
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * strength * 0.5
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * strength * 0.5
    dz = np.ones_like(h)

    # Normalize vectors
    length = np.sqrt(dx * dx + dy * dy + dz * dz)
    nx = (dx / length) * 0.5 + 0.5
    ny = (-dy / length) * 0.5 + 0.5  # OpenGL / Blender convention
    nz = (dz / length) * 0.5 + 0.5

    normal_rgb = np.stack([nx, ny, nz], axis=-1)
    return np.clip(normal_rgb * 255.0, 0, 255).astype(np.uint8)


def colourise(height: np.ndarray, low, high) -> np.ndarray:
    normalised = (height - height.min()) / max(height.ptp(), 1e-6)
    low_arr = np.array(low, dtype=np.float64)
    high_arr = np.array(high, dtype=np.float64)
    return low_arr + (high_arr - low_arr) * normalised[..., None]


# --- Procedural PBR Generators ----------------------------------------------

def gen_dark_wood(seed: int):
    """Jacaranda / Vinhatico: Bevelled floor planks, distinct grain pores, and satin gloss."""
    gen = rng(seed)
    plank_count = 6
    plank_h = SIZE / plank_count
    yy = np.arange(SIZE)[:, None] * np.ones((1, SIZE))
    p_idx = (yy / plank_h).astype(int)
    p_rel = (yy % plank_h) / plank_h  # 0.0 to 1.0 within plank

    # Bevelled seams: deep V-groove at top/bottom of each plank
    seam_dist = np.minimum(p_rel, 1.0 - p_rel)
    seam_bevel = np.clip(seam_dist * 12.0, 0.0, 1.0)
    seam_crevice = (seam_dist < 0.035) * 0.65

    # Plank tone variations
    plank_tone = gen.uniform(0.82, 1.18, size=plank_count)[p_idx % plank_count]

    # Wood grain fibers (elongated horizontally)
    fine_grain = tiling_noise(seed + 1, 2, 4) * 0.25 + tiling_noise(seed + 2, 20, 2) * 0.12
    vessels = (tiling_noise(seed + 3, 32, 2) > 0.72) * 0.15

    # Sawmill chatter marks (subtle vertical ribbing across planks)
    chatter = np.sin(np.arange(SIZE)[None, :] * math.tau * 14 / SIZE) * 0.04

    height_field = np.clip(seam_bevel * 0.75 + fine_grain * 0.20 - vessels - seam_crevice + chatter, 0.0, 1.0)
    height = (height_field * 255).astype(np.uint8)
    normal = compute_normal_map(height, strength=4.2)

    # Albedo: deep walnut with rich reddish-brown undertones
    albedo = np.clip(colourise(height_field * plank_tone, (36, 22, 14), (96, 68, 44)), 0, 255).astype(np.uint8)

    # Roughness: satin wood finish (0.42-0.62) with rougher seams (0.85)
    roughness = (np.clip(0.44 + (1.0 - seam_bevel) * 0.40 + fine_grain * 0.15, 0.0, 1.0) * 255).astype(np.uint8)
    return albedo, normal, height, roughness, None


def gen_terracotta(seed: int):
    """Fired clay floor tiles with recessed grout, edge chipping, and warm baked tone."""
    gen = rng(seed)
    rows_count, cols_count = 5, 4
    row_h, col_w = SIZE / rows_count, SIZE / cols_count
    yy = np.arange(SIZE)[:, None] * np.ones((1, SIZE))
    xx = np.ones((SIZE, 1)) * np.arange(SIZE)[None, :]

    row = (yy / row_h).astype(int)
    offset = (row % 2) * (col_w / 2.0)
    col = (((xx + offset) % SIZE) / col_w).astype(int)

    # Distance to tile border (for bevel & grout)
    fy = (yy % row_h) / row_h
    fx = ((xx + offset) % col_w) / col_w
    dist_y = np.minimum(fy, 1.0 - fy)
    dist_x = np.minimum(fx, 1.0 - fx)
    edge_dist = np.minimum(dist_y * (row_h / col_w), dist_x)

    tile_bevel = np.clip(edge_dist * 8.5, 0.0, 1.0)
    grout = (edge_dist < 0.04) * 0.75

    # Baked clay surface grit and micro-pits
    clay_grit = tiling_noise(seed + 4, 8, 4) * 0.22 + tiling_noise(seed + 5, 24, 2) * 0.12
    tile_tone = gen.uniform(0.85, 1.15, size=(rows_count, cols_count))[row % rows_count, col % cols_count]

    height_field = np.clip(tile_bevel * 0.80 + clay_grit * 0.20 - grout, 0.0, 1.0)
    height = (height_field * 255).astype(np.uint8)
    normal = compute_normal_map(height, strength=4.5)

    # Albedo: warm burnt orange and rich terracotta clay
    albedo = np.clip(colourise(height_field * tile_tone, (115, 48, 28), (195, 105, 68)), 0, 255).astype(np.uint8)
    # Grout is dusty grey-beige
    grout_mask = (grout > 0.1)
    albedo[grout_mask] = (140, 130, 118)

    # Roughness: unglazed clay (0.65-0.78), rougher grout (0.90)
    roughness = (np.clip(0.65 + (1.0 - tile_bevel) * 0.25 + clay_grit * 0.10, 0.0, 1.0) * 255).astype(np.uint8)
    return albedo, normal, height, roughness, None


def gen_azulejo(seed: int):
    """Tin-glazed tile (faianca): High-gloss glaze pillowing, painted cobalt motifs, and grout."""
    tiles = 6
    pitch = SIZE / tiles
    yy = np.arange(SIZE)[:, None] * np.ones((1, SIZE))
    xx = np.ones((SIZE, 1)) * np.arange(SIZE)[None, :]

    fy = (yy % pitch) / pitch - 0.5
    fx = (xx % pitch) / pitch - 0.5

    # Tile pillowing / edge bevel
    dist_edge = np.minimum(0.5 - np.abs(fx), 0.5 - np.abs(fy))
    tile_pillow = np.sin(np.clip(dist_edge * math.pi * 2.0, 0.0, math.pi / 2.0))
    grout = (dist_edge < 0.035) * 0.85

    # Four-lobed traditional Portuguese azulejo motif
    radius = np.hypot(fx, fy)
    angle = np.arctan2(fy, fx)
    lobes = 0.28 + 0.09 * np.cos(4.0 * angle)
    motif = np.exp(-((radius - lobes) ** 2) / 0.0025)
    centre = np.exp(-(radius ** 2) / 0.004)
    corner = np.exp(-((np.abs(fx) - 0.42) ** 2 + (np.abs(fy) - 0.42) ** 2) / 0.0018)

    # Subtle glaze waviness (ondulacao de faianca)
    glaze_wave = tiling_noise(seed + 6, 4, 3) * 0.14
    height_field = np.clip(tile_pillow * 0.85 + glaze_wave * 0.15 - grout, 0.0, 1.0)
    height = (height_field * 255).astype(np.uint8)
    normal = compute_normal_map(height, strength=4.0)

    # Albedo: pure tin-white glaze with deep cobalt blue ink
    ink = np.clip(motif * 0.90 + centre * 0.70 + corner * 0.60, 0.0, 1.0)
    albedo = np.clip(colourise(1.0 - ink * 0.85, (42, 78, 142), (242, 244, 240)), 0, 255).astype(np.uint8)
    albedo[dist_edge < 0.035] = (128, 124, 116)  # Grout color

    # Roughness: very glossy vitreous tin-glaze (0.18-0.32), matte grout (0.85)
    roughness_val = np.clip(0.20 + (1.0 - tile_pillow) * 0.25 + (dist_edge < 0.035) * 0.60, 0.0, 1.0)
    roughness = (roughness_val * 255).astype(np.uint8)
    return albedo, normal, height, roughness, None


def gen_whitewash(seed: int):
    """Caiacao: Brushed slaked lime plaster with subtle brush lines, micro-pores, and chalky matte."""
    broad_trowel = tiling_noise(seed + 7, 3, 4) * 0.45
    # Directional brush strokes (horizontal sweep)
    brush = tiling_noise(seed + 8, 12, 3) * 0.30 + np.sin(np.arange(SIZE)[:, None] * math.tau * 24 / SIZE) * 0.05
    pores = (tiling_noise(seed + 9, 36, 2) > 0.82) * 0.14

    height_field = np.clip(0.65 + broad_trowel * 0.20 + brush * 0.15 - pores, 0.0, 1.0)
    height = (height_field * 255).astype(np.uint8)
    normal = compute_normal_map(height, strength=3.2)

    # Albedo: warm chalky ivory / bone limewash
    albedo = np.clip(colourise(height_field, (208, 204, 192), (246, 244, 238)), 0, 255).astype(np.uint8)
    # Roughness: highly diffuse matte lime (0.82-0.95)
    roughness = (np.clip(0.84 + broad_trowel * 0.12, 0.0, 1.0) * 255).astype(np.uint8)
    return albedo, normal, height, roughness, None


def gen_rough_limestone(seed: int):
    """Chiseled stone blocks with deep mortar channels and mineral fracture relief."""
    gen = rng(seed)
    rows_count, cols_count = 6, 4
    row_h, col_w = SIZE / rows_count, SIZE / cols_count
    yy = np.arange(SIZE)[:, None] * np.ones((1, SIZE))
    xx = np.ones((SIZE, 1)) * np.arange(SIZE)[None, :]

    row = (yy / row_h).astype(int)
    offset = (row % 2) * (col_w / 2.0)
    col = (((xx + offset) % SIZE) / col_w).astype(int)

    fy = (yy % row_h) / row_h
    fx = ((xx + offset) % col_w) / col_w
    edge_dist = np.minimum(np.minimum(fy, 1.0 - fy) * (row_h / col_w), np.minimum(fx, 1.0 - fx))

    block_bevel = np.clip(edge_dist * 7.5, 0.0, 1.0)
    mortar = (edge_dist < 0.045) * 0.80

    chisel = tiling_noise(seed + 10, 8, 4) * 0.35 + tiling_noise(seed + 11, 28, 2) * 0.18
    block_tone = gen.uniform(0.82, 1.18, size=(rows_count, cols_count))[row % rows_count, col % cols_count]

    height_field = np.clip(block_bevel * 0.75 + chisel * 0.25 - mortar, 0.0, 1.0)
    height = (height_field * 255).astype(np.uint8)
    normal = compute_normal_map(height, strength=4.8)

    albedo = np.clip(colourise(height_field * block_tone, (88, 82, 70), (155, 146, 128)), 0, 255).astype(np.uint8)
    albedo[mortar > 0.1] = (112, 106, 96)
    roughness = (np.clip(0.78 + (1.0 - block_bevel) * 0.18 + chisel * 0.08, 0.0, 1.0) * 255).astype(np.uint8)
    return albedo, normal, height, roughness, None


def gen_old_limestone(seed: int):
    """Aged interior plaster with smooth trowel passes, hairline fissures, and patina."""
    broad = tiling_noise(seed + 12, 3, 4) * 0.50
    trowel = tiling_noise(seed + 13, 7, 3) * 0.30
    pores = (tiling_noise(seed + 14, 28, 2) > 0.78) * 0.12

    height_field = np.clip(0.60 + broad * 0.25 + trowel * 0.15 - pores, 0.0, 1.0)
    height = (height_field * 255).astype(np.uint8)
    normal = compute_normal_map(height, strength=3.0)

    albedo = np.clip(colourise(height_field, (126, 118, 102), (175, 168, 148)), 0, 255).astype(np.uint8)
    roughness = (np.clip(0.74 + broad * 0.18, 0.0, 1.0) * 255).astype(np.uint8)
    return albedo, normal, height, roughness, None


def gen_wrought_iron(seed: int):
    """Hammered wrought iron: Ball-peen dimpling, scale pits, and metallic specular highlights."""
    dimples = tiling_noise(seed + 15, 6, 3) * 0.45
    fine_pits = tiling_noise(seed + 16, 24, 2) * 0.22

    height_field = np.clip(0.55 + dimples * 0.30 - fine_pits * 0.18, 0.0, 1.0)
    height = (height_field * 255).astype(np.uint8)
    normal = compute_normal_map(height, strength=4.5)

    # Albedo: dark oxidized charcoal-grey iron
    albedo = np.clip(colourise(height_field, (28, 28, 26), (62, 62, 58)), 0, 255).astype(np.uint8)
    # Metallic map (iron metalness ~ 0.85)
    metallic = (np.clip(0.80 + dimples * 0.15, 0.0, 1.0) * 255).astype(np.uint8)
    # Roughness: polished hammer faces (0.35) to scaled crevices (0.65)
    roughness = (np.clip(0.38 + (1.0 - dimples) * 0.28, 0.0, 1.0) * 255).astype(np.uint8)
    return albedo, normal, height, roughness, metallic


def gen_forge_scale(seed: int):
    """Heat-treated iron with flaky slag oxidation relief and heat bands."""
    flake = tiling_noise(seed + 17, 5, 4) * 0.40
    pits = tiling_noise(seed + 18, 24, 2) * 0.28
    heat_band = np.sin(np.arange(SIZE)[:, None] * math.tau * 3 / SIZE) * 0.08

    height_field = np.clip(0.48 + flake * 0.32 + heat_band - pits * 0.15, 0.0, 1.0)
    height = (height_field * 255).astype(np.uint8)
    normal = compute_normal_map(height, strength=4.2)

    albedo = np.clip(colourise(height_field, (52, 44, 36), (160, 135, 95)), 0, 255).astype(np.uint8)
    metallic = (np.clip(0.60 + flake * 0.25, 0.0, 1.0) * 255).astype(np.uint8)
    roughness = (np.clip(0.52 + (1.0 - flake) * 0.30, 0.0, 1.0) * 255).astype(np.uint8)
    return albedo, normal, height, roughness, metallic


def gen_charcoal(seed: int):
    """Fractured carbon lumps with sharp cleavage facets and deep crevice voids."""
    lumps = tiling_noise(seed + 19, 6, 4) * 0.50
    grit = tiling_noise(seed + 20, 28, 2) * 0.25

    height_field = np.clip(lumps * 0.70 + grit * 0.30, 0.0, 1.0)
    height = (height_field * 255).astype(np.uint8)
    normal = compute_normal_map(height, strength=5.2)

    albedo = np.clip(colourise(height_field, (10, 9, 8), (55, 50, 44)), 0, 255).astype(np.uint8)
    roughness = (np.clip(0.88 + (1.0 - lumps) * 0.10, 0.0, 1.0) * 255).astype(np.uint8)
    return albedo, normal, height, roughness, None


def gen_bread_crust(seed: int):
    """Artisan broa crust: Deep scoring fissures, blisters, and flour dusting."""
    broad = tiling_noise(seed + 21, 4, 4) * 0.38
    blisters = (tiling_noise(seed + 22, 16, 2) > 0.65) * 0.25
    # Scoring cuts (fissures across bread)
    slash = (np.sin(np.arange(SIZE)[None, :] * math.tau * 5 / SIZE + tiling_noise(seed + 23, 3, 2) * 2.0) > 0.85) * 0.40

    height_field = np.clip(0.50 + broad * 0.30 + blisters * 0.20 - slash, 0.0, 1.0)
    height = (height_field * 255).astype(np.uint8)
    normal = compute_normal_map(height, strength=4.5)

    albedo = np.clip(colourise(height_field, (105, 48, 16), (225, 155, 78)), 0, 255).astype(np.uint8)
    # Pale flour dusting on high points
    albedo[height_field > 0.78] = (232, 218, 192)
    roughness = (np.clip(0.68 + broad * 0.20, 0.0, 1.0) * 255).astype(np.uint8)
    return albedo, normal, height, roughness, None


def gen_aged_cloth(seed: int):
    """Interlocking linen/burlap weave with slub fibers and soft fabric roughness."""
    threads = 50
    warp = np.sin(np.arange(SIZE) * math.tau * threads / SIZE)[None, :]
    weft = np.sin(np.arange(SIZE) * math.tau * threads / SIZE)[:, None]
    slub = tiling_noise(seed + 24, 10, 3) * 0.35

    height_field = np.clip(0.50 + 0.22 * (warp * weft) + slub * 0.25, 0.0, 1.0)
    height = (height_field * 255).astype(np.uint8)
    normal = compute_normal_map(height, strength=3.8)

    albedo = np.clip(colourise(height_field, (82, 64, 48), (142, 118, 92)), 0, 255).astype(np.uint8)
    roughness = (np.clip(0.86 + slub * 0.10, 0.0, 1.0) * 255).astype(np.uint8)
    return albedo, normal, height, roughness, None


RECIPES = {
    "dark_wood": dict(seed=1101, gen=gen_dark_wood, world=2.0,
                      note="Plank runs for floors, partitions, beams and doors."),
    "rough_limestone": dict(seed=2203, gen=gen_rough_limestone, world=2.5,
                            note="Staggered masonry courses for exterior walls and hearths."),
    "old_limestone": dict(seed=3307, gen=gen_old_limestone, world=3.0,
                          note="Interior lime mortar and plaster."),
    "whitewash": dict(seed=5501, gen=gen_whitewash, world=3.0,
                      note="Caiacao: Default wall of a colonial Portuguese town."),
    "azulejo": dict(seed=6607, gen=gen_azulejo, world=0.9,
                    note="Blue-and-white tin-glazed tile, 6x6 tiles per 0.9m."),
    "terracotta": dict(seed=7703, gen=gen_terracotta, world=1.6,
                       note="Fired clay: pantiles, floor tile, unglazed pottery."),
    "aged_cloth": dict(seed=4409, gen=gen_aged_cloth, world=1.2,
                       note="Bedding, sacking, hangings, lunch cloth."),
    "wrought_iron": dict(seed=8819, gen=gen_wrought_iron, world=1.0,
                         note="Anvil faces, grilles, bands, weapons, hinges."),
    "bread_crust": dict(seed=8801, gen=gen_bread_crust, world=0.34,
                        note="Baked crust with scoring and flour-pale pores."),
    "forge_scale": dict(seed=9901, gen=gen_forge_scale, world=0.28,
                        note="Heat-darkened, pitted iron for worked surfaces."),
    "charcoal": dict(seed=10103, gen=gen_charcoal, world=0.42,
                     note="Matte dusty charcoal for hearths."),
}


def build(semantic_id: str, spec: dict, directory: Path, *, write: bool) -> dict:
    albedo, normal, height, roughness, metallic = spec["gen"](spec["seed"])

    files = {
        "albedo.png": Image.fromarray(albedo, "RGB"),
        "normal.png": Image.fromarray(normal, "RGB"),
        "height.png": Image.fromarray(height, "L"),
        "roughness.png": Image.fromarray(roughness, "L"),
    }
    maps = {
        "albedo": "albedo.png",
        "normal": "normal.png",
        "height": "height.png",
        "roughness": "roughness.png",
    }
    if metallic is not None:
        files["metallic.png"] = Image.fromarray(metallic, "L")
        maps["metallic"] = "metallic.png"

    if write:
        directory.mkdir(parents=True, exist_ok=True)
        for name, image in files.items():
            image.save(directory / name, optimize=True)

    hashes = {}
    for name in files:
        path = directory / name
        if path.is_file():
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()

    record = {
        "materialKind": material_library.MATERIAL_KIND,
        "version": material_library.MATERIAL_VERSION,
        "semanticId": semantic_id,
        "status": "placeholder",
        "worldSizeMetres": spec["world"],
        "maps": maps,
        "notes": spec["note"],
        "provenance": {
            "origin": "procedural",
            "generator": "tools/materials/make_placeholder_materials.py",
            "seed": spec["seed"],
            "license": LICENSE,
            "retrieved": "2026-08-26",
            "sha256": hashes,
        },
    }
    if write:
        (directory / "material.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(prog="make_placeholder_materials")
    parser.add_argument("--check", action="store_true",
                        help="regenerate in memory and verify the tracked files")
    parser.add_argument("--project", type=Path, default=None)
    args = parser.parse_args()

    root = material_library.library_root(args.project)
    failures = 0
    for semantic_id, spec in sorted(RECIPES.items()):
        directory = root / semantic_id
        if args.check:
            existing = material_library.load(semantic_id, args.project)
            if existing is None:
                print(f"{semantic_id}: MISSING")
                failures += 1
                continue
            problems = material_library.validate(existing)
            print(f"{semantic_id}: {'ok' if not problems else 'FAILED'}")
            for problem in problems:
                print(f"    - {problem}")
            failures += len(problems)
        else:
            build(semantic_id, spec, directory, write=True)
            print(f"{semantic_id}: wrote {directory}")
    if failures:
        raise SystemExit(f"{failures} problem(s)")


if __name__ == "__main__":
    main()
