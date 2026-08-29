# Shared Second Gate UI language and cross-runtime presentation semantics — audit

**Issue:** #965 (umbrella audit/architecture)
**Audit date:** 2026-08-29
**Audited main:** `8828db43`
**Status:** audit/evidence. No production behavior changes here.
**Related:** #796 (icon-palette mirror extraction), #783 (canonical entity label/icon presentation), #773 (architecture-policy migration), SPEC §1.1.2.

Read this as as-of-`8828db43` evidence. It classifies surfaces and facts; it does
not track delivery.

---

## 1. Headline result

The candidate architecture in #965 is **accepted in part and narrowed in one
material place.**

Accepted:

- one Project-owned, machine-validated **presentation contract** for authored
  visual facts, with explicit revision identity;
- the LÖVE renderer remains the real game renderer;
- restricted TypeScript only for small pure renderer-neutral leaves;
- runtime services for pixels that need real LÖVE/font/shader truth;
- fail-visible missing/incompatible resources.

Narrowed:

> The proposed **"reusable browser adapter that translates the same facts to
> DOM/CSS/Canvas"** is accepted only for *inert theme tokens* — font files,
> colors, pixel-scaling and spacing units. It is **rejected** for windowskin
> 9-slice reconstruction, icon atlas compositing, panel opening geometry and
> typographic measurement/reveal.

The reason is evidential, not stylistic. The duplication #965 fears **does not
exist today**: outside the two already-documented paired cases
(`icon-renderer.js`, `thestra-viewport-contract.js`), a repository-wide search
for windowskin/9-slice/`textPalette`/`fontOffsetY`/`textRevealDelay` consumers in
JavaScript or Python finds **no browser copy of any panel, typography or timing
semantic**. The only JS references to those keys are *authoring form labels* in
`studio/editor/js/widgets.js:1381-1391`, which edit the value and never
interpret it.

Meanwhile the correct mechanism already ships. `studio/editor/server.js:526,598`
expose `POST /preview-window` and `GET /preview-font`, backed by
`runtime-preview-worker.js`, which runs the actual `ui.drawPanel` /
`ui.drawString` headlessly and returns a PNG — `widgets.js:1305-1310` documents
this explicitly as "the real 9-slice windowskin, not an approximation of it".

So building a DOM/Canvas windowskin adapter would **create** the second
presentation authority this issue exists to prevent, in order to replace a
service that is already correct by construction. The audit therefore routes
game-accurate pixels to the existing service and gives browser tools only the
inert tokens.

---

## 2. Current authority map

