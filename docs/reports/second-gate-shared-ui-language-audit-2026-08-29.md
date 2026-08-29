# Shared Second Gate UI language and cross-runtime presentation semantics — audit

**Issue:** #965 (umbrella audit/architecture)
**Audit date:** 2026-08-29
**Audited main:** `8828db43`
**Status:** audit/evidence. No production behavior changes here.
**Related:** #796 (icon-palette mirror extraction), #783 (canonical entity label/icon presentation), #773 (architecture-policy migration), SPEC §1.1.2.

Read this as as-of-`8828db43` evidence. It classifies surfaces and facts; it does
not track delivery.

---

## 1. Decision

The candidate architecture in #965 is **accepted, including the full browser
adapter**: a reusable package that renders Second Gate windowskins, icons and
typography to DOM/CSS/Canvas, not merely a set of inert theme tokens.

An earlier draft of this audit proposed narrowing the adapter to fonts, colors
and units, on the grounds that no browser copy of those semantics exists today
and that `POST /preview-window` / `GET /preview-font`
(`studio/editor/server.js:526,598`) already return real LÖVE pixels. The owner
rejected that narrowing. The full adapter is the accepted direction, and the rest
of this audit is written to make it **safe**, not to relitigate it.

Safety here has one precise meaning, and it is the whole content of the decision:

> A browser adapter that draws a windowskin is only legitimate if the facts it
> draws from are **promoted out of `ui.lua` into shared authority first**. An
> adapter that reads hardcoded Lua quads and retypes them as JavaScript
> constants is exactly the second presentation authority SPEC §1.1.2 forbids.

So the accepted architecture is:

1. **One Project-owned, machine-validated presentation contract** carrying the
   authored visual facts *plus* the atlas geometry currently hardcoded in
   `ui.lua`. Both hosts read it. `ui.lua` stops holding those numbers.
2. **The LÖVE adapter remains the real game renderer** and the only shipped one.
3. **A reusable browser adapter** consuming the contract, the shared leaves and
   the Project assets — inventing no fallback value and no gameplay meaning.
4. **Restricted TypeScript** for the pure renderer-neutral behavior the adapter
   now genuinely needs a second execution of.
5. **The `preview-*` runtime service stays**, in a new and more useful role: it
   is the **arbiter of the parity gate** (§6) and the source of truth for any
   frame that must be exactly the shipped pixels.
6. **Fail-visible** missing or incompatible resources, with contract identity
   sufficient to defeat stale caches.

The mechanism is unchanged from the landed precedent: the browser gets its
correctness from *generated and validated shared facts*, not from a careful
JavaScript author. Where that is genuinely impossible — font rasterization —
§4.4 says so plainly and bounds the residual.

---

## 2. Current authority map

Verdicts below are the **post-decision destinations**, not the current state.

