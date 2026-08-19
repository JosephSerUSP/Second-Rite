# Authored Tileset Format Architecture & Synthesis

> **Intent, not status.** This document defines the canonical architectural
> recommendation for the authored Tileset format in Second Rite, synthesizing the
> experimental findings of Issue #558 and draft PRs #559, #560, and #561 alongside
> the post-#617 world-presentation realities.
>
> For what exists in the engine right now, see [`docs/ENGINE-STATE.md`](../ENGINE-STATE.md)
> (gated by G4); for live engine mechanics, see [`docs/SPEC.md`](../SPEC.md). Where
> this document and those disagree, they win.
>
> Downstream Issue #547 (Tileset Studio redesign) builds upon the ontology defined
> here.

---

## 1. Executive Summary & Core Principle

### The Principle: Author Loose, Compile Tight

The core principle governing world tile authoring is **Author Loose, Compile Tight**:

- **Authored Truth is Semantic, Readable, and Modular**: Content authors (both
  humans and multimodal AI agents) write high-level, human-readable semantic
  assets. Textures are standalone files with distinct semantic roles (`albedo.png`,
  `height.png`, `emission.png`, `moss_mask.png`). Animations declare independent
  per-property frame sequences and timing. Structural profiles and fixture
  placements are declared as declarative rules.
- **Runtime Normalization is an Implementation Output**: Atlasing, channel
  packing, texture arrays, mesh decimation, prebaking, and GPU pass-slot binding
  are compilation and runtime responsibilities. Authors never manually pack
  disparate scalar fields into the R, G, B, and A channels of an opaque "data"
  texture, nor do they slice half-tile composite textures to simulate corners.

```text
======================= AUTHORED TRUTH (LOOSE) =======================
  Surface Library         Environment Palette         Map & Zone Policy
  - standalone images     - role assignments          - layout grid
  - independent clocks    - structural profiles       - facing-space ownership
  - ordered layer passes  - fixture predicates        - sparse overrides
                          - environment defaults
                              |
                              v
==================== RUNTIME / COMPILER (TIGHT) =====================
  Geometry Prebake        Texture Normalizer          Renderable Bundle
  - profile extrusion     - optional runtime atlas    - unified draw calls
  - height displacement   - channel packing / cache   - exact provenance
  - seam-sealed meshes    - fixed shader pass slots   - DCC / Blender export
```

---

## 2. The Five Decoupled Architectural Layers

The legacy tileset schema conflated texture packing, role assignment, material
properties, height displacement, mesh geometry, fixture placement, and
environmental defaults into a single monolithic JSON record.

We decompose world presentation into **five orthogonal layers of concern**:

```text
+-------------------------------------------------------------------------+
| 1. MAP TOPOLOGY & SPATIAL POLICY                                        |
|    - Logical grid ('#', '.', 'O') owning collision and traversal        |
|    - Facing-space wall face ownership across zone boundaries            |
|    - Sparse cell and material overrides                                 |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| 2. ENVIRONMENT PALETTE                                                  |
|    - Structural role pools: walls, floors, ceilings, wallTops, skies    |
|    - Connective opening & door definitions                              |
|    - Architectural structural profiles (square, chamfer, round, cap)    |
|    - Fixture placement vocabulary & predicates (torches, rubble)        |
|    - Environment presentation defaults (ambient light, fog, panorama)   |
+-------------------------------------------------------------------------+
                                    | references Surface IDs
                                    v
+-------------------------------------------------------------------------+
| 3. SURFACE LIBRARY                                                      |
|    - Atomic visual/material unit (reusable across multiple Palettes)    |
|    - Semantic standalone image sources (albedo, height, emission)       |
|    - Independent property animation clocks                              |
|    - Ordered material overlay passes (blend modes, UV sources)          |
|    - Compatibility adapter for legacy atlas regions                     |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| 4. GEOMETRY & RELIEF                                                    |
|    - Structural profiles define top-down junction outline               |
|    - Invariant: visual geometry ⊆ logical solid cell footprint          |
|    - Height field evaluates relief along face normals                   |
|    - Authored junction meshes override procedural profiles              |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| 5. NORMALIZATION & COMPILER OUTPUT                                      |
|    - Geometry prebake & mesh decimation (seam-sealed, watertight)       |
|    - Runtime texture caching, dynamic atlasing, array binding           |
|    - Renderable Bundle generation with exact authored provenance        |
+-------------------------------------------------------------------------+
```

---