| Visual fact | Authority today | Consumers | Ownership | Verdict |
|---|---|---|---|---|
| Active font name/size/Y-offset | `data/system.json` `ui.activeFont/fontSize/fontOffsetY` | `ui.init` → `ui.setFont`; `widgets.js` (edits only) | Project (font *files* Project-or-RTP) | Data. Publish in contract. |
| Font files | `assets/fonts/*.ttf`; RTP class via `tools/export/rtp-baseline-resources.js` (`FONT_DIR`) | LÖVE `ui.loadFont`; `GET /api/fonts` listing | Project overrides pinned RTP revision | Data + existing provenance authority. Reusable as `@font-face`. |
| `Lucida` sentinel | `ui.setFont` fallback = LÖVE built-in, no file on disk | mirrored as a *comment* in `widgets.js:1288` | Runtime | Runtime-only. Browsers must render it as "engine default", never guess a substitute face. |
| Text palette (`\c[n]`) | `data/system.json` `ui.textPalette` (8 RGBA entries) | `parseRichText` in `ui.lua:121` | Project | Data. Token-exportable. Parsing stays a semantic leaf (§4). |
| Gauge / cost / tone colors | **hardcoded** `ui.lua:271-303` | `ui.lua` only | Project intent, engine-held | Currently runtime-only. Promoting to data is a separate authored-data question, not a browser question. |
| Windowskin images | `assets/system/windowskin_{back,button,button_highlight}.png` | `ui.init` | Project | Data (asset reference). |
| Windowskin atlas geometry | **hardcoded quads** `ui.lua:196-211` (borders at 32..64, scroll track/thumb at y=32, arrows) | `ui.drawPanel`, `ui.drawScrollbar` | Runtime | **Runtime-only.** See §3.1. |
| Target reticle atlas | hardcoded quads `ui.lua:215-224` over `UI_Target.png` | `ui.drawTargetReticle` | Project asset + runtime geometry | Runtime-only. |
| Role selection (`back`/`button`/`button_highlight`) | `ui.buttonRole` + `drawPanel` role arg | window renderer | Runtime | Runtime-only; it is a draw-time branch, not a fact. |
| Panel opening geometry | `ui.rescaleRect` `ui.lua:348` — equal-pixel-rate both axes, floors 16x9 | panel open/close animation | Runtime | **Pure leaf candidate** (§4.2), but no second consumer exists yet. |
| Panel content origin / tile grid | `ui.panelContentOrigin`, `ui.toPx`, `tileSize=8`, 32x30 tiles | every window renderer | Project convention, engine-held | Constants → contract; the origin *rule* is a pure leaf candidate. |
| Iconset image | `assets/system/iconset.png` | `ui.init`; `icon-renderer.js:31` fetches `/assets/system/iconset.png` | Project | Data (asset reference). |
| Icon atlas addressing | `resolveIconQuad` `ui.lua:882` (10 cols, 8px, 1-based) | runtime; **mirrored** `icon-renderer.js:4-5` | Project layout, engine-held | **Existing duplicate.** Belongs to #796. Do not re-solve here. |
| Icon keying/ramp | `initIconShader` + `resolveIconKeyProfile` `ui.lua:795,938` | runtime shader; **mirrored** `icon-renderer.js:6-12` | Project palettes, engine-held | **Existing duplicate.** #796. |
| Structured icon reference resolution | `ui.resolveIcon` `ui.lua:894` — pure shape normalization | runtime | Engine | Pure leaf candidate (§4.1); interacts with #783. |
| Text normalization | `normalizeText` `ui.lua:598` — 14 fixed UTF-8 → ASCII substitutions, gated by `ui.fontNormalize` | `ui.drawString` | Engine, Project-toggled | **Pure leaf candidate** (§4.1). |
| Text wrapping | `ui.wrapText` `ui.lua:1105` — delegates to `Font:getWrap`, manual path measures with `Font:getWidth` | runtime | Runtime | **Runtime-only.** Requires font rasterization. |
| Reveal timing | `ui.revealedCount` `ui.lua:1142` — bytes/`ui.textRevealDelay`; `utf8Prefix` snaps to a codepoint | runtime | Project timing + engine rule | Split: delay is data; the count+prefix rule is a pure leaf; `revealedLines` needs measurement → runtime. |
| Menu/move/turn/input timings | `data/system.json` `ui.*Duration`, cooldowns, auto-repeat | runtime | Project | Data. Exportable, but no browser tool currently animates like the game. |
| Popup fonts/formats/colors | `system.json` `battle_screen.popup` | `ui.init` | Project | Data. Battle-only; out of scope for every browser tool inventoried. |
| Cursor / waiting / blue-dot | `assets/system/Cursor.png`, `UI_WaitingForInput[fps=30].png`, `UI_BlueDot[fps=15].png` | runtime | Project | Data (asset reference). Frame rate already governed by the `sprite-timing` leaf. |
| Character sprites | `assets/character/town/npc_*.png` (incl. `npc_alicia.png`, `npc_laura.png`) | runtime; resolution rules already shared via `shared/semantics/sprite-resolution.ts` + generated JS/Lua | Project | **Already solved.** Browsers reuse the generated JS; no new authority. |
| Studio editor chrome | `studio/editor/themes.json` (RM2003 desktop palette) | Studio only | Studio | **Separate authority, deliberately.** Must not be merged with the Project contract. |
| Pixel scaling | nearest filter set per-image at load in `ui.init`; 256x240 logical screen | runtime | Engine | Convention → contract token (`image-rendering: pixelated`, integer scale). |

