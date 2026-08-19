# Floor/Ceiling Texturing — Design Constraints

> **Intent, not status.** This document records the rendering and spatial-design
> constraints that motivated textured floor/ceiling work. Implementation
> inventory belongs to [`docs/ENGINE-STATE.md`](../../ENGINE-STATE.md) and reviewed
> renderer behavior to `docs/SPEC.md`.

## Why GPU-side projected texturing

Projected floors and ceilings can require a distinct world-space sample for
many screen pixels. Performing that work as thousands of tiny CPU-side draw
operations is the wrong scaling model. When the renderer needs per-pixel
projection, lighting, fog, or material sampling, that work should be expressed
as GPU-friendly batched/shader work or an equivalently efficient renderer path.

The durable constraint is not a particular shader source: **world-space plane
presentation must not regress into per-pixel Lua draw-call loops.**

## Shared spatial meaning

Floor, ceiling, and wall presentation must agree about the same camera/world
coordinates and the same authored material ownership. A floor texture must not
be resolved through a second material system merely because its projection math
differs from a wall's.

Likewise, lighting should describe one spatial field. Renderer-specific sampling
may differ, but the visible result must not invent separate authored light
truths for walls versus floors versus ceilings.

## Material fallback is explicit

A tileset may omit a specialized floor or ceiling material. In that case the
renderer may use the Project's defined fallback presentation, but missing
required resources must not be silently replaced by unrelated Second Gate
content. The live material/resource contract, including legitimate inherited
resources, belongs to `docs/SPEC.md` and the Project/RTP design.

## Height and topology are not shader flags

Variable floor/ceiling elevation and non-grid spatial topology are materially
different design questions from texturing a surface. They must not arrive as a
few renderer flags that quietly redefine Map gameplay.

Preserve these boundaries:

- the game's logical Map/grid, movement, collision, Events, and saves remain
  authoritative unless a separate gameplay-spatial design changes them;
- richer presentation geometry may represent relief, openings, shells, models,
  or other shapes without implying new navigable topology;
- if a future Project needs true multiple walkable heights, sectors, continuous
  placement, or another spatial ontology, define that semantic model first and
  then choose a renderer suited to it.

This is intentionally compatible with a polygonal renderer: presentation can
become much richer while the gameplay world remains a 2D logical grid.

## Determinism and authoring

Any generated/projected surface result used by Studio previews, export, or the
runtime should derive deterministically from the same authored resource and Map
inputs. Studio may approximate final shading for interactivity, but it must not
invent a separate floor/ceiling compiler whose geometry or material ownership
can disagree with the runtime.
