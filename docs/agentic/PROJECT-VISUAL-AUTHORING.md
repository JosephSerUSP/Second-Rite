# Agent-authored Project visuals

Agent-authored Thestra Projects should treat visual assets as authored source, not opaque binary aftermath.

## Minimum visual vocabulary first

Start with the smallest Project-owned visual vocabulary that makes the game readable and gives it an identity. A tiny game often needs only a few reusable surfaces, interaction fixtures, symbols, portraits, or props. Render them in the real Project before expanding the asset count.

Do not assume "asset-free" means neutral or legible. If exact-engine captures show indistinguishable spaces or invisible interactions, add the smallest visual distinction that solves the observed problem and recapture.

## Preserve how an asset was made

Every newly authored player-facing image should have a reproducible source or an explicit provenance note. Prefer one of these shapes:

- a Project-local script/spec that deterministically regenerates the raster or atlas;
- a retained editable source plus an export recipe;
- an asset-gen run manifest containing the prompt/reference/provider/model plus its deterministic post-processing/export target;
- an imported asset with source, author, license, and any transformation recorded.

A final PNG with no retained recipe is allowed only as an explicit non-reproducible exception. Do not silently discard temporary scripts, prompts, palette definitions, geometry/source images, or generation parameters after producing the shipping file.

Project-specific source/spec/provenance belongs beneath the Project root (for example `art/source/` or another clearly documented Project-owned directory) and generated player assets belong beneath that Project's `assets/`. Shared tooling may remain installation/repository-owned.

## Prefer the right authoring path

### Programmatic raster

Use simple programmatic raster construction for tiny icons, wall fixtures, UI symbols, masks, flat atlases, and other graphics made mostly from geometry/palette decisions. This is usually more controllable and reproducible than generative imagery.

The repository does not yet expose a neutral Project-oriented helper for this lane. Until #531 lands, retain the script/spec that produced such assets inside the Project rather than committing only its PNG output.

### Existing asset-gen

For image-model-backed sprites, portraits, tilesets, texture pieces, wall pieces, panoramas, location/event art, and animation sheets, prefer the existing `tools/asset-gen` pipeline instead of making direct opaque model calls.

`tools/asset-gen/gen.py` already owns the expensive/reproducible workflow: it stages raw model output and processed variants under `tools/asset-gen/out/`, creates a nearest-neighbour contact sheet, records prompt/provider/model/target information in a run `manifest.json`, supports deterministic local seeds, reprocessing without another model call, tile seam checks, reports, and promotion into the player asset path. Read `tools/asset-gen/README.md` and its class registry rather than inventing a second generation pipeline.

For an independent Project, make the target/ownership explicit. Do not accidentally promote generated work into root Second Gate `assets/` merely because that is the historical default of a class. #531 should make Project-root targeting a first-class agent workflow rather than duplicating asset-gen.

### Geometry-bearing art

Use Thestra's existing image-authored geometry / asset tooling when the desired result is a surface relief, shell/radial volume, or other geometry-bearing asset rather than flattening every object into a sprite. Preserve the source image/height/spec and the build recipe.

Use hand/painted editable sources when that is the most appropriate authoring method; the same provenance/source rule applies.

## Evidence is part of authoring

A game-authoring task is not visually complete because files exist. Its review package should include:

1. a short visual-method note describing palette/resolution, asset roles, and how each asset family was made;
2. a contact sheet of the Project-owned visual vocabulary when there are several small assets;
3. exact-engine screenshots showing those assets in their actual gameplay context;
4. a written walkthrough identifying the interactions/spaces the captures are meant to prove readable.

Reuse asset-gen's generated contact sheet/report when it is the authoring path. A Project-local raster helper should provide equivalent contact-sheet evidence when #531 implements that lane.

Inspect the rendered evidence. If a fixture is recognizable in its source PNG but disappears in perspective, or several rooms collapse into the same read, that is an authoring failure even when validation and boot are green.

## Scope rule

The goal is not for every autonomous game experiment to receive a finished art pass. The goal is for an agent to be able to make **deliberate, inspectable, reproducible visual decisions** sufficient to judge the game it authored.

A successful visual experiment may remain crude. It should not remain mysterious.