## 3. Synthesis of Experimental Lanes (#559, #560, #561) & Post-#617 Realities

### Lane 1 (#559): Resource Ontology, Reuse, and Migration

#### Why Composable Tileset Imports (Candidate B) Were Rejected
PR #559 tested allowing Tilesets to import sub-tilesets or component libraries.
This immediately introduced severe friction:
1. **Merge Precedence Conflicts**: When an imported library and a local tileset
   both define `stone_wall`, resolving whether weights add, replace, or re-scale
   created opaque authoring rules.
2. **Hidden Cross-Library Dependencies**: A fixture prefab in library A required a
   predicate defined in library B, making modular re-use fragile.
3. **Namespace Pollution**: Authors had to manage deep inheritance graphs.

#### Why Surface Library + Environment Palette (Candidate A) Won
Separating atomic **Surfaces** from **Environment Palettes** proved clean and
frictionless:
- A single Surface (`dungeon_flagstone`) is referenced by multiple Palettes
  (`dungeon_default` and `showcase_thestra`) without duplicating texture paths,
  height parameters, or material layers.
- Palettes focus entirely on role assignment, variant weighting, and environment
  settings.

#### Facing-Space Zone Wall Ownership (Candidate C)
PR #559 demonstrated that Maps containing multiple visual themes (e.g., a
cathedral nave opening into a flooded crypt) do not need full-map atlas duplication
or complex boundary stitching.
- **The Facing-Space Rule**: An exposed wall face is owned by the walkable
  cell it *faces*.
- If a wall at `(5, 5)` separates the default nave from a crypt zone at `(5, 6)`,
  the south face of the wall automatically samples the crypt palette, while the
  north face samples the nave palette.
- Boundary edges resolve deterministically without seam artifacts.

#### 100% Lossless Compatibility Migration
The migration census across all repository tilesets proved that 100% of existing
tilesets migrate losslessly to the new ontology:
- Legacy atlas coordinates are preserved under a synthetic `legacyAtlasRegion`
  Surface adapter.
- Deterministic variant weights and selection algorithms produce identical
  pseudo-random selections across all existing seed points.

---

### Lane 2 (#560): Material Imagery, Animation, and Normalization

#### Why Fixed 4-Channel RGBA Data Packing Was Rejected
1. **Arbitrary Capacity Ceiling**: A 4-channel RGBA texture forces an artificial
   cap. World materials often need albedo, height, emission, and multiple
   semantic overlay masks (e.g., moss, wetness, soot).
2. **Multimodal Agent & Tool Readability**: A standalone `height.png` or
   `emission.png` is immediately inspectable in image viewers, diffable in Git,
   and comprehensible to vision models. Storing height in the Red channel and
   roughness in Green creates uninterpretable sludge for authoring tools.
3. **Decoupled Runtime Consumption**:
   - `height.png` is processed on the **CPU** during geometry generation and
     decimation to produce static 3D vertex meshes.
   - `emission.png` and overlay layers are processed on the **GPU** in fragment
     shaders.
   - Coupling them into one source texture binds CPU mesh generation to GPU
     shader samplers.

#### Independent Property Animation
PR #560 established that material properties must animate on independent clocks:
- **Animated Albedo + Static Height**: Flowing water animates its color sequence
  without forcing continuous CPU mesh recompilations.
- **Static Albedo + Animated Emission**: A flickering torch or pulsating crystal
  modulates its glow map on a 10 fps clock without requiring duplicate albedo
  frames.
- **Explicit Animated Height Boundary**: Animated vertex displacement is
  classified as *animated geometry* (morph targets or vertex shaders), not an
  ordinary material texture clock.

#### Ordered Material Overlay Layers
Adopting the overlay pass model proven by the item material system (`main@fcdc4ea8`):
- Surfaces can declare an ordered list of material layers.
- Each layer specifies an image mask, blend operation (`add`, `multiply`,
  `screen`, `mix`, `subtract`), strength, and UV source (`uv` or `sphere`).
- The compiler maps these layers to fixed runtime shader pass slots.

---

### Lane 3 (#561): Structural Profiles, Junctions, and Collision Truth

#### Decoupling Structure from Surface Material
PR #561 proved that architectural shape must be independent of surface material:
- A `soft-round` profile can be styled with `wet_stone`, `carved_marble`, or
  `rough_wood`.
- A palette or wall variant declares its structural profile (`square`, `chamfer`,
  `round`, `cap`), and the geometry engine constructs the 3D faces accordingly.
