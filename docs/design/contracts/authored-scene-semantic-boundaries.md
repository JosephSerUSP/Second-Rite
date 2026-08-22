# Authored Scene semantic boundaries

This note records only durable conclusions supported across the current Scene corpus and the #325/#400 architecture decisions. The dated evidence/census lives in `docs/reports/scene-portability-native-boundary-audit-2026-08-13.md`.

## 1. Authored composition is a semantic contract, not a file-format claim

A Scene, Event Program, or Flow is backend-neutral when its behavior is stated in Thestra semantics. JSON storage alone does not make behavior portable, and native implementation alone does not make a semantic primitive unauthorable.

Authored composition may depend on explicit native semantic primitives whose implementation a backend replaces while preserving the contract.

Examples include targeting, authoritative Battle resolution, save/load, roster transactions, input hosting, and rendering.

## 2. Scene authorability model

An ordinary authored Scene should be intelligible as:

> Scene-instance state + conditions + Event commands + presentation requests + calls into explicit semantic primitives.

This is a legibility rule, not an RPG Maker exporter requirement.

Reusable semantic commands and queries are preferred when they express domain behavior. `SCRIPT` remains a legitimate escape hatch for backend/package/tooling needs, but large one-Scene native controllers should not be mistaken for reusable semantic primitives merely because they are written in engine code.

## 3. State crossing the authored boundary

Scene `v` is Scene-instance state, not persistent Game Variable storage.

Author-facing Scene values should be deterministic serializable values or stable owner identities. Native object references, userdata, function identity, metatables, pointer/reference aliasing, and live backend handles are not portable authored values.

A native primitive may internally hold rich engine objects. Authored composition should cross that boundary through values, explicit queries, stable identities, or an explicitly non-authored native context owned outside `v`.

Persistent domain truth remains with its semantic owner: inventory, quests, gold, rosters, recruitment nodes, save data, and similar state are not copied into generic Scene Variables merely to make them visible to a Scene.

## 4. Formula semantics belong to Thestra

The formula evaluator may be implemented with Lua today, but authored formulas are a Thestra language contract.

A backend implementation must reproduce the documented formula semantics used by authored resources rather than treating the current Lua evaluator as an accidental permanent specification.

The contract must define the supported value types, operators/precedence, truthiness, equality, indexing/list conventions, absence behavior, helpers, randomness/determinism, and errors before another evaluator can claim compatibility.

Raw `SCRIPT` is different: unless a package explicitly chooses a portable scripting contract, Lua SCRIPT source remains a backend escape hatch rather than backend-neutral authored semantics.

## 5. Presentation is requested by authored resources and implemented by the backend

Authored Scenes may describe windows, pictures, logical-input responses, visibility, layout/formulas, and lifecycle transitions without owning renderer objects.

Renderer/window/audio/input implementations may use LÖVE or another backend internally. Backend APIs should not be required in ordinary authored Scene data.

Gameplay/authored formulas that control presentation properties are resolved on the semantic engine side before a backend renderer consumes their numeric/value result. Presentation must not silently become the definition of gameplay formula semantics.

## 6. Native Battle is compatible with authored Battle composition

Battle has an authoritative native domain/kernel responsibility: action/target validity and resolution, effect/resource/state/death commits, immutable resolved facts/provenance, deterministic ordering, and outcome evaluation.

That does not imply that Battle input menus, lifecycle Flow policy, log/revelation timing, animation choreography, reward narration, encounter policy, or Project-specific reserve/permadeath rules are inherently native domain semantics.

Battle architecture should therefore be evaluated responsibility by responsibility. “Native Battle primitive” and “one-off native Battle Scene composition” are different categories.

## 7. RTP ownership is semantic ownership

RTP/default/template versus Project ownership is decided by reusable role and policy, not by whether a resource is JSON or Lua.

A reusable Scene structure may be mixed with Project-specific text, art, Common Events, policies, or domain rules. Extracting/moving those resources is a separate ownership task coordinated through #390; portability work must not silently move ownership boundaries.

## 8. Time is an explicit semantic dependency

Authored repeated-update behavior must not derive gameplay meaning from an undocumented renderer frame rate. A Scene may be authorable with a repeated hook while still lacking a deterministic portable time contract.

The concrete timing contract is owned by #386. This note establishes only the boundary: frame cadence is not implicit authored game time.
