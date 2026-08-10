# Editor renderable bundle

This document records the design boundary for #277's authoritative visual bridge between Second Rite and Thestra Studio. It describes intent and contract; repository status remains governed by `docs/ENGINE-STATE.md`, `docs/SPEC.md`, and GitHub delivery state.

## Purpose

Thestra Studio needs an interactive renderer that can orbit, pick and edit quickly without reimplementing Second Rite's image-authored geometry compiler, tileset composition rules, deterministic variant resolution, OBJ placement rules, or future geometry topologies in JavaScript.

The bridge therefore exports the **resolved static world surfaces** that Second Rite itself compiled for a loaded map. Browser renderers consume those surfaces; they do not compile authored height fields.

```text
authored project/map
        |
        v
Second Rite loader + runtime structure resolution
        |
        v
engine geometry compiler / OBJ loader / wall compositor
        |
        v
Editor Renderable Bundle
        |------------------------|
        v                        v
Thestra authoring renderer   external serializers
(Three.js initially)         (OBJ/MTL, later GLTF...)
```

The existing map-geometry OBJ exporter becomes a serializer of this bundle rather than a second owner of map collection.

## Authority

The bundle is a **resolved presentation fact**, not authored game data.

- It is produced by the same runtime structure and geometry/compiler paths used by Second Rite.
- It may be regenerated at any time and is never saved into map JSON.
- It contains no editor camera, selection state, transforms or Three.js objects.
- It does not make triangle collision authoritative; Second Rite's logical grid remains gameplay authority.
- A browser renderer may approximate shaders, fog, affine distortion, dithering and lighting while still displaying the authoritative compiled surface geometry/material inputs.

## Version 1 shape

The transport is intentionally simple data: one bundle, a deduplicated material table, and triangle-list surfaces.

```text
bundle
  version
  map { id, name }
  coordinateSystem
  quality
  materials[]
  surfaces[]
  stats
```

Each surface carries four aligned flat attribute streams:

- `positions`: xyz
- `uvs`: uv
- `normals`: xyz
- `colors`: rgba

A surface also carries a stable `material` id and a semantic `source` describing the authored/runtime thing that produced it. A cell source records authored zero-based `x/y`, runtime one-based `runtimeX/runtimeY`, and a surface role such as `floor`, `ceiling`, `north-wall`, `opening`, or `floor-feature`. Event-model surfaces use an event source with the authored event id.

This provenance is intentional. The editor should never infer a cell by reverse-engineering arbitrary final triangles.

## Materials

A material may point at a real project asset or carry an embedded final PNG when the runtime created pixels that do not exist as a source file.

- Ordinary atlas/model textures use `project-asset` paths.
- Runtime wall composites use embedded PNG pixels so edges, fixtures and event-authored wall overlays remain exactly the composed material the renderer resolved.
- Emission/glow follows the same material record when available.
- Image-authored geometry composed from several layers may embed the final albedo produced by the engine composition path rather than exposing its source layers as though they were the final texture.

The bundle preserves vertex colors independently of material color because the static mesh contract already contains both.

## Coordinate contract

Second Rite's runtime mesh space remains Z-up and right-handed, with one world unit equal to one map cell. Runtime grid placements are one-based while authored map/event coordinates are zero-based. Version 1 records both conventions explicitly rather than silently translating the geometry.

A Thestra adapter may map runtime `(x, y, z)` to its editor axes and subtract the recorded grid-origin offset. That transform belongs to the project adapter, not to the engine collector.

UVs preserve Second Rite's top-left image convention. A renderer whose texture API uses another convention performs the explicit conversion at its backend boundary.

## Semantic editing stays separate

The final renderable mesh is what the author sees. It is not what the author manipulates.

Thestra's neutral scene continues to own simple semantic proxies for cells, events, lights, overrides and spawn. Picking/editing should resolve through those proxies or through the bundle's semantic provenance, never through renderer mesh identity.

This permits generated relief, shells, radial geometry, future topologies and visually complex composed walls without turning their triangles into gameplay/editor schema.

## Transient editor snapshots

The authoritative editor bridge accepts the map currently in Studio memory, not only the last version saved to disk. That snapshot is input to one transient runtime load and must never be silently written back to authored storage. The runtime loader/compiler remains the implementation; the snapshot merely substitutes the one map record for that invocation.

The same requirement applies to deterministic procedural authoring previews: the bridge reports the seed used for a generated snapshot so repeated editor refreshes do not masquerade as authored changes. Studio hosts the compiler boundary as a small localhost runtime-bridge service separate from ordinary editor/data HTTP; it invokes LÖVE with a short-lived ignored request file rather than passing large JSON on the Windows command line.

The in-process LÖVE adapter lives at `presentation/editor_renderable_bridge.lua`: it is presentation/tool-host composition, not engine policy. `main.lua`, already the CLI host composition root, detects `SECOND_RITE_RENDERABLE_REQUEST` and routes only that explicit Studio request into the adapter; ordinary `preview-map` continues through the unchanged `engine/cli_tools.lua`. PR3A therefore creates no new runtime `engine -> presentation` module boundary after #282.

Until #237 carries the opened project root through LÖVE preview/Test Play, the bridge must fail loudly when `SECOND_RITE_PROJECT` points outside the installation rather than compiling the installation's project and returning a plausible but wrong bundle.

## Serializer direction

OBJ/MTL is a consumer, not the internal representation. Texture-support work should be built after this boundary so OBJ, Three.js and future GLTF/GLB all receive the same resolved geometry/material facts rather than maintaining separate map-resolution code.