- This completely supersedes legacy composite half-tile edge slicing (`middle`,
  `leftEdge`, `rightEdge`), eliminating manual 32px atlas coordination.

#### Geometric Containment Invariant
To ensure collision and traversal remain 100% truthful:
$$\text{visual geometry} \subseteq \text{logical solid cell footprint}$$
- Presentation profiles (e.g., beveling a wall corner) only *remove* solid
  material from the corner of a solid cell; they never protrude into traversable
  space.
- The player never collides with empty air or walks through visible geometry.
- Grid-based navigation and collision detection remain completely untouched.

#### Synthesis: Procedural Profiles with Authored Mesh Overrides
- **Procedural Profiles** (square, 1-cut chamfer, 2–4 segment low-poly round)
  cover 95% of regular architectural needs with zero kit asset overhead.
- **Authored Junction Meshes** (`model: "models/arch_corner.obj"`) serve as
  explicit overrides for extraordinary or highly irregular architectural focal
  points.

---

### Post-#617 Implementation Realities

The synthesis incorporates all production capabilities landed in PR #617:
1. **`wallTops` Role**: Upward-facing wall caps are a first-class structural role
   in Palettes, distinct from ceilings. In overhead perspective (26° FOV) and
   orthographic camera modes, wall tops render with dedicated surface textures
   and height relief.
2. **Resolved Camera & Projection Profiles**: Presentation modes (first-person,
   overhead perspective, orthographic) consume the same resolved surface and
   structural geometry without requiring geometry duplication.
3. **Design-Pixel Density (`pixelsPerTile`)**: Visual art density (e.g., 24
   design pixels per world tile) is cleanly decoupled from physical screen
   resolution and grid collision bounds.

---

## 4. Authored Schema Specifications

### 4.1 Surface Schema (`Surface`)

An atomic visual/material asset definition:

```json
{
  "id": "surface_crypt_wet_stone",
  "name": "Crypt Wet Stone",
  "source": {
    "kind": "standalone"
  },
  "albedo": {
    "image": "assets/surfaces/crypt_stone/albedo.png"
  },
  "height": {
    "image": "assets/surfaces/crypt_stone/height.png",
    "scale": 0.08,
    "offset": 0.0,
    "operation": "replace"
  },
  "emission": {
    "frames": [
      "assets/surfaces/crypt_stone/glow_01.png",
      "assets/surfaces/crypt_stone/glow_02.png",
      "assets/surfaces/crypt_stone/glow_03.png"
    ],
    "fps": 6,
    "strength": 1.2
  },
  "layers": [
    {
      "meaning": "moss_growth",
      "image": "assets/surfaces/crypt_stone/moss_mask.png",
      "blend": "multiply",
      "uvSource": "uv",
      "strength": 0.85
    },
    {
      "meaning": "water_sheen",
      "image": "assets/surfaces/crypt_stone/sheen.png",
      "blend": "add",
      "uvSource": "sphere",
      "strength": 0.4
    }
  ]
}
```

#### Legacy Compatibility Surface Form
For existing atlas-backed tilesets:

```json
{
  "id": "legacy:dungeon_default:walls:0",
  "source": {
    "kind": "legacyAtlasRegion",
    "texture": "assets/tilesets/dungeon.png",
    "tileWidth": 64,
    "tileHeight": 64,
    "atlas": [0, 0]
  },
  "height": {
    "image": "assets/tilesets/dungeon_height.png",
    "scale": 0.1
  }
}
```

---

### 4.2 Environment Palette Schema (`EnvironmentPalette`)

Defines role assignments, structural profiles, fixture rules, and environment
defaults:

```json
{
  "id": "palette_flooded_crypt",
  "name": "Flooded Crypt",
  "base": {
    "walls": [
      { "id": "main_wall", "surface": "surface_crypt_wet_stone", "weight": 70 },
      { "id": "mossy_wall", "surface": "surface_crypt_moss_stone", "weight": 30 }
    ],
    "floors": [
      { "id": "shallow_water", "surface": "surface_crypt_water", "weight": 80 },
      { "id": "broken_slab", "surface": "surface_crypt_slab", "weight": 20 }
    ],
    "ceilings": [
      { "id": "arched_stone", "surface": "surface_crypt_vault", "weight": 100 }
    ],
    "wallTops": [
      { "id": "stone_cap", "surface": "surface_crypt_cap", "weight": 100 }
    ],
    "skies": []
  },
  "doors": [
    { "id": "iron_gate", "surface": "surface_crypt_iron_gate", "weight": 100 }
  ],
  "structuralProfile": {
    "kind": "procedural",
    "corner": "round",
    "radius": 0.12,
    "segments": 3
  },
  "fixturePrefabs": [
    {
      "id": "wall_sconce",
      "model": "assets/models/sconce.obj",
      "where": { "all": ["wall_beside_floor", "not_near_door"] },
      "injectProbability": 0.25,
      "emitsLight": { "color": [1.0, 0.6, 0.2], "radius": 3.5 }
    }
  ],
  "environment": {
    "ambient": [0.15, 0.18, 0.22],
    "fogPreset": "crypt_murk",
    "skyPanorama": null
  }
}
```

