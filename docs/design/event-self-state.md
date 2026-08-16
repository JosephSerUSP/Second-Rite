# Persistent Map Event SELF state

**Status:** implemented by #409
**Parent architecture:** `docs/design/authored-state-scopes.md` (#400)

Placed Map Event SELF state is persistent gameplay truth. It is deliberately separate from `engine.event_actor`, animation-controller instances, facing, locomotion, and Event presentation inheritance, all of which remain transient presentation/runtime concerns.

## Ownership and storage identity

One SELF owner is identified by the pair:

```text
stable authored Map id + stable placed Event instanceId
```

`event.id` is **not** persistence identity. It remains the existing editor/runtime slot used by Event routing and may be reused after deletion.

Every repo-owned placed Event therefore carries an authored `instanceId`. Studio assigns a cryptographically random `event:<uuid>` when a new placement is applied. Moving a placement preserves that identity. Copy/paste creates a new placement and therefore assigns a new identity even though the copied behavior, Pages, Common Event link, and presentation defaults may be identical.

A legacy or synthetic Event without `instanceId` remains valid when it does not use SELF state. The first ordinary SELF read/write or SELF Page condition fails explicitly rather than falling back to numeric id, coordinates, name, contents, or another invisible heuristic.

Deleting an Event does not retarget its saved bucket. Recreating an Event in the same numeric slot or coordinates receives a new `instanceId`, so orphaned old state cannot be silently claimed.

## State kinds

### Self Switch

A Self Switch is named boolean persistent state local to one placed Event.

- unknown/unset reads `false`;
- `Control SELF Switch` writes explicit ON/OFF;
- Page conditions may require the named switch ON or OFF.

### Self Variable

A Self Variable is named typed persistent state local to one placed Event.

The persistent value boundary is `engine/state_value.lua`: the #407 deterministic value-semantics slice shared by persistent authored-state owners. It accepts the value family established by #400/#407's contract:

- boolean;
- finite number;
- string;
- nil as absence/unset;
- dense ordered lists;
- string-keyed deterministic records.

Values cross the boundary by value. Functions, userdata, metatables, cycles, shared-reference aliases, sparse/mixed tables, and non-finite numbers are rejected.

#409 **reuses** the Game Variable value boundary landed by #407; it does not create an Event-only serializer or a second typed-state vocabulary.

`Control SELF Variable` supports `set`, `add`, `subtract`, `multiply`, and `divide`. Its value field uses the same `stateValue` expression contract as Game Variables, so `set` may author the full deterministic value family (including records/lists). Arithmetic operations require an existing finite-number value and a finite-number operand.

## Event Page conditions

A Page may author structured SELF conditions separately from its existing `condition` string:

```json
{
  "selfConditions": {
    "switch": { "name": "open", "value": true },
    "variable": { "name": "phase", "operator": ">=", "value": 2 }
  }
}
```

Supported Self Variable operators are:

```text
==  !=  >  >=  <  <=  is_set  is_unset
```

Relational operators require finite numeric authored values. Equality uses deterministic typed value equality.

`selfConditions` and the existing Page `condition` are ANDed. Pages keep the existing resolution rule: they are checked in authored order and the last matching Page wins. Resolution is recomputed from current gameplay state on every `resolvePage` call; SELF mutation does not maintain a second Page cache or presentation state machine.

Page formulas may also read the sanitized snapshot nouns:

```text
self.switches.<name>
self.variables.<name>
```

Unknown Self Switches read false; unknown Self Variables are nil/unset. Formula never receives the mutable saved storage tables.

## Event command execution and Common Events

Ordinary SELF commands use the placed Event execution owner captured in the interpreter context. Interactive command graphs bind that owner to their graph walker, so immediate command nodes and Common Event commands injected into the same graph retain the original placed caller.

A reusable Common Event/default behavior therefore owns no SELF bucket of its own. Two placed Events using the same reusable behavior mutate two independent `(map id, instanceId)` buckets.

A Common Event invoked without a placed Event owner cannot use ordinary SELF operations. It may deliberately address another placed Event only by supplying **both** stable identifiers:

```text
mapId + eventInstanceId
```

Supplying only one identifier, an unknown Map, or an unknown placed Event fails. Numeric Event id is never accepted as the persistence target key.

## Save/load

`GameSession.eventSelfState` is serialized as ordinary save data and restored without numeric-key coercion because both owner keys are authored identities.

The save boundary deep-copies and validates values through `engine/state_value.lua`. Because `eventSelfState` becomes a required persistent owner, #409 advances the development save schema to v5 rather than silently tightening v4. Older development saves are intentionally not dual-read (SPEC §1.5).

Event presentation state remains excluded. In particular, #620 animation-controller runtime instances continue to be transient and are not moved into SELF storage.

## Studio authoring

The existing Event/Page modal adds a dedicated **SELF — this placed Event** Page-condition fieldset with:

- Self Switch name + ON/OFF requirement;
- Self Variable name + typed scalar comparison;
- clear placement ownership text;
- Page-list summaries that identify SELF conditions.

The registry-driven Event command editor exposes `Control SELF Switch` and `Control SELF Variable`. This is authoring of gameplay state, not a generic runtime state inspector.

Studio persists `instanceId` on Apply. Copy/paste explicitly refreshes it for the new placement. Repo-owned current Map data has been assigned stable instance identities without changing numeric Event ids.

## Verification contract

Coverage proves:

- Event A/B isolation;
- independent SELF state for two placements sharing one reusable behavior;
- save/load of Self Switch and non-boolean Self Variable values;
- deterministic Page re-resolution after mutation;
- deletion/recreation/numeric-id reuse cannot claim old state;
- deliberate cross-Event stable addressing and rejection of partial/unknown targets;
- deterministic by-value semantics and malformed-value rejection;
- old Events without SELF state keep previous behavior;
- Studio/runtime parity through `tests/fixtures/event_self_state_authoring.json`.

The canonical AUTHORING-STATE census records this as its own Event self-state surface. It is not folded into generic Event command authoring and it is not conflated with Event animation-controller presentation state.

## Non-goals

#409 does not add generic Map Variables, migrate Scene `v`, add ECS/Scene Actors, change Event actor/animation/controller/camera behavior, add compatibility aliases for repo-owned Event data, or recapture G5/G6 references.

Agent-Signature:
  platform: ChatGPT Web
  model: GPT-5.6 Sol
  role: architecture + implementation
  task: "#409 persistent Map Event SELF state and Self Variable authoring"
