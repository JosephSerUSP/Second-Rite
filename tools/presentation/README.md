# Second Gate presentation for browser hosts

From the [#965 audit](../../docs/reports/second-gate-shared-ui-language-audit-2026-08-29.md).
Three pieces, in dependency order.

| Path | What it is |
|---|---|
| `contract.js` | Publishes the presentation contract for one Project (#967) |
| `adapter/second-gate-ui.js` | Renders Second Gate presentation to DOM/Canvas (#968) |
| `parity/` | Measures the adapter against the real LÖVE renderer (#968) |

## The rule

> The adapter is an adapter. Every rectangle, thickness, colour and metric it
> draws with comes from the contract. It owns no presentation fact of its own,
> and it invents no fallback value.

The shipped renderer is and stays `runtime/presentation/ui.lua`. Where a
browser surface needs pixels that must be *exactly* the game's — a real
authored window, a font sample — the answer is still the runtime service
(`POST /preview-window`, `GET /preview-font`), not this package.

## Using it

```js
const { build } = require('tools/presentation/contract');
const contract = build({ projectDir, runtimeDir, rtpRoot });
```

Serve `contract` to the page, load the images it names, then:

```js
const ui = SecondGateUI.create({ contract, images });
document.head.insertAdjacentHTML('beforeend', `<style>${ui.themeCss({ assetBase: '/' })}</style>`);
ui.drawPanel(ctx, 8, 8, 240, 64);                 // role: undefined | 'button' | 'button_highlight'
ui.drawString(ctx, 'Alicia: \\c[6]Laura?\\c[0] She...', 16, 16);
```

`images` is keyed by the contract's asset roles — `windowskin.back`,
`windowskin.button`, `windowskin.button_highlight`, `target`, `iconset`,
`cursor`. Cache anything you derive from the contract under
`contract.identity`: it is a hash over every input including asset *bytes* and
the pinned RTP revision, so a repainted windowskin invalidates it even though
no JSON changed.

Call `ui.missingAssets()` and show what it returns. A Project that ships no
windowskin is a real state, and the viewer of a surface that claims to show the
game must be able to see that a resource was absent rather than quietly getting
a different picture.

## What it does not do

- **Icons.** Icon atlas addressing and keying are mirrored today in
  `studio/editor/js/icon-renderer.js`, and [#796](https://github.com/JosephSerUSP/Second-Rite/issues/796)
  owns migrating that mirror to a shared contract. Adding icon compositing here
  before #796 lands would create the third copy the audit forbids, so the
  adapter deliberately has none.
- **Text wrapping.** `Font:getWrap` is rasterizer-bound (audit §4.4). Glyphs
  themselves now match exactly, but the adapter measures with its own metrics,
  so its line BREAKS are its own. Words and their order are exact; where a line
  ends may not be.
- **The world renderer, effects, battle presentation or shaders.**

## Parity

```bash
npm run parity:presentation
```

LÖVE renders `runtime/presentation/parity_cases.json`; the adapter renders the
same corpus in headless Chrome; the LÖVE PNG is the reference and the adapter
is the candidate. Both `reference.png` and `candidate.png` are written to
`--out` so a failure can be looked at rather than argued about.

The gate has two tiers.

**Text is exact.** The #965 audit expected glyph parity to be out of reach
(§4.4). For a pixel font at an integer size it is not: thresholding the
browser's antialiased raster back to 1-bit and correcting the baseline by one
pixel reproduces LÖVE's output with **zero** differing pixels across the whole
panel interior, drop shadow included. Measured by sweeping threshold × baseline
against the real `preview-font` render:

| threshold | baseline | differing pixels |
|---|---|---|
| ≥160 | −1 | **0** |
| 144 | −1 | 81 |
| 96–128 | −1 | 152 |
| any | 0 | 1554 |

**Geometry is bounded.** Two operations differ between the hosts as arithmetic,
not logic — a stretched edge tile (each host resamples it) and an alpha-blended
blit (each rounds the composite). Those regions are computed from the
*contract*, not from the adapter, and held to a per-channel tolerance with a
budget. Everything else is byte-exact.

The residual is a property of the GPU stack, not of the adapter, so the
tolerance is sized from two renderers rather than one:

| renderer | tolerated pixels | worst channel delta |
|---|---|---|
| NVIDIA (developer machine) | 45 | 10 |
| Mesa llvmpipe (CI runner) | 175 | 14 |

Limit 24, budget 808 of 16,170 band pixels, zero untolerated differences across
61,440 pixels on both.

```bash
npm run test:presentation-parity
```

runs the negative control: nine deliberate breakages — an off-by-one border, a
shifted background inset, a wrong stretch divisor, a raised panel minimum, a
moved corner origin, a shifted rail slice, a wrong arrow alpha, a wrong shadow
colour and a wrong font size — each of which the gate must catch. A gate never
observed to fail is a claim, not evidence. The subtlest lands 24 pixels outside
the tolerance band, so the widened limit still leaves it caught.

Two things that control has already earned. A **crash is not a catch**: an
earlier runner threw before comparing anything, every mutation exited non-zero,
and the control read all ten as caught while three were reaching no comparison
at all — so a mutation now counts only when the gate ran *and reported*. And
`textShadowOffset` is deliberately **not** among the mutations: the sample's
panel interior is pure black and its text pure white, so an 80%-black shadow is
invisible over it in both hosts. The gate is right to see no difference; the
corpus simply cannot show that fact.