| Visual fact | Authority today | Consumers | Ownership | Destination |
|---|---|---|---|---|
| Active font name/size/Y-offset | `data/system.json` `ui.activeFont/fontSize/fontOffsetY` | `ui.init` → `ui.setFont`; `widgets.js` (edits only) | Project (font *files* Project-or-RTP) | **Data** — contract. |
| Font files | `assets/fonts/*.ttf`; RTP class via `tools/export/rtp-baseline-resources.js` (`FONT_DIR`) | LÖVE `ui.loadFont`; `GET /api/fonts` listing | Project overrides pinned RTP revision | **Data** + existing provenance authority; browser loads the same TTF via `@font-face`. |
| `Lucida` sentinel | `ui.setFont` fallback = LÖVE built-in, no file on disk | mirrored as a *comment* in `widgets.js:1288` | Runtime | **Runtime-only.** The adapter must render it as an explicit "engine default" state, never guess a substitute face. |
| Text palette (`\c[n]`) | `data/system.json` `ui.textPalette` (8 RGBA entries) | `parseRichText` `ui.lua:121` | Project | **Data** — contract. Parsing is a leaf (§4.1). |
| Gauge / cost / tone colors | **hardcoded** `ui.lua:271-303` | `ui.lua` only | Project intent, engine-held | **Promote to data.** Now required: the adapter draws gauges and tone-coloured readouts. |
| Windowskin images | `assets/system/windowskin_{back,button,button_highlight}.png` | `ui.init` | Project | **Data** (asset reference). |
| Windowskin atlas geometry | **hardcoded quads** `ui.lua:196-211` (borders at 32..64, scroll track/thumb at y=32, arrows) | `ui.drawPanel`, `ui.drawScrollbar` | Runtime | **Promote to data.** The single highest-value promotion in this audit — see §5.1. |
| Target reticle atlas | hardcoded quads `ui.lua:215-224` over `UI_Target.png` | `ui.drawTargetReticle` | Project asset + runtime geometry | **Promote to data**, same table, same shape. |
| Role selection (`back`/`button`/`button_highlight`) | `ui.buttonRole` + `drawPanel` role arg | window renderer | Runtime | **Runtime + adapter draw-time branch.** Not a fact; the *role vocabulary* is contract-named so both hosts spell it identically. |
| Panel opening geometry | `ui.rescaleRect` `ui.lua:348` — equal-pixel-rate both axes, floors 16x9 | panel open/close animation | Runtime | **Leaf** (§4.1) — now justified; the adapter animates panels. |
| Panel content origin / tile grid | `ui.panelContentOrigin`, `ui.toPx`, `tileSize=8`, 32x30 tiles | every window renderer | Project convention, engine-held | **Data** (constants) + trivial adapter arithmetic. |
| Iconset image | `assets/system/iconset.png` | `ui.init`; `icon-renderer.js:31` fetches `/assets/system/iconset.png` | Project | **Data** (asset reference). |
| Icon atlas addressing | `resolveIconQuad` `ui.lua:882` (10 cols, 8px, 1-based) | runtime; **mirrored** `icon-renderer.js:4-5` | Project layout, engine-held | **#796.** The adapter consumes #796's output; it must not add a third copy. |
| Icon keying/ramp | `initIconShader` + `resolveIconKeyProfile` `ui.lua:795,938` | runtime shader; **mirrored** `icon-renderer.js:6-12` | Project palettes, engine-held | **#796.** This audit raises its priority: it moves from a bounded picker-only mirror to a dependency of every themed browser surface. |
| Structured icon reference resolution | `ui.resolveIcon` `ui.lua:894` — pure shape normalization | runtime | Engine | **Leaf** (§4.1); dependency of #783. |
| Text normalization | `normalizeText` `ui.lua:598` — 14 fixed UTF-8 → ASCII substitutions, gated by `ui.fontNormalize` | `ui.drawString` | Engine, Project-toggled | **Leaf** (§4.1). |
| Text wrapping | `ui.wrapText` `ui.lua:1105` — `Font:getWrap`, manual path measures `Font:getWidth` | runtime | Runtime | **Split** — see §4.4. The wrap *algorithm* is a leaf; the measurement it consumes is not. |
| Reveal timing | `ui.revealedCount` `ui.lua:1142` — bytes/`ui.textRevealDelay`; `utf8Prefix` snaps to a codepoint | runtime | Project timing + engine rule | Delay is **data**; count + prefix is a **leaf**; `revealedLines` is **runtime/§4.4**. |
| Menu/move/turn/input timings | `data/system.json` `ui.*Duration`, cooldowns, auto-repeat | runtime | Project | **Data** — contract; the adapter's animations use them. |
| Popup fonts/formats/colors | `system.json` `battle_screen.popup` | `ui.init` | Project | **Data**, already. Battle-only; no inventoried tool needs it yet. |
| Cursor / waiting / blue-dot | `assets/system/Cursor.png`, `UI_WaitingForInput[fps=30].png`, `UI_BlueDot[fps=15].png` | runtime | Project | **Data** (asset references). Frame rate already governed by the landed `sprite-timing` leaf — the adapter reuses it unchanged. |
| Character sprites | `assets/character/town/npc_*.png` (incl. `npc_alicia.png`, `npc_laura.png`) | runtime; rules already shared via `shared/semantics/sprite-resolution.ts` + generated JS/Lua | Project | **Already solved.** The adapter reuses the generated JS. No new authority. |
| Studio editor chrome | `studio/editor/themes.json` (RM2003 desktop palette) | Studio only | Studio | **Separate authority, deliberately.** Never merged with the Project contract (#965 non-goal). |
| Pixel scaling | nearest filter set per-image at load in `ui.init`; 256x240 logical screen | runtime | Engine | **Data** (contract token): integer scale + `image-rendering: pixelated`. |

RTP revision identity is `system.json.rtp.revision` (currently `"1.0"`), and
`rtp-baseline-resources.js` already enforces pinned-revision containment plus a
five-field provenance record (`source`, `authorship`, `redistributionStatus`,
`genericReason`, `playerFacingReason`). The contract **consumes** that; it does
not restate it. A themed browser surface that loads a font or windowskin is
therefore loading a resource whose Project/RTP ownership and redistribution
status are already known.

---

## 3. Applet and tool inventory

Every HTML/CSS surface in the repository outside `node_modules` and generated
`out/`. There are seven.

### 3.1 NPC Gauntlet Lab — `tools/npc-gauntlet`

- **User / decision:** the owner and agents judging whether proposed NPC dialogue
  and behavior read as Second Gate characters.
- **Current authority:** `lib/sources.js` extracts speaker/text pairs from
  Project `docs/` and `data/` with a sha256 digest per source file. Presentation
  is 2 lines of generic CSS (`public/app.css`), a 10-line HTML shell, 24 lines of JS.
- **Duplicated facts:** none today.
- **Clock:** frame-local for the UI; revision/compilation for source digests and
  contract identity.
- **Destination:** contract + browser adapter (full strength), plus the landed
  `sprite-resolution` leaf for sprites.
- **Ownership:** Project sources, Project sprites, Project fonts and system assets.
- **Verdict — STRONG, and the pilot.** Judging whether a line sounds like Alicia
  while it is set in `system-ui` on `#eef1f5` is judging the wrong artifact.
  Dialogue belongs in a real message window, in the Project font, at the Project
  offset, with the speaker's sprite beside it. This is the surface that most
  justifies the adapter existing.
- **Verification:** adapter-vs-`preview-window` parity (§6) on a fixed dialogue
  corpus, plus the existing gauntlet test.
- **Non-goals:** no gameplay simulation in the browser; the lab never becomes a
  second authority on what an NPC *is*.

### 3.2 Craft Space — `tools/craft-space`

- **User / decision:** design judgment on Item Creation's discipline/ingredient space.
- **Current authority:** exemplary. `build.py` takes analysis facts from
  `engine.craft` through the read-only `lovec . craft-space-export` CLI mode and
  owns "only the HTML projection, provenance, deterministic serialization, and
  drift check". A `--check` mode gates staleness.
- **Duplicated facts:** none.
- **Clock:** compilation/revision — it is a built static artifact.
- **Verdict — MODERATE, narrower than #965 expects.** The page is a hue-plane
  scatter plot, a value axis, a coverage table and a derivation audit
  (`template.html:104-138`): an analysis instrument, not a screen the player
  sees. Its dark analytic palette is fit for that purpose and should survive.
  What it should inherit is the part that *is* game vocabulary — item and
  discipline names rendered with their canonical icons and tone colors, in the
  Project font — so a design judgment about a shipped system is made against the
  shipped presentation of its entities. Chrome, plots and tables stay analytic.
- **Migration dependency:** contract + adapter + #783 (canonical entity
  presentation). Blocked until #783 gives it something canonical to consume.
