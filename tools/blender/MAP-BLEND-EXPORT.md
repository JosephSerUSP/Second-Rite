# Structured map `.blend` export

This tool exports a Thestra map into a Blender file without routing through OBJ.

The geometry authority remains the runtime `map_renderable_bundle`. The launcher uses the same `compileRenderable()` bridge as Thestra Studio's 3D viewport, then Blender consumes that renderer-neutral JSON bundle and creates one selectable Blender object per bundle surface.

## Requirements

- LÖVE 11.5 at the normal development path, or `LOVE_PATH` set for the existing runtime bridge.
- Blender available as `blender`, or `BLENDER_PATH` set to the Blender executable.
- Node.js.

## Run

From the repository/project root:

```text
node tools/blender/export_map_blend.js 8
```

A map JSON path is also accepted:

```text
node tools/blender/export_map_blend.js data/maps/8.json --output exports/maps/dev-room.blend
```

For generated maps, pin a seed when desired:

```text
node tools/blender/export_map_blend.js 8 --seed 1735689600
```

The default output is `exports/maps/<id>-<name>.blend`.

## What survives

- one Blender object per authoritative renderable surface;
- source-level parent empties, so all surfaces belonging to the same authored/renderable source can be selected together;
- semantic bundle provenance (`source.kind`, authored cell coordinates, event id, feature/surface fields when present) as custom properties;
- collections grouped by provenance kind (for example `cell` and `event`);
- material identity and base color;
- project or runtime-composed albedo textures, packed into the `.blend`;
- emission textures where the bundle exposes them, packed into the `.blend`;
- UV coordinates and available custom normals;
- resolved vertex-light colors as the `Thestra Light` corner color attribute;
- Thestra's native right-handed Z-up coordinates and map-cell units.

The importer intentionally does not reconstruct authored Map semantics from JSON or OBJ. If a fact is absent from the authoritative renderable bundle, this exporter does not invent it.

## Scope

This is an authoring/export tool, not a new runtime representation. Editing the generated `.blend` does not write changes back into the Thestra Map. A future import/round-trip workflow, if useful, needs its own explicit ownership contract.
