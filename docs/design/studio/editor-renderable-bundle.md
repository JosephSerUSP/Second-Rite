# Editor renderable bundle

This document records the design boundary for the authoritative visual bridge
between a Thestra Project and Studio. It describes intent and contract;
repository status remains governed by `docs/ENGINE-STATE.md`, `docs/SPEC.md`,
and GitHub delivery state.

## Purpose

Thestra Studio needs an interactive renderer that can orbit, pick, and edit
quickly without reimplementing the runtime's image-authored geometry compiler,
tileset composition rules, deterministic variant resolution, model placement,
or future geometry topologies in JavaScript.

The bridge therefore exports the **resolved static world surfaces** that the
runtime compiler produced for a loaded Map. Browser/editor renderers consume
those surfaces; they do not independently compile authored height fields.

```text
authored Project / Map
        |
        v
runtime loader + structure/resource resolution
        |
        v
geometry compiler / model loader / surface compositor
        |
        v
Editor Renderable Bundle
        |------------------------|
        v                        v
Studio authoring renderer     serializers
(replaceable backend)         (OBJ/MTL, GLTF/GLB, ...)
```

An interchange exporter is a serializer of this bundle rather than a second
owner of Map collection/compilation.

## Authority

The bundle is a **resolved presentation fact**, not authored game data.

- It is produced from the same runtime structure/resource and geometry/compiler
  semantics used by the game.
- It may be regenerated at any time and is never saved into Map JSON as the new
  authority.
- It contains no editor camera, selection state, or backend-specific objects.
- It does not make triangle collision authoritative; the Project's logical Map
  remains gameplay authority.
- An authoring renderer may approximate shaders, fog, affine distortion,
  dithering, and lighting while still displaying the authoritative resolved
  geometry/material inputs.

## Bundle shape

The transport is deliberately plain, versioned data: one bundle, a deduplicated
material table, and triangle-list surfaces.

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

Each surface carries aligned attribute streams such as:

- `positions`: xyz
- `uvs`: uv
- `normals`: xyz
- `colors`: rgba

A surface also carries a stable material reference and semantic `source`
provenance describing the authored/runtime thing that produced it. Cell-derived
surfaces retain enough authored/runtime grid identity and surface role for Studio
to map a pick back to the semantic cell. Event/model surfaces retain event or
source identity appropriate to that same purpose.

The editor should never infer authored identity by reverse-engineering arbitrary
final triangles.

## Materials

A material may reference a resolvable authored resource or carry embedded final
pixels when the runtime composition creates a texture that has no single source
asset.

- Ordinary atlas/model textures retain resource provenance rather than becoming
  anonymous browser assets.
- Runtime composites may embed their resolved image so edges, fixtures, and
  authored overlays remain the material the compiler actually resolved.
- Emission/glow or related material channels travel with the same material fact
  where the bundle contract exposes them.
- Image-authored geometry composed from several sources may embed the final
  albedo rather than pretending one contributing layer is the resolved texture.

The bundle preserves vertex colors independently of material color because the
resolved static mesh contract may need both.

Resource/provider ownership must follow the Project/package/RTP resolution
contract rather than assuming every valid material originated as a Project-local
file.

## Coordinate contract

The bundle records its coordinate system explicitly, including world-unit scale,
axis orientation, and authored/runtime grid-origin conventions. An editor backend
may transform those coordinates for its own camera/library, but that transform
belongs to the adapter boundary and must not rewrite semantic provenance.

UVs likewise preserve the runtime's declared image convention. A backend with a
different texture convention performs one explicit conversion at its rendering
boundary.

## Semantic editing stays separate

The final renderable mesh is what the author sees. It is not what the author
manipulates as schema.

Studio's neutral scene owns semantic proxies for cells, events, lights,
overrides, spawn, and other authored objects. Picking/editing resolves through
those proxies or through the bundle's source provenance, never through renderer
mesh identity alone.

This permits relief, shells, radial geometry, composed walls, and future
presentation topologies without turning their triangles into gameplay/editor
schema.

## Transient editor snapshots

The visual bridge must be able to compile the Map currently in Studio memory,
not only the last copy written to disk. That snapshot is input to one transient
runtime load and must never be silently persisted back to authored storage.

The same rule applies to deterministic procedural previews: the bridge reports
or otherwise preserves the generation identity needed for a stable refresh so a
new random result does not masquerade as an authored edit.

The hosting/transport mechanism is an implementation detail. Whether Studio uses
an in-process adapter, local service, request file, or another bounded host seam,
it must preserve these invariants:

- runtime loader/compiler semantics remain the implementation;
- ordinary runtime/preview entrypoints do not become editor-specific policy;
- the explicit opened **Project** identity is carried end to end;
- a bridge that cannot resolve that Project must fail loudly rather than compile
  installation/sample content and return a plausible but wrong bundle;
- transient snapshot data is scoped to the request and cannot silently become a
  second authored storage path.

That last rule replaces any dependency on a particular historical Project-root
migration sequence: it is the durable correctness condition regardless of how
Project mounting/materialization evolves.

## Serializer direction

OBJ/MTL, GLTF/GLB, and future formats are consumers, not internal
representations. Serializer work should consume the same resolved
geometry/material facts as Studio so export formats do not grow independent Map
resolution code.