- **Non-goal:** theme adoption must not weaken the existing export/drift gate.

### 3.3 asset-gen UI — `tools/asset-gen/ui`

- **User / decision:** the owner rating generated textures/sprites (`rate.html`,
  `index.html`, 269 CSS lines).
- **Verdict — REJECT for chrome; ACCEPT for in-game previews.** #965 asks whether
  game framing helps review here or confuses production-tool chrome with player
  UI. It confuses it: a texture must be judged against the *material*, and a
  rating UI dressed as a game menu invites judging the frame instead of the
  asset. But any preview claiming to show how an asset looks **in-game** is a
  player-facing claim and must be honest — that comes from the adapter or from
  `preview-*`, never from hand-rolled CSS, and it must not become decoration
  around the rating control.
- **Ownership:** generated assets are Project candidates; ratings are tool state.

### 3.4 Studio — `studio/editor`

- **Verdict — SPLIT, already correctly.** `themes.json` and `surface-host.css`
  own editor chrome and stay untouched. Player-preview surfaces already consume
  real pixels via `preview-*`. The one exception is the icon picker's mirror,
  which is #796's.
- **Consequence of this decision:** Studio is the **largest beneficiary and the
  largest risk**. Once the adapter exists, several Studio previews that today pay
  a service round-trip could become frame-local — and that is a legitimate use of
  the authoring clock. But Studio must not acquire the adapter *and* keep the
  mirror: #796 must land, or the adapter must consume it, before any Studio
  surface adopts adapter-drawn icons.

