# Round 0 — Evidence and Integration Audit

**Date:** 2026-08-15  
**Target:** 128×128 Front-View World-Event Character Sprites (Registrar Celina, Sister Agnes, The Gambler)  
**Branch:** `main`  

---

## 1. Codebase Baseline and Inspection

- **Engine:** LÖVE2D (Lua 5.1 / LuaJIT) with raycaster / first-person 3D viewport (`presentation/viewport_3d.lua`).
- **Validation:** All cross-references and engine invariants pass (`lovec . validate` -> `VALIDATE OK`).
- **Tools:** Blender 5.1 (`C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`), Python 3.10 with Pillow 9.5.0.

---

## 2. Character Authored Appearances & References

### A. Registrar Celina
- **Location:** St. Maria (Map 1, `data/maps/1.json`).
- **Event Definition:** Event ID 13 (`"name": "Registrar"`, `"label": "Registrar Celina"`, coordinates `x=11, y=6`).
- **Interaction:** Handles the Crossing Writ. Holds out hand for the Summoner's seal ("Your Summoner's seal. Not your name. We keep those separate here.") and records it in a narrow ledger.
- **Tone/Persona:** Severe, composed, watchful, dry bureaucratic sense of mortality. Formal colonial tailoring.
- **Existing Portrait:** `assets/portraits/NPC_Registrar_Celina.png` (Copic/ink style dialogue portrait).
- **Existing World Sprite:** `assets/sprites/NPC06.png` (48×64 placeholder).

### B. Sister Agnes
- **Location:** St. Maria (Map 1, `data/maps/1.json`).
- **Event Definition:** Event ID 12 (`"name": "EV012"`, `"label": "Sister Agnes"`, coordinates `x=9, y=6`).
- **Interaction:** Found repairing the chapel stone steps with a patience better suited to embroidery. Brushes stone dust from sleeves. Offers quiet without faking certainty ("If you need quiet, the chapel is open. If you need certainty, try somewhere else.").
- **Tone/Persona:** Calm, physically present, unpretentious chapel caretaker with stone dust on sleeves.
- **Existing Portrait:** `assets/portraits/NPC_Sister_Agnes.png`.
- **Existing World Sprite:** `assets/sprites/NPC11.png` (170×170 placeholder, also mirrored as `assets/sprites/NPC_SisterAgnes.png`).

### C. The Gambler
- **Location:** St. Maria (Map 1, `data/maps/1.json`).
- **Event Definition:** **Not an independent world map event.** He is an interactive sub-branch within Event ID 8 (`"name": "Pub Owner"`, coordinates `x=14, y=13`, which represents the entrance and interior hub of The Rusty Tankard pub).
- **Interaction:** Triggered via "Look for a table" -> `random() < 0.4` roll. Shuffling cards in a dimly lit corner. "A collector of sorts. A collector of... numbers." Offers a high/low number guessing game for 10 Gold.
- **Tone/Persona:** Conversational, slightly strange, number-obsessed, hands and fingers always active.
- **Existing Portrait:** `assets/portraits/NPC_Gambler.png` (640×192 dialogue sheet).
- **Existing World Sprite:** None. Does not have a standalone map billboard event.

---

## 3. Current World Sprite Paths & Event Standalone Status

| Character | Standalone Map Event? | Current Sprite Path | Shared with Other Events? |
|---|---|---|---|
| **Registrar Celina** | Yes (Map 1, EV 13) | `assets/sprites/NPC06.png` | **Yes** (Map 1 EV 10, Map 8 EV 1) |
| **Sister Agnes** | Yes (Map 1, EV 12) | `assets/sprites/NPC11.png` | **Yes** (Map 8 EV 3, Map 9 EV 2) |
| **The Gambler** | **No** (Inside Pub EV 8) | N/A | N/A |

### Critical Integration Rule:
Because `NPC06.png` and `NPC11.png` are shared across other map events, **we must not overwrite generic `NPCxx.png` files.**  
We must produce dedicated production sprites:
- `assets/sprites/event_registrar_celina.png`
- `assets/sprites/event_sister_agnes.png`
- `assets/sprites/event_the_gambler.png`

---

## 4. Current First-Person Billboard Renderer Architecture

In `presentation/viewport_3d.lua`:
- Event sprites are resolved via `getEventSprite(rawEv, session)` using `viewport_3d.resolveEventSpritePath(ev, session)`.
- When `not rawEv.wallEvent` and `presentation.visual == "sprite"`, `addBillboard(image, rawEv.x, rawEv.y)` is called.
- `addBillboard` places a vertical quad centered at `(x + 1.5, y + 1.5)`:
  - Width: 1.0 world units (`rightX * 0.5` half-width).
  - Height: 1.0 world units (`z = 0` to `z = 1`).
  - UV coordinates: `(0, 1)` at bottom to `(1, 0)` at top.
  - Image filter: `nearest, nearest`.
- As the player moves through the dungeon or village, the perspective raycaster/shader dynamically scales the quad based on camera distance and angle.
- Vertex colors provide height-based and distance-based lighting/fog.

---

## 5. Lessons & Evidence from PR #599 (Tiny 3D Character Pipeline)

PR #599 explored 24×24 top-down chibis. Key findings to adopt vs adapt:

1. **What to Adopt:**
   - **Zero White Outline / Edge Dilation:** Render on transparent film with pure black world (`(0,0,0,1)`), then dilate genuine surface RGB colors into 0-alpha margin pixels before downscaling.
   - **Authoritative Editable `.blend` Sources:** All models authored procedurally or hand-tuned in Blender, saved to `assets/authoring/characters/`.
   - **Multi-scale Torture Testing:** Always test against contrasting backgrounds (pitch black, dungeon slate, masonry, parchment, checkerboard).

2. **What to Change for 128×128 Front-View:**
   - **Camera Grammar:** Level front-view (eye/chest height, long-lens/orthographic), NOT 32-degree top-down.
   - **Proportions:** 5.25–5.75 heads tall (stylized adults), NOT 2.5-head chibis.
   - **Acting Priorities:** Head inclination, shoulder line, expressive hands, torso lean, costume masses.
   - **Alpha Edge:** At 128×128, test both binary alpha and controlled steep alpha curves (rather than assuming 24×24 binary is optimal).

---

## 6. Safe Runtime Integration Roadmap

1. **Production Assets:**
   - Author models in `assets/authoring/characters/`.
   - Bake final 128×128 RGBA PNGs to `assets/sprites/event_registrar_celina.png` and `assets/sprites/event_sister_agnes.png`.
2. **Map 1 Event References:**
   - Celina (Event 13): Change `"sprite": "assets/sprites/NPC06.png"` to `"sprite": "assets/sprites/event_registrar_celina.png"`.
   - Agnes (Event 12): Change `"sprite": "assets/sprites/NPC11.png"` to `"sprite": "assets/sprites/event_sister_agnes.png"`.
3. **The Gambler:**
   - Asset `assets/sprites/event_the_gambler.png` will be ready in `assets/sprites/`.
   - We will document the integration gap without inventing an unsanctioned map event.
