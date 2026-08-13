# Tileset System & Map-Event Fixtures — Redesign Proposal

> **Intent, not status.** This document describes what we mean to build and why.
> For what exists, read the generated [`docs/ENGINE-STATE.md`](../ENGINE-STATE.md)
> (gated by G4); for how the engine works, read `docs/SPEC.md`. Where this
> document and those disagree, they win.

Drafted 23.07.2026 as a design-board proposal. Several items are explicitly
flagged as open decisions rather than settled design. The implementation
observations that motivated the proposal are historical context, not a live
status record.

## 0. Why this exists

The design pass identified a mismatch between the tileset authoring model and the
underlying schema: weighted structural variants, per-cell feature painting, and
autotile role labels were being presented as one workflow even though they imply
different ownership and placement semantics.

The motivating problems were:

- a structural role needs a real N-way weighted pool rather than one effective
  slot with a decorative `weight` field;
- role labels must be authored data when runtime behavior depends on them, not
  UI-only synthesized state;
- per-cell visual exceptions need one explicit override concept rather than a
  second shadow representation of tileset data;
- dead or unreachable editor surfaces must not become a parallel schema.

This is not a bug list to patch. The philosophy underneath comes first:
**algorithmic placement, controlled by data, before (or instead of)
hand-authoring individual cells.** The editor follows from that philosophy.

## 1. Core layering

Three orthogonal layers apply identically whether the source map is hand-authored
(e.g. the town) or procedurally generated (e.g. a dungeon floor):

- **Structure layer** — per cell: `wall | floor | ceiling | opening`. Authored by
  hand or produced by a room/corridor generator.
- **Decoration layer** — algorithmic, rule-driven placement of visual features
  (torches, rubble, wall variants, floor variants) on top of structure. Driven
  by weighted variant pools plus adjacency/context rules (§3), independent of
  who authored the structure beneath it.
- **Override layer** — one per-cell escape hatch for intentional exceptions:
  “the generator got this cell wrong” and “the town needs a bespoke placement”
  are the same concept, not separate storage paths.

## 2. Structure layer detail

Cell types: `wall`, `floor`, `ceiling`, `opening`.

- `opening` is a first-class structural cell type — a **doorway/gate/arch** the
  player physically walks through to reach another part of the same map. It
  belongs at this layer because room/corridor generation and pathing need to
  know it is passable. Its visual form is resolved through the same
  weighted/adjacency system as walls and floors.
- Per-cell overrides at this layer cover passability anomalies such as illusory
  walls and blocked or one-way floor cells. These are variants of the same
  override mechanism, not new systems.
- A dungeon generator and a human editor must produce the same structural schema;
  only the author changes.

## 3. Decoration layer detail

- **Weighted variant pools per structural role** — real N-way weighted
  selection, not a cosmetic weight with no sibling choices.
- **Adjacency/context rules** — conditions like “only if adjacent to floor,”
  “only within N tiles of an opening,” or “only in zone X.” Use declarative,
  composable predicates (`{all: [...]}`, `{not: {...}}`, etc.) rather than a
  fixed enum; composability matters more than a tiny closed vocabulary.
- **Prefabs** — the day-to-day authoring surface. A prefab is a named,
  pre-validated predicate composition with sane parameter ranges (for example
  `torch_near_corners` or `sparse_rubble`). Raw predicate composition remains
  available for bespoke cases but starts from a known prefab where possible.
- **Zone/region tagging** — map regions such as corridor, treasure room, or boss
  arena may carry rule subsets. The authorship of those tags remains an open
  design question (§8).
- **Per-biome/per-level overrides** — a level references a base tileset plus a
  sparse override delta rather than duplicating the whole ruleset.

## 4. Dungeon generation is data-driven

Room, corridor, anchor/injection, and decoration placement should be controlled
by authored data through shared declarative rule concepts. Generation code may
provide reusable algorithms, but campaign-specific placement policy belongs in
data rather than bespoke map logic.

The important design constraint is one vocabulary for spatial conditions: a
predicate that can describe where decoration belongs should also be reusable by
generation or fixture-placement rules where the semantics match.