RTP revision identity is `system.json.rtp.revision` (currently `"1.0"`), and
`rtp-baseline-resources.js` already enforces pinned-revision containment plus a
five-field provenance record (`source`, `authorship`, `redistributionStatus`,
`genericReason`, `playerFacingReason`). The theme contract must **consume** that,
not restate it.

---

## 3. Applet and tool inventory

Every HTML/CSS surface in the repository outside `node_modules` and generated
`out/`. There are seven.

### 3.1 NPC Gauntlet Lab — `tools/npc-gauntlet`

- **User / decision:** the owner and agents judging whether proposed NPC dialogue
  and behavior read as Second Gate characters.
- **Current authority:** `lib/sources.js` extracts speaker/text pairs from
  Project `docs/` and `data/` with sha256 provenance per file. Presentation is 2
  lines of generic CSS (`public/app.css`), a 10-line HTML shell and 24 lines of JS.
- **Duplicated facts:** none.
- **Clock:** frame-local for the UI; revision-scoped for source digests.
- **Destination:** class 1 (already-generated sprite resolution) + inert theme
  tokens; **class 3 runtime service** for any panel/dialogue frame that must look
  like the game.
- **Ownership:** Project sources, Project sprites, Project fonts.
- **Verdict — STRONG, and the correct pilot.** Judging whether a line sounds like
  Alicia while it is set in `system-ui` on `#eef1f5` is judging the wrong artifact.
  But the useful inheritance is narrow: the Project font at the Project size and
  offset, the `\c[n]` palette, the pixel-scaling rule, and the character sprite
  beside the line. A dialogue frame rendered through `POST /preview-window` is
  strictly better than a CSS windowskin and costs no new authority.
- **Non-goals:** no gameplay simulation in the browser; no CSS windowskin.

### 3.2 Craft Space — `tools/craft-space`

- **User / decision:** design judgment on Item Creation's discipline/ingredient space.
- **Current authority:** exemplary. `build.py` takes analysis facts from
  `engine.craft` through the read-only `lovec . craft-space-export` CLI mode and
  owns "only the HTML projection, provenance, deterministic serialization, and
  drift check". A `--check` mode gates staleness.
- **Duplicated facts:** none.
- **Clock:** compilation/revision (it is a built static artifact).
- **Verdict — WEAK, contrary to #965's expectation.** The page is a hue-plane
  scatter plot, a value axis, a coverage table and a derivation audit
  (`template.html:104-138`). It is an *analysis instrument*, not a player-adjacent
  surface: there is no window, no menu, no entity list rendered as the player sees
  it. Its dark analytic palette is fit for purpose. Inherit **fonts and the
  `\c[n]`/tone palette only where it labels a real gameplay entity**, and stop
  there. Reskinning a scatter plot in windowskins would make the instrument worse.
- **Non-goal:** do not let theme adoption weaken the existing export/drift gate.

### 3.3 asset-gen UI — `tools/asset-gen/ui`

- **User / decision:** the owner rating generated textures/sprites (`rate.html`,
  `index.html`, 269 CSS lines total).
- **Verdict — REJECT, with one exception.** Production-tool chrome. Game framing
  would actively confuse review here: a texture must be judged against the
  *material*, and a rating UI dressed as a game menu invites judging the frame.
  The exception is any preview that claims to show how an asset will look
  **in-game** — that must come from the runtime service, not from CSS, and it
  must not become a rating surface's decoration.

### 3.4 Studio — `studio/editor`