### 3.5 Walkthrough — `projects/hichaukitoden-game/docs/walkthrough`

- **Not named in #965; found by the inventory.** A Project-owned, player-facing
  prose walkthrough with its own magazine styling and `images/title.png`.
- **Verdict — MODERATE.** It is the only genuinely player-facing browser surface
  in the repository, so it has the strongest claim to the Project's typography
  and palette. But it is prose: #783 explicitly warns against turning arbitrary
  web prose into runtime entity UI, so entity names and icons must come from
  #783's canonical presentation or stay plain. Typography first, entities later.

### 3.6 Golden/comparison galleries and generated reports

- Emitted by `tools/golden/record-core.py`, `tools/golden/screens.py`,
  `tools/asset-gen/lib/report.py` and the overnight runners.
- **Verdict — REJECT, explicitly. Evidence tooling.** A gallery's job is to make
  a pixel difference visible. Second Gate chrome around a G5 frame is noise
  competing with the evidence, and risks a reader mistaking harness chrome for
  shipped pixels. Keep them neutral. This is a classification, not an oversight.

### 3.7 Encounter Lab / labs / design-critique

- Python-only, no browser surface (`encounter_lab.py`, `critique_renders.py`,
  `tools/labs/*.py`). **Not applicable.** Recorded so the inventory is complete.

---

## 4. Cross-runtime semantic candidates

The calibration bar is the three landed leaves: 138, 156 and 187 lines, each
pure, deterministic, renderer-neutral, with a real second host executing it. The
adapter decision supplies that second host, so several candidates that were
speculative before are justified now.

### 4.1 Justified by the adapter

Each is its own issue, each independently testable, none bundled into the
adapter implementation.

**`text-normalization`** — `normalizeText` (`ui.lua:598-628`). 14 fixed UTF-8 →
ASCII substitutions gated by one Project boolean. Pure, byte-oriented, no
graphics context. Authority: `ui.lua`. Consumer today: `ui.drawString`. The
adapter renders Project prose in the same pixel fonts, where an unnormalized
curly quote is the difference between a readable line and a tofu box. Parity
gate: the same substitution matrix in Node and real LÖVE/LuaJIT.

**`rich-text-parse`** — `parseRichText` (`ui.lua:121-172`). Splits `\c[N]` runs
against `ui.textPalette`. Pure given the palette, which the contract supplies.
Without it the adapter cannot colour a single line of authored dialogue.

**`icon-reference-resolution`** — `ui.resolveIcon` (`ui.lua:894-919`). Pure
normalization over four authored spellings (`number`, `.icon`, `.icon.id`,
`.iconPalette`/`.palette`) with an empty-string-to-nil rule. It is the
*addressing* half of #783's canonical presentation; extracting it separately
means #783 and #796 consume one resolution rule instead of two.