---

### 4.3 Map Zone Policy Schema (`MapZonePolicy`)

Maps specify a default Palette and optional regional Zones:

```json
{
  "tileset": "palette_cathedral_nave",
  "zoneGrid": [
    ["", "", "", "crypt", "crypt"],
    ["", "", "", "crypt", "crypt"]
  ],
  "zones": {
    "crypt": {
      "palette": "palette_flooded_crypt",
      "ambient": [0.08, 0.12, 0.15]
    }
  },
  "materialOverrides": {
    "5,3:south": { "surface": "surface_ancient_fresco" }
  }
}
```

---

## 5. Resolver & Normalization Pipeline

The runtime resolution workflow is strictly staged:

```text
Map Data (Layout + ZoneGrid + Overrides)
    |
    v
Resolver (engine/tileset_resolver.lua)
    1. Resolve active Palette for each cell and facing wall face.
    2. Resolve variant selections from weighted pools deterministically by seed.
    3. Dereference Surface IDs -> resolved Surface definitions.
    |
    v
Geometry Compiler (engine/geometry/prebake.lua)
    1. Evaluate Structural Profiles (square, chamfer, round).
    2. Displace vertices along normal using Surface height fields.
    3. Stitch seams and emit watertight polygonal meshes.
    |
    v
Presentation & Renderable Bundle (presentation/map_renderable_bundle.lua)
    1. Bind active albedo / emission frame samplers.
    2. Apply ordered material overlay shader passes.
    3. Retain exact authored asset provenance for tooling & export.
```

---

## 6. Migration Strategy & Backward Compatibility

1. **Zero Breaking Changes**: Existing `data/tilesets/*.json` files continue to
   load and resolve without modification.
2. **Dual-Path Resolution**: The resolver transparently accepts both:
   - Modern `surface: "id"` references.
   - Legacy atlas fields (`atlas: [x, y]`, `texture`, `heightMap`).
3. **Lossless Programmatic Migration**: When an author or build step migrates a
   legacy tileset, it generates discrete Surface records and an Environment
   Palette, preserving 100% of variant IDs, weights, and coordinate data.

---

## 7. Explicitly Stated Unresolved Questions

The following bounded decisions remain open for future downstream work:

1. **Shared Surface Storage Location**:
   - Option A: Single registry file `data/surfaces.json`.
   - Option B: Directory of standalone JSON files `data/surfaces/*.json` (matching
     the `data/tilesets/*.json` storage convention).
   - *Recommendation*: Directory-per-surface under `data/surfaces/*.json` to
     support clean Git diffs and asset co-location (`assets/surfaces/<id>/`).

2. **Riser Material Assignment on Elevation Steps**:
   - When elevation changes create a vertical riser between cell A (higher) and
     cell B (lower), does the riser inherit the material of cell A, cell B, or a
     dedicated transition material declared by the Palette?

3. **Prebaked Geometry Cache Invalidation**:
   - Invalidation keys currently incorporate `heightMap` path and settings. When
     Surfaces become standalone assets, invalidation must hash the Surface's
     `height.image` content hash or timestamp.

4. **In-Editor Preview of Dynamic Multi-Clock Animations**:
   - Tileset Studio in-browser preview needs a lightweight WebGL/Canvas ticker to
     preview independent emission vs albedo animation cycles.

---

## 8. Downstream Scope

- **Issue #547 (Tileset Studio Redesign)**: Remains strictly downstream. It will
  implement the authoring UI for the decoupled **Surface Library** and
  **Environment Palette** surfaces specified herein.
- **No Golden Recapture Required**: This architectural synthesis and resolver
  skeleton preserve 100% backward-compatible rendering output. G1–G6 gates remain
  green without baseline modification.
