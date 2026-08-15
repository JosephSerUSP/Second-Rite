# Agent-authored Project visuals

Agent-authored Thestra Projects should treat visual assets as authored source, not opaque binary aftermath.

## Minimum visual vocabulary first

Start with the smallest Project-owned visual vocabulary that makes the game readable and gives it an identity. A tiny game often needs only a few reusable surfaces, interaction fixtures, symbols, portraits, or props. Render them in the real Project before expanding the asset count.

Do not assume "asset-free" means neutral or legible. If exact-engine captures show indistinguishable spaces or invisible interactions, add the smallest visual distinction that solves the observed problem and recapture.

## Preserve how an asset was made

Every newly authored player-facing image should have a reproducible source or an explicit provenance note. Prefer one of these shapes:

- a Project-local script/spec that deterministically regenerates the raster or atlas;
- a retained editable source plus an export recipe;
- an image-generation prompt/reference record plus deterministic post-processing/export steps;
- an imported asset with source, author, license, and any transformation recorded.

A final PNG with no retained recipe is allowed only as an explicit non-reproducible exception. Do not silently discard temporary scripts, prompts, palette definitions, geometry/source images, or generation parameters after producing the shipping file.

Keep sources beneath the Project root (for example `art/source/` or another clearly documented Project-owned directory) and generated player assets beneath `assets/`.

## Prefer the right authoring path

Use simple programmatic raster construction for tiny icons, wall fixtures, UI symbols, masks, flat atlases, and other graphics made mostly from geometry/palette decisions. This is usually more controllable and reproducible than generative imagery.

Use image generation or hand/painted source work when the asset depends on illustration, texture, composition, or visual ambiguity that is cumbersome to encode as primitives. Preserve the prompt/source and post-process the output intentionally for the target resolution and rendering language.

Use Thestra's existing image-authored geometry / asset tooling when the desired result is a surface relief, shell/radial volume, or other geometry-bearing asset rather than flattening every object into a sprite.

## Evidence is part of authoring

A game-authoring task is not visually complete because files exist. Its review package should include:

1. a short visual-method note describing palette/resolution, asset roles, and how each asset family was made;
2. a contact sheet of the Project-owned visual vocabulary when there are several small assets;
3. exact-engine screenshots showing those assets in their actual gameplay context;
4. a written walkthrough identifying the interactions/spaces the captures are meant to prove readable.

Inspect the rendered evidence. If a fixture is recognizable in its source PNG but disappears in perspective, or several rooms collapse into the same read, that is an authoring failure even when validation and boot are green.

## Scope rule

The goal is not for every autonomous game experiment to receive a finished art pass. The goal is for an agent to be able to make **deliberate, inspectable, reproducible visual decisions** sufficient to judge the game it authored.

A successful visual experiment may remain crude. It should not remain mysterious.