- **Verdict — SPLIT, already correctly.** `themes.json` and `surface-host.css`
  own editor chrome and stay untouched (#965 non-goal). Player-preview surfaces
  (Scenes, Windows, font picker, icon picker) already consume real pixels via
  `preview-*`, except the icon picker, whose mirror is #796's.
  **Studio needs nothing from this issue.** Its role here is as the *reference
  implementation* the other tools copy.

### 3.5 Walkthrough — `projects/hichaukitoden-game/docs/walkthrough`

- **Not named in #965; found by the inventory.** A Project-owned, player-facing
  prose walkthrough with its own magazine styling and `images/title.png`.
- **Verdict — MODERATE, deferred.** It is the only genuinely *player-facing*
  browser surface in the repository, so it has the strongest claim to the
  Project's typography. But it is prose, not UI, and #783 explicitly warns
  against turning arbitrary web prose into runtime entity UI. Font and palette
  inheritance is defensible; entity-name/icon rendering is not, until #783 lands
  a canonical presentation to consume.

### 3.6 Golden/comparison galleries and generated reports

- Emitted by `tools/golden/record-core.py`, `tools/golden/screens.py`,
  `tools/asset-gen/lib/report.py` and the overnight runners.
- **Verdict — REJECT, explicitly. Evidence tooling.** A gallery's job is to make
  a pixel difference visible. Second Gate chrome around a G5 frame is visual noise
  competing with the evidence, and worse, risks a reader mistaking harness chrome
  for shipped pixels. Keep them neutral.

### 3.7 Encounter Lab / labs / design-critique

- Python-only, no browser surface (`encounter_lab.py`, `critique_renders.py`,
  `tools/labs/*.py`). **Not applicable.**

---

## 4. Cross-runtime semantic candidates

The calibration bar is the three landed leaves: 138, 156 and 187 lines, each pure,
deterministic, renderer-neutral, and each with a *real* second host executing it.

### 4.1 Justified now (conditional on a second consumer existing)

**`text-normalization`** — `normalizeText` (`ui.lua:598-628`).
Small (14 substitutions), pure, deterministic, host-neutral, byte-oriented, and
gated by one Project boolean. Current authority: `ui.lua`. Current consumers:
`ui.drawString` only. It becomes a leaf the moment a browser tool renders Project
prose in a pixel font — which is exactly the Gauntlet pilot, where an unnormalized
curly quote is the difference between reading a line and reading a tofu box.
Parity gate: the same substitution matrix in Node and real LÖVE/LuaJIT, plus the
existing "no regrown handwritten duplicate" assertion.

**`icon-reference-resolution`** — `ui.resolveIcon` (`ui.lua:894-919`).
Pure shape normalization over four authored spellings (`number`, `.icon`,
`.icon.id`, `.iconPalette`/`.palette`) with an empty-string-to-nil rule. No
graphics context. Independently testable. It is the *addressing* half of #783's
canonical presentation, and separating it means #783 and #796 can each consume
one resolution rule instead of two. **Must be its own issue**, not bundled.

**`rich-text-parse`** — `parseRichText` (`ui.lua:121-172`).
Splits `\c[N]` runs against `ui.textPalette`. Pure given the palette. Justified
only alongside `text-normalization`; on its own it has no second consumer.

### 4.2 Candidate, not yet justified

**`panel-open-geometry`** — `ui.rescaleRect` (`ui.lua:348-356`). Pure and
genuinely subtle (equal *pixel* rate, not equal fraction; 16x9 floors). But its
only plausible second host is a browser panel animation, which §1 rejects.
Record it; do not extract it.

**`content-origin`** — `ui.panelContentOrigin`. Pure but four lines. Below the
bar; ship it as contract constants instead.

**`reveal-count`** — `ui.revealedCount` + `ui.utf8Prefix`. Pure and correct
(the UTF-8 continuation-byte walk is easy to get wrong twice). Justified only if
a browser tool actually animates a reveal. `revealedLines` is **not** a
candidate: it measures with `Font:getWidth`.

### 4.3 Rejected — runtime/service truth

`ui.wrapText`, `ui.measureText`, `ui.fitText`, `ui.revealedLines` (font
rasterization); `drawPanel`, `drawScrollbar`, `drawTargetReticle`, `drawBar`,
`drawIcon` (LÖVE resource lookup, quads, shaders, draw state); `ui.init`
(filesystem probing and image caching); the icon shader (GPU). Every one of these
is served to a browser today, or can be, by `preview-*`.

---

## 5. Proposed contract shape

One Project-owned publication (working name `data/presentation.json`, or a
validated projection of the existing `system.json.ui` — the audit does not fix
the filename) carrying **only facts already authored elsewhere**, plus identity:

- font: name, size, offsetY, normalize flag, and the resolved file path or the
  `Lucida` engine-default sentinel;
- palettes: `textPalette`, and the tone/cost colors *if* they are first promoted
  out of `ui.lua` by separate authored-data work;
- asset references: windowskin trio, iconset, cursor set, target skin — as paths
  with their Project/RTP ownership and the pinned RTP revision;
- units: `tileSize`, logical screen tiles, gauge height, pixel-scaling rule;
- timings: the `ui.*Duration` / cooldown / auto-repeat / reveal-delay set.

Rules:

1. **It publishes, it does not decide.** Any value present in `system.json` is
   read from there. A second spelling of the same number is a validation failure.
2. **Identity.** Content hash over every contributing source, asset and the RTP
   revision. Browser caches key on it. This is the compilation/revision clock.
3. **Fail visible.** A missing asset or an unresolvable font is an explicit error
   state in the consumer — never a silent CSS fallback, and never an invented
   default value. `ui.init` already models the honest version of this: a skin
   whose file is missing falls back to `back` *deliberately*, because "a panel
   that draws nothing is worse than a panel wearing the wrong skin".
4. **The LÖVE renderer does not consume it as authority.** It stays a derived
   publication; making `ui.lua` read it would invert the direction and put a
   generated file upstream of the game.

Gates: a stale-output check in the shared-semantics style; a validator asserting
every published value is byte-equal to its authored source; and an assertion that
no browser surface has regrown a handwritten windowskin/atlas/typography copy —
the negative control that makes this contract enforceable rather than advisory.

**G5 remains shipped rendering truth; G6 remains Studio visual truth. Nothing in
a browser tool authorizes a golden recapture.**

---

## 6. Issue topology

Foundation, strictly chronological:

1. **Theme/asset contract + validation** (§5). Blocks everything below.
2. **Browser theme-token consumer + freshness gate.** Deliberately small:
   `@font-face` from the Project font, CSS custom properties from the palettes,
   the pixel-scaling rule, contract-identity cache keying, and the
   no-regrown-duplicate negative control. **Not** a windowskin/icon/typography
   renderer.
3. **Pilot: NPC Gauntlet Lab**, including Alicia/Laura sprite presentation via
   the existing generated `sprite-resolution` JS, and dialogue frames via
   `preview-window` where a real frame is wanted.

Then, in parallel, each bounded and separate: Craft Space entity-label
inheritance (narrow, per §3.2); walkthrough typography (§3.5, gated on #783);
any asset-review in-game preview that must come from the service (§3.3).

Independently, one issue each, not bundled into the adapter:
`text-normalization`, `icon-reference-resolution`, `rich-text-parse` — and each
only when its second consumer actually exists.

#796 and #783 remain their own coordinated work. This audit hands #796 the icon
atlas addressing and keying rows of §2 unchanged, and hands #783 the
`icon-reference-resolution` leaf as a dependency it may consume.

---

## 7. Non-goals restated

Reimplementing the LÖVE UI renderer in JavaScript; making every engineering tool
look like the game; reskinning Studio editor chrome; moving mutable gameplay,
simulation, validation, Test Play or final rendering into TypeScript; changing
any art asset or UI design; folding #796 or #783 into this work.
