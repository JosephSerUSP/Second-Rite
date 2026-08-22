# Authored state scopes

**Status:** durable architecture for #400  
**Evidence:** `docs/reports/authored-state-scopes-evidence-audit-2026-08-13.md`

Thestra names authored state by **owner and lifetime**. The command or formula spelling used to read/write a value does not by itself determine how long that value lives.

## Game Variables and Switches

A **Game Variable** is named authored state with saved playthrough lifetime. It survives Scene changes and Map transfers and round-trips through save/load.

A **Switch** is the boolean authoring affordance for persistent authored state. Switches may share the same typed state substrate as Variables; they retain dedicated author-facing semantics:

- Control Switch / ON-OFF operations;
- boolean page/branch conditions;
- Switch-specific search and inspection affordances.

Game Variables and Switches do not replace existing domain owners. Inventory, quests/progression, gold, creatures and other established game facts remain owned by their semantic subsystems unless a specific migration establishes otherwise.

## Scene state

**Scene state** belongs to one Scene instance. It is appropriate for UI state machines, cursors, selections, transient derived rows/records, presentation working state and other values that should disappear with that Scene instance.

Current Scene `v` is fundamentally this category. It must not be renamed wholesale into persistent Game Variables.

Scene state may contain host-local runtime objects that are not valid generic persistent values. Making structured authored values possible does not require serializing every live object a Scene currently keeps internally.

## Process locals

**Process Locals** belong to one invocation of an authored Flow, Troop Event or other immediate process. They are scratch calculations and control values whose meaning ends with that invocation.

Process-local state is distinct from Scene state even when both are transient.

## Map Event Self state

Persistent **Self state** belongs to one stable placed Map Event instance, not to an Event Template shared by many instances.

Preserve the author-facing vocabulary:

- **Self Switch** for boolean Event-self state;
- **Self Variable** for non-boolean Event-self state.

Cross-event or cross-map access may be supported only when the author explicitly identifies the target's stable owner identity.

## Map-owned state

Map is a valid state owner. Current runtime already has specialized Map-owned persistence.

A generic author-facing **Map Variable** feature is reserved/deferred. It should be added only when production authoring evidence establishes a need; external precedent alone is not sufficient.

## Generic authored value semantics

Persistent generic authored state must be deterministic and serializable. The intended value family is:

- boolean;
- finite number;
- string;
- absence/null semantics defined by the implementation contract;
- deterministic records;
- dense ordered lists.

Structured values cross state-owner boundaries by value, not by surprising shared mutable alias.

Generic persistent authored values must not contain functions, metatables, cycles, userdata, non-finite numbers, live engine references or other values that cannot round-trip deterministically.

Structured records/lists are useful independently of any Scene Actor/ECS architecture. This design does not require or imply Scene Actors.

## Ownership and cross-context access

Every author-visible value has an owner identity. Cross-context reads or writes must select that owner explicitly whenever it is not the current context.

At minimum the architecture distinguishes:

- game/playthrough owner;
- current Map owner;
- placed Map Event instance owner;
- Scene instance owner;
- process invocation owner;
- existing semantic/domain owners.

Stable owner identity, not table reachability, is the basis for cross-context authored state access.

## Studio model

Studio should present state as an owner-aware live tree rather than one flat Variable list:

- **Game Variables**
- **Current Map State**
- **Selected Event Self State**
- **Current Scene State**
- **Process Locals**

The authoring surface should support search/reference discovery and Switch-specific affordances. Declarations/defaults may be optional aids for authoring and validation; runtime-created values remain valid and visible. This architecture does not require numeric preallocation.

## Deferred/non-goals

This document does not define:

- the #407 storage/save implementation;
- the #410 migration of existing `v` uses;
- the #411 inspector UI implementation;
- a generic Map Variable feature;
- a save-schema change;
- a Scene Actor/ECS model;
- migration of inventory/quests/gold/creatures into Variables.

#409 now implements the placed-Event SELF slice described above; see `docs/design/runtime/semantics/event-self-state.md`. The remaining bounded implementation work is tracked by #410 and #411; #407 and #409 are now implemented. #400 remains the architecture parent.

Agent-Signature:
  platform: ChatGPT
  model: GPT-5.6 Sol
  role: documentation
  task: "#400 authored state scopes publication + verification"
  base: 63010d0e3864a17c0a41d5d6c6ca674ad8d0f735