**`panel-open-geometry`** — `ui.rescaleRect` (`ui.lua:348-356`). Pure and
genuinely subtle: both axes grow at the same *pixel* rate rather than the same
fraction, with 16x9 floors, so a wide button unrolls sideways instead of
inflating. A JavaScript reimplementation would plausibly get this wrong and look
almost right. Now justified — the adapter animates panels.

**`reveal-count`** — `ui.revealedCount` + `ui.utf8Prefix` (`ui.lua:1142-1157`).
Byte count against `ui.textRevealDelay`, then a walk back over UTF-8
continuation bytes so a prefix never splits a codepoint. Easy to get wrong twice
independently. Justified wherever the adapter types text out.

### 4.2 Contract data, not code

`ui.panelContentOrigin` (four lines), `ui.toPx`, `tileSize`, screen tiles,
`gaugeHeight`, and the windowskin/target atlas rectangles. These are numbers, not
algorithms. Shipping them as validated contract data is cheaper and safer than a
generated module, and it removes them from `ui.lua` — which is the point.

### 4.3 Rejected — runtime/service truth

`drawPanel`, `drawScrollbar`, `drawTargetReticle`, `drawBar`, `drawIcon`,
`drawString` (LÖVE resource lookup, quads, shaders, draw state); `ui.init`
(filesystem probing and image caching); the icon shader (GPU). The adapter has
its own DOM/Canvas implementations of the *drawing*; it does not port these, and
neither implementation is authority over the other. The shipped one is LÖVE's.

### 4.4 The residual: font measurement

This is the one place the accepted architecture cannot reach parity by
construction, and it is stated plainly rather than buried.

`ui.wrapText` (`ui.lua:1105`) delegates to `Font:getWrap`, and its manual
coloured-text path measures with `Font:getWidth`. `ui.measureText`, `ui.fitText`
and `ui.revealedLines` all rasterize. A browser measuring the same TTF with
Canvas `measureText` will agree *often* and not *always*: hinting, rounding and
subpixel policy differ between LÖVE's rasterizer and the browser's.

Three honest options, in preference order:

1. **Extract the wrap algorithm as a leaf, inject the measurement.** The
   greedy-fit loop, the space accounting and the `\c[N]`-stripping-before-measure
   rule are pure given a width function. Both hosts then execute the same
   algorithm over their own measurement. This removes the algorithmic divergence
   and isolates the residual to per-glyph widths.
2. **Bound the residual with a gate.** A fixed corpus at the Project font and
   size, wrapped by both hosts, with the browser's wrap points required to match
   LÖVE's exactly. A mismatch is a real finding, not tolerated drift.
3. **Fall back to `preview-*`** for any surface where the wrap must be exact.

Pixel-fonts help materially here — integer advances at integer sizes are far
more likely to agree than a hinted vector face — but that is a reason the gate
will usually be green, not a reason to skip it.

---

## 5. Contract shape

### 5.1 What moves

One Project-owned publication (working name `data/presentation.json`, or a
validated projection of `system.json.ui` — the audit does not fix the filename)
carrying:

- **font**: name, size, offsetY, normalize flag, resolved file path or the
  `Lucida` engine-default sentinel;
- **palettes**: `textPalette`, plus the gauge/cost/tone colors promoted out of
  `ui.lua:271-303`;
- **asset references**: windowskin trio, iconset, cursor set, target skin — with
  Project/RTP ownership and the pinned RTP revision;
- **atlas geometry**: the windowskin and target rectangles now hardcoded at
  `ui.lua:196-224`, named by role and part;
- **units**: `tileSize`, logical screen tiles, gauge height, pixel-scaling rule;
- **timings**: the `ui.*Duration` / cooldown / auto-repeat / reveal-delay set.

The atlas-geometry promotion is the load-bearing one. Every other row could
survive as a read-only projection; this one must genuinely change `ui.lua`,
because a browser that draws a nine-slice from numbers the runtime holds
privately is a second authority by definition.

### 5.2 Rules

1. **Single spelling.** Any value authored in `system.json` is read from there. A
   second spelling of the same number anywhere is a validation failure.
