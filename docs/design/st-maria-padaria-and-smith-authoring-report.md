# St. Maria Interior Authoring: Alicia's Padaria & Laura's Smith

## 1. Executive Summary

This document records the full design, multi-model contest deliberation, shared grammar expansion, and verified 3D environment authoring for **Alicia's Padaria** (*A Padaria da Alicia*) and **Laura's Smith** (*A Forja da Laura*) in St. Maria.

Both environments were authored against the fixed camera and movement contract in `docs/design/st-maria-interior-authoring.md`, verified through the camera-calibrated staging pipeline (`tools/blender/stage_room_model.py`), and validated against all project gates.

---

## 2. Multi-Model Contest Pitches & Adversarial Critique

To ensure high architectural quality and strict adherence to the colonial Portuguese brief, we executed an adversarial design contest utilizing **OpenRouter** (`nvidia/nemotron-3-super-120b-a12b:free`, `minimax/minimax-m2.7:free`) and **OpenAI** (`gpt-4o-mini`, `gpt-4o`).

### 2.1 Contest Transcripts Summary

#### Alicia's Padaria
- **Pitches**:
  - `gpt-4o-mini`: Emphasized the wood-fired baking oven in an alcove, hardwood customer counter with Laura's lunch bundle, scales, and apothecary shelves.
  - `nvidia/nemotron-3-super-120b-a12b:free`: Proposed an L-shaped division of labour with kneading tables, floor flour sacks, and ceiling herb rails.
- **Adversarial Critique (`gpt-4o`)**:
  - *Key Ruling*: Enforce **Single-Axis Discipline**. The baking oven alcove with header on the back wall is the primary axis. Reject any competing side window to preserve the alcove as the singular architectural statement. Motivate lighting strictly from the oven embers, wall lanterns, and doorway bounce light.
  - *Winning Synthesis*: Alcove with header (`back_wall(alcoves=[(0.35, 3.25, 1.25)], arch_z=2.65)`), bread oven with glowing embers, peeling table with fresh broas, mercantile shelves with apothecary draughts, and Alicia's neatly wrapped lunch cloth bundle on the counter.

#### Laura's Smith
- **Pitches**:
  - `gpt-4o-mini`: Focused on the smith's working triangle (forge -> anvil on cepo -> slack tub -> workbench).
  - `nvidia/nemotron-3-super-120b-a12b:free`: Pitched high chiaroscuro contrast between incandescent forge embers and cool morning daylight.
  - `minimax/minimax-m2.7:free`: Emphasized heavy iron tools, ingot stacks, and weapon display racks.
- **Adversarial Critique (`gpt-4o`)**:
  - *Key Ruling*: Spend the **Side Window** axis (`side_walls(openings={1: [...]})`). Raking cool daylight across the dark forge hearth, grindstone, quench tub, and anvil creates a striking visual contrast against the deep warm orange of the forge fire, differentiating the smithy from both Room 3 and Alicia's Padaria.
  - *Winning Synthesis*: Side window raking daylight across the room, heavy stone forge hearth with chimney and bellows, anvil on banded hardwood stump, slack tub with resting tongs, rotary grindstone, heavy workbench with vice, and weapon display racks.

---

## 3. Shared Grammar Expansion (`furnishings.py`)

The shared furnishings module was significantly enhanced with 9 reusable, low-poly, single-mesh pieces:

1. **`mercantile_shelf`**: Freestanding 3-tier merchant display shelf (*estante de mercearia*) loaded with ceramic crocks, unglazed earthenware jars, and bronze tins.
2. **`apothecary_rack`**: Wall-hung apothecary rack with cubby slots holding summoner potion vials, water flasks, and herbal packets.
3. **`hanging_rack`**: Ceiling-suspended timber beam with iron hooks carrying cured sausages, garlic braids, and dried herbs.
4. **`grain_bin`**: Heavy slatted wooden chest with angled lid, interior flour bed, and carved wooden scoop.
5. **`counter_dressing`**: Tabletop set featuring an open ledger book, iron inkpot with quill, and Alicia's wrapped lunch cloth bundle.
6. **`grindstone`**: Rotary sharpening stone (*rebolo*) on timber A-frame trestle with foot treadle and water drip trough.
7. **`fuel_bunker`**: Low timber charcoal hopper (*carvoeira*) with iron coal shovel.
8. **`armor_stand`**: Hardwood cross-buck display stand (*manequim de armadura*) holding a forged iron cuirass blank and pauldrons.
9. **`slack_tub_dressed`**: Enhanced quench tub with resting forged iron tongs.

---

## 4. Architectural Implementation Details

| Property | Alicia's Padaria (`alicias_padaria.py`) | Laura's Smith (`lauras_smith.py`) |
|---|---|---|
| **Asset ID** | `alicias_padaria` | `lauras_smith` |
| **Room Dimensions** | Width: ~9.6m (Classic 256px), Depth: 6.4m, Ceiling: 3.5m | Width: ~8.6m (Classic 256px), Depth: 6.6m, Ceiling: 3.6m |
| **Primary Axis Spent** | **Alcove** with header (`y0=0.35, y1=3.25, depth=1.25, arch_z=2.65`) | **Side Window** (`x0=back_x-4.2, x1=back_x-2.0, z0=1.35, z1=2.75`) |
| **Floor Material** | Terracotta tile | Terracotta tile |
| **Wall Material** | Limewash (*caiação*) with waist-high azulejo dado | Limewash (*caiação*) with waist-high azulejo dado |
| **Key Focal Pieces** | Bread oven in alcove, merchant counter with lunch bundle, mercantile & apothecary shelves, grain bin, kneading table | Stone forge hearth with hood & bellows, anvil on cepo, quench tub, rotary grindstone, weapon rack, workbench & vice |
| **Motivated Lighting** | Oven fire glow (`55W`, amber), back window daylight (`240W`), wall lantern (`22W`), doorway bounce (`24W`) | Forge fire glow (`75W`, red-orange), side window rake (`260W`), workbench lantern (`24W`), doorway bounce (`24W`) |
| **Movement Contract** | Outward extruded exit threshold (`Y=143`) | Outward extruded exit threshold (`Y=143`) |

---

## 5. Verification & Camera Calibration Results

Staging was executed using `stage_room_model.py` and Blender 5.1 EEVEE rendering:

```json
{
  "camera": "tools/blender/fixtures/town_sideview_camera.json",
  "actor": {
    "feetPx": [128.0, 128.0],
    "headPx": [128.0, 80.0],
    "pixelHeight": 48.0,
    "characterFloorLimit": 144.0,
    "headroomAboveLimit": 16.0
  },
  "expectedPixelHeight": 48.0,
  "pixelHeightError": 0.0,
  "materialsRebound": [],
  "engine": "BLENDER_EEVEE"
}
```

- **Walker Scale**: Exactly 48.000px height (0.000px error).
- **Character Floor Limit**: Feet project to native Y=128.0, maintaining a safe 16.0px headroom above the Y=144 floor limit.
- **Outliner Cleanliness**: All multi-box furnishings are joined inside `Interior.piece` into single named mesh objects.
- **Project Gates**: `validate`, `unittest`, `savetest`, and `material_library check` all pass with 0 errors.