## 5. Wall/floor event fixtures — reusing, not replacing, map events

Wall and floor fixtures are ordinary RPG-Maker-style map events: cell-attached
entities with a trigger and a command list compiled through the shared event
language. A chest, trap, painting, switch, teleport point, hidden search spot,
or interaction door should not require a parallel “fixture system.”

Examples:

- chest: `interact` + item-changing commands;
- trap: player-touch/step trigger + damage/state commands;
- sign or painting: `interact` + text;
- teleporter: player-touch/step trigger + teleport/load commands.

**Trigger unification:** passable-cell contact and impassable-cell bump are two
outcomes of movement, not two unrelated event systems. The same player-touch
concept should be able to fire after a successful move or when movement is
rejected by an attached impassable fixture. If distinct trigger spellings remain
useful at the authoring surface, they must still resolve through one movement /
event-dispatch contract rather than duplicated behavior.

**Required fixture semantics:**

1. **Attachment + wall-face rendering.** A wall fixture needs an attachment
   concept identifying the wall face it belongs to and must render on that face
   rather than as a free-floating billboard.
2. **Hidden presentation.** A fixture may intentionally render nothing until a
   reveal condition or structural change makes it visible. Hidden presence must
   be explicit rather than overloaded onto generic transparency.
3. **Structural mutation.** Event commands need a reusable primitive that can
   change structural map state (for example wall → opening) so a hidden-passage
   reveal remains an event-authored behavior rather than bespoke Lua.

**Naming:** the general primitive is `wall_event` / `floor_event` — an
interactable attached to a cell, with trigger + effect — not `door_event`. The
same primitive covers a painting, hidden switch, interaction door, or trap.

## 6. The two “door” concepts

- **SMT-style door** (visual decoration, triggers a scene like a shop/NPC on
  interact) → a `wall_event`, decoration layer, no structural implication. The
  wall stays a wall for pathing/generation purposes.
- **Doorway/gate/arch** (player physically walks through to another part of the
  same map) → the `opening` structural cell type (§2), not an event. No command
  list is required for ordinary passage; it is connectivity plus a visual
  variant.

“Doors as events” is therefore only half the rule: interaction doors are events;
connective openings are structure.

## 7. Editor implications

- The atlas cell-painting UI is not the primary authoring surface for generated
  decoration. It is a coordinate/source picker for structural and decoration
  variants.
- **Primary surface:** author variant pools + weights, adjacency/context rules
  (prefabs first, raw predicate composer second), zone-tag rule subsets,
  biome/level override deltas, plus a generate → preview → reseed loop.
- Hand-editing survives as the override-layer pass over generated or
  hand-authored structure; it is an exception workflow rather than the main
  placement model.
- Town-style hand-authored structure and generated dungeon structure use the
  same decoration rules and override vocabulary.

## 8. Open design questions

1. **Unified override table shape** — the per-cell override must express visual
   override, passability override, and an event's structural-mutation target
   without inventing separate shadow grids.
2. **Predicate composition schema** — declarative composition is preferred to a
   fixed enum; the operator set (`all`/`any`/`not`/adjacency/distance/zone) must
   remain enumerable and validator-friendly rather than fully open-ended.
3. **Zone/region tagging authorship** — hand-tagged vs. algorithmically inferred.
   Prefer algorithm-first if the choice becomes contentious; resolve “what is a
   dungeon floor, structurally?” before adding authoring ceremony.
4. **Structural-mutation validation** — commands that alter map structure must
   remain ordinary registry commands and pass the same context/parameter
   validation discipline as other event effects.
5. **Hidden vs. transparent semantics** — hidden presence and ordinary rendering
   transparency must remain distinct concepts even if both affect whether a
   sprite is drawn.

## 9. Explicitly out of scope

- A mass rewrite of existing map events solely to adopt fixture terminology.
  Schema migrations should be data-migration-not-fallback when a representation
  actually changes.
- Battle/skill/quest command-list work tracked in
  [event-driven-content.md](event-driven-content.md). This proposal is a sibling
  instantiation of the same eventing principle, not a dependency of it.