2. **Both hosts consume it.** `ui.lua` reads the promoted geometry and colors
   from the contract. This is a deliberate reversal of the usual
   derived-publication direction: because the fact is now shared, the contract is
   upstream of both renderers rather than downstream of one.
3. **Identity.** A content hash over every contributing source, asset and the RTP
   revision. Browser caches key on it; a stale theme cache is then impossible
   rather than unlikely. This is the compilation/revision clock.
4. **Fail visible.** A missing asset or unresolvable font is an explicit error
   state — never a silent CSS fallback, never an invented default. `ui.init`
   already models the honest version: a skin whose file is missing falls back to
   `back` *deliberately*, because "a panel that draws nothing is worse than a
   panel wearing the wrong skin". The adapter must make the same choice
   explicitly and visibly, not by accident of CSS cascade.
5. **No gameplay meaning.** The adapter renders what it is given. It does not
   decide what an item costs, what an icon means, or what a creature is called —
   those remain #783's and the runtime's.

---

## 6. Verification

The gates must demonstrate freshness and parity **without making browser pixels
the shipped-product truth**. Four, in dependency order:

1. **Contract validation.** Every published value is byte-equal to its authored
   source; no orphan keys; every referenced asset resolves within its declared
   Project/RTP ownership.
2. **Staleness.** The shared-semantics pattern: regenerate, reject stale
   checked-in outputs, and assert no host has regrown a handwritten duplicate of
   a promoted fact. This last assertion is the negative control that makes the
   whole architecture enforceable rather than advisory — without it, an adapter
   author can reintroduce the hardcoded quads and every other gate stays green.
3. **Leaf conformance.** Node + real LÖVE/LuaJIT over the same boundary matrices,
   exactly as the landed leaves do.
4. **Adapter parity.** A fixed corpus of panels, dialogue frames and icon rows
   rendered by the adapter and by `preview-window`/`preview-font`, compared as
   images. **The service PNG is the reference; the adapter is the candidate.** A
   difference is an adapter bug by definition. This is what keeps the adapter a
   presentation adapter and stops it becoming an authority — and it is the reason
   the `preview-*` service must be kept even though the adapter reduces its
   day-to-day traffic.

**G5 remains shipped rendering truth; G6 remains Studio visual truth. An adapter
parity failure is fixed in the adapter. Nothing a browser renders authorizes a
golden recapture.**

---

## 7. Issue topology

Foundation, strictly chronological — each blocks the next:

1. **Presentation contract + validation** (§5), including the atlas-geometry and
   color promotion out of `ui.lua` and the `ui.lua` cutover to reading it.
2. **Reusable browser adapter package + freshness/conformance coverage** (§6.2,
   §6.4), including contract-identity cache keying and the
   no-regrown-duplicate negative control.
3. **Pilot: NPC Gauntlet Lab** (§3.1), including Alicia/Laura sprite
   presentation via the landed `sprite-resolution` leaf.

Then, in parallel, each bounded and separate: Craft Space entity presentation
(§3.2, gated on #783); walkthrough typography (§3.5); asset-gen in-game previews
(§3.3); eligible Studio preview surfaces (§3.4, gated on #796).

Independently, one issue each, not bundled into the adapter:
`text-normalization`, `rich-text-parse`, `icon-reference-resolution`,
`panel-open-geometry`, `reveal-count`, and the §4.4 wrap-algorithm extraction.

#796 and #783 remain their own coordinated work, and this decision **raises
#796's priority**: it is no longer a bounded picker-only mirror but a dependency
of every themed browser surface that shows an icon.

---

## 8. Non-goals restated

Reimplementing the complete LÖVE UI renderer in JavaScript — the adapter covers
panels, icons and text, not the world renderer, effects, battle presentation or
shaders; making every engineering tool look like the game (§3.3, §3.6 are
explicit rejections); reskinning Studio editor chrome; moving mutable gameplay,
simulation, validation, Test Play or final rendering into TypeScript; changing
any art asset or UI design; folding #796 or #783 into this work.
