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
- **Text wrapping and measurement.** `Font:getWrap` and `Font:getWidth` are
  rasterizer-bound (audit §4.4). The adapter matches the face, size, offset,
  line step and `\c[n]` runs; it does not claim to match glyph pixels or wrap
  points.
- **The world renderer, effects, battle presentation or shaders.**

## Parity

```bash
npm run parity:presentation
```

LÖVE renders `runtime/presentation/parity_cases.json`; the adapter renders the
same corpus in headless Chrome; the LÖVE PNG is the reference and the adapter
is the candidate. Both `reference.png` and `candidate.png` are written to
`--out` so a failure can be looked at rather than argued about.

Two operations differ between the hosts as arithmetic, not logic — a stretched
edge tile (each host resamples it) and an alpha-blended blit (each rounds the
composite). Those regions are computed from the *contract*, not from the
adapter, and held to a per-channel tolerance with a budget. Everything else is
byte-exact. Current measurement: **45 tolerated pixels out of 16,170 band
pixels, worst channel delta 10 of an allowed 16, zero untolerated differences
across 61,440 pixels.**

```bash
npm run test:presentation-parity
```

runs the negative control: seven deliberate breakages — an off-by-one border,
a shifted background inset, a wrong stretch divisor, a raised panel minimum, a
moved corner origin, a shifted rail slice, a wrong arrow alpha — each of which
the gate must catch. A gate never observed to fail is a claim, not evidence.
