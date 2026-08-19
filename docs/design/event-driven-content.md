# Event-Driven Content — Action Sequences, Quest Hooks, Editor Themes

Three independently useful workstreams share one architectural pattern: authored defaults plus per-entry overrides, all exposed through the editor and validated through the same underlying registries.

## 0. The unifying pattern

**Default + override command lists.** The engine uses the same general shape for map events, battle phases, and scene hooks:

- a **default** authored command list defines standard behavior;
- individual entries may select a shared named list or carry an inline custom list;
- command lists compile through `engine/interpreter.lua`'s registry rather than through a parallel host-specific language;
- the validator walks the authored structures under the context that is actually allowed to execute them.

Action Sequences and Quest Hooks apply that shape to two more content domains.

A hard constraint follows from battle's deterministic architecture: authored command lists orchestrate the simulation and emit events for paced replay. They do not block simulation on real-time animation. The event stream is the seam between resolved gameplay and presentation.

---

## A. Action Sequences

### Design decision

Action sequences own **orchestration plus `APPLY_EFFECT`**. `skill.effects` remains the source of damage/heal math; the sequence decides when and how those effects land.

This permits authored timing, animation, waits, and repeated `APPLY_EFFECT` for multi-hit behavior without duplicating effect math in the sequence itself.

A missing per-skill sequence resolves to an authored default that reproduces ordinary behavior.

### Schema intent

`data/actionSequences.json` contains named sequences shaped like common events:

```json
{
  "default": {
    "name": "Default Skill Sequence",
    "commands": []
  }
}
```

Skill assignment mirrors the map-event common/custom split:

- `skill.actionSequence = "<id>"` selects a named common sequence;
- `skill.actionSequenceCommands = [...]` carries a custom inline sequence;
- neither selects the reserved default.

Items use the same model with their own default sequence.

### Command surface

The action-sequence context needs a deliberately small orchestration vocabulary:

- **`APPLY_EFFECT`** applies the acting skill/item effects to already resolved targets and emits the normal resolved combat events. Repeating the command is the multi-hit primitive.
- **`PLAY_ANIM`** emits animation intent for the actor or target rather than making simulation wait on presentation.
- **`WAIT`** emits an authored replay delay.
- general deterministic commands such as text/event emission may participate where their registered context allows them.

The sequence context exposes the acting battler, target, action data, battle, and session through the ordinary formula/ref model rather than a special expression language.

### Runtime intent

Battle resolution should:

1. resolve the action and targets in authoritative gameplay code;
2. resolve the selected action sequence;
3. execute the sequence immediately against that resolved context;
4. append emitted events to the normal battle event stream;
5. let replay/presentation consume `wait`, animation, effect-result, and other events in order.

The default sequence is the compatibility baseline for ordinary authored actions. Custom sequences should alter orchestration, not create a second effect-resolution implementation.

### Editor and validation intent

Action Sequences belong in the Database editor through the same reusable command-list editor used elsewhere. Skills/items select a default, named sequence, or custom inline list rather than requiring raw JSON editing.

Validation should cover:

- reserved defaults,
- sequence references,
- command admissibility under the action-sequence context,
- command parameter shapes,
- and inline/custom sequences through the same command validator.

---

## B. Quest hooks

### Design decision

Quest defaults should make quest data live rather than requiring each conversation graph to hand-roll requirements, rewards, and state transitions.

Quest state remains engine-owned. Authored hooks extend the behavior around an offer or completion; they do not create a second authority for whether a quest is active or complete.

### Schema intent

`data/flows.json` provides quest-host defaults such as:

- `quest.offer`
- `quest.complete`

A quest may optionally override those defaults with per-quest hooks:

```json
{
  "hooks": {
    "on_offer": [...],
    "on_complete": [...]
  }
}
```

The intended split is:

- generic quest plumbing resolves the quest and owns the state transition;
- the default or per-quest authored hook performs content behavior;
- conversation/event graphs route into that generic plumbing rather than owning bespoke reward/requirement logic themselves.

### Quest command intent

The quest context may expose reusable commands that operate on the quest's authored data, such as:

- **`QUEST_TAKE_REQUIREMENTS`** — verify and consume requirement entries according to authored rules;
- **`QUEST_GRANT_REWARDS`** — grant authored rewards and emit readable result events.

Existing general commands remain available when admitted by the quest context.

The point is to keep requirements/rewards declarative and to prevent every NPC graph from independently reimplementing the same bookkeeping.

### Runtime invariants

- Quest state mutates exactly once at the authoritative transition point.
- Missing optional hooks are safe.
- A hook cannot cause the same offer/completion transition to be applied twice.
- Requirement consumption and graph-side item removal must not both charge the same authored cost.
- Reward application comes from quest data rather than duplicated graph literals.
- The established quest-status flag convention remains usable by authored graph conditions.

### Editor and validation intent

Quest authoring should expose the hook command lists beside requirements/rewards through the shared command-list editor.

Validation should ensure:

- quest-host default flows exist,
- hook commands are legal in the quest context,
- referenced data resolves,
- requirement/reward references remain valid.

Absorbing the whole conversation-graph dialect into the main command registry and adding a dedicated quest-log scene are separate design questions, not prerequisites for quest hooks.

---

## C. Editor themes — Studio surface

### Design decision

Editor themes belong to the **editor**, not to game runtime data. Their source of truth is editor-owned under `studio/editor/`, and the editor applies them as presentation tokens without making the game loader understand them.

The theme editor belongs to a Studio/Preferences surface distinct from Database and Engine because these values configure the authoring environment rather than campaign content or engine registries.

### Theme data

Theme definitions should be committable/shareable editor data with stable tokens for concerns such as:

- desktop and window backgrounds,
- title-bar colors,
- content/panel colors,
- selection colors,
- bevel light/shadow values,
- tooltip colors,
- typography/presentation values where appropriate.

The editor maps those tokens to `:root` CSS variables. Individual panels should consume the variables rather than keeping parallel hardcoded theme constants.

Tokens not yet consumed by a surface may remain in the theme definition when they are part of the intended shared palette; adding a surface should extend the mapping rather than inventing a second theme source.

### Studio behavior

The Studio surface should provide:

- theme selection,
- live preview by applying root variables,
- creation/deletion/editing of shared theme definitions,
- persistence of theme definitions to the editor-owned file,
- persistence of the active local preference independently from game data.

### Runtime boundary

The game runtime must remain independent of editor theme data. Removing or changing editor themes must not affect game loading or validation except for editor-specific checks/tests.

---

## Why these belong together

The architectural payoff is the same in all three cases:

> authored data -> generic dispatch/application -> validation -> shared tooling

rather than:

> authored data -> bespoke host branch -> bespoke editor UI -> bespoke validation workaround

Action Sequences apply it to combat orchestration. Quest Hooks apply it to progression behavior. Editor themes apply the same ownership discipline to authoring-tool presentation, while intentionally staying outside runtime data.

The workstreams are related by architecture, not by delivery order. A design document should preserve that connection without becoming their progress tracker.
