# Unit, Actor, Battler, and symbolic Unit identity

Status: architectural contract for issue #147.

The core rule is:

> **Unit is authored identity. Battler is combat state. Actor is persistent
> player-owned identity. Enemy/ally is a runtime relationship.**

This vocabulary describes responsibilities. It does not require separate Actor
and Enemy databases, an Enemy subclass, or allegiance on authored creature
definitions.

## 1. Unit

A **Unit** is an authored combat-capable definition.

Examples include `pixie`, `skeleton`, `moa`, and `red_dragon`.
Unit data owns facts shared by occurrences of that definition:

- canonical symbolic resource ID;
- base and growth parameters;
- elements;
- definition-granted skills and passives;
- art and presentation references;
- authored evolution and transformation rules;
- recruitment eligibility and other definition-level metadata.

A Unit has no intrinsic battle allegiance. The same Unit may produce a transient
opponent Battler or a persistent player-owned creature.

The Unit catalog is one semantic authored resource. Whether its physical storage
is monolithic or fragmented belongs to the authored-storage layer and must not
change Unit identity semantics.

## 2. Battler

A **Battler** is the runtime abstraction for something participating in combat.
It owns or exposes combat state such as HP, states, resolved parameters, skills,
passives, resources, and formation position.

Second Rite intentionally uses the same Battler abstraction on both sides of a
fight. Troop/encounter construction and player-owned creatures resolve the same
Unit definitions into Battlers.

There is therefore no authored Enemy type. “Enemy” and “ally” describe where a
Battler participates in an encounter.

## 3. Actor

An **Actor** is the persistent player-owned identity of a Battler built from a
Unit.

Actor responsibility includes individuality that survives beyond one battle:

- instance UID;
- personal/display name;
- individual growth seed and accumulated history;
- EXP and persistent level history;
- equipment and persistent resources;
- Favorite Food and discovery state;
- provenance and reversible-transform origin;
- creature history.

Conceptually:

```text
Unit
  -> Battler              transient combat occurrence
  -> Actor : Battler      persistent player-owned occurrence
```

The notation does not require a Lua `Actor` subclass. Persistent identity fields
may remain co-located with universal combat state until responsibility and every
reader/writer can move atomically. Splitting an object solely to make the
terminology look purer would force growth, transforms, save/load, recruitment,
equipment, presentation, and tests across a new boundary at once.

An Actor/Battler object cleanup should move responsibilities only when ownership
of those fields and all callers can move together.

## 4. Legacy Summoner migration note

The symbolic Unit migration used `summoner` as the canonical resource identity
for the old Summoner combat definition. That migration fact does **not** make
“Summoner” part of the Unit concept: a legacy record, if retained by authored
data, is merely a cleanup concern.

Removing or relocating legacy records is deliberately separate from symbolic
identity migration so a naming/domain change is not mixed with a semantic roster
deletion. The presence or absence of any such record is a live data question,
not a design-doc status claim.

## 5. Canonical loader vocabulary

Authored-definition loader APIs use **Unit** vocabulary:

```text
loader.units
loader.unitsById
loader.getUnit(id)
loader.getUnitByRole(role)
```

There is no need for an Actor-named authored-definition API. Code that means an
authored definition uses Unit vocabulary; Actor-named operations are reserved
for persistent player-owned individuals.

## 6. Canonical Unit identity

Unit IDs are symbolic strings. Numeric Unit IDs are not a supported runtime or
authoring compatibility surface.

Every Unit definition must have one non-empty string ID, unique within the Unit
registry. References resolve directly against that registry.

Examples of canonical identities:

```text
Pixie       -> pixie
High Pixie  -> high_pixie
Moa         -> moa
Red Dragon  -> red_dragon
Gbl. Thief  -> goblin_thief
Gbl. Prince -> goblin_prince
```

These illustrate why resource identity is not display-name slugging. UI
abbreviations do not define identity, and mutable presentation text must not
become a lookup key.

Likewise, `red_dragon` remains a creature-concept identity even when an encounter
uses it as a boss. Boss status belongs to troop/encounter data. Encoding that
status in the Unit ID would make identity carry gameplay context that need not
hold for every occurrence.

## 7. IDs are opaque handles

No gameplay or tooling behavior may be inferred by parsing a Unit ID.

In particular, code must not infer from the string:

- element;
- tier;
- allegiance;
- recruitability;
- boss status;
- progression position;
- evolution order;
- role;
- presentation category.

Those are authored fields or relationships.

Symbolic identity exists to make references meaningful and stable, not to hide
rules inside names.

Evolution-family or progression information should likewise be explicit data if
it becomes useful. IDs such as `pixie`, `high_pixie`, and `titania` identify the
resources themselves; family, stage, branch, and the `evolvesTo` graph must not
be inferred from naming conventions such as `pixie_1` or `dragon_2a`.

## 8. Reference field spellings are separate from identity

A field may carry a Unit ID even if its historical spelling uses Actor-era or
generic vocabulary. Examples of spellings the identity migration must treat as
Unit-reference positions include:

- `actor`;
- `actorId`;
- map `recruits` entries;
- `recruit_egg.value`;
- `evolvesTo`;
- `eligibleFrom`;
- transform destination `actor`;
- fixed new-game member `id`;
- deterministic fixture party entries.

Renaming such fields is a separate schema migration. Changing a field name and
changing its identity domain at the same time makes failures harder to diagnose.

The Unit-reference audit/validator must know every schema position that carries a
Unit identity and require every destination to resolve. Verification fixtures
speak the same canonical identity domain as gameplay data rather than retaining a
private numeric convention.

Transform operation sentinels are not Unit IDs:

```text
hatch
metamorph
revert
```

A new Unit-reference schema must be added to the identity audit when introduced.

## 9. Actor names and Unit identities are different

Persistent creature names must never become resource lookup keys.

For example, an individual Actor named **Saban** may be built from Unit `moa`.
Code that wants the species/definition resolves `moa`; code that wants the
individual Actor may display or modify Saban's personal identity.

This distinction is the point of the Unit/Actor vocabulary rather than an edge
case to paper over.

## 10. Save compatibility for the symbolic cutover

The numeric-to-symbolic Unit migration deliberately does **not** preserve a
numeric Unit-ID fallback for development saves.

A save from before the symbolic identity boundary must fail loudly rather than
being interpreted through a permanent numeric-to-symbolic mapping. New save
formats persist symbolic Unit identity in fields such as Battler identity and
reversible-transform origin.

Keeping a numeric lookup table for ordinary runtime resolution would create a
second identity system and turn obsolete numeric IDs into a permanent
compatibility surface.

## 11. Names intentionally not forced by this contract

The following names can move independently when responsibility or storage is
actually being changed:

- authored `actor` / `actorId` field names;
- `Battler.actorData`;
- `GameSession:createPersistentBattler`;
- `GameSession:recruitActor`;
- historical save/session field names;
- presentation modules whose “actor” surface genuinely describes a persistent
  party creature.

A broad textual rename is not itself architecture.

## 12. Future Actor/Battler object cleanup

A useful test for moving a field out of Battler is:

> Can a transient opponent meaningfully need this fact during one battle, or is
> it meaningful only because this individual persists outside battle?

Personal name, instance UID, Favorite Food discovery, provenance, and long-term
history are strong Actor-owned candidates. Other fields require more care.
Growth affects enemy combat stats too. Equipment may be valid for opponents.
Persistent resources may need a battle representation.

Trace actual readers and writers before moving them.

## 13. Invariants

1. **Unit definitions have no intrinsic ally/enemy side.**
2. **Troops and player rosters resolve the same Unit registry.**
3. **Battler is the shared combat abstraction.**
4. **Actor means persistent player-owned identity, not the authored catalog.**
5. **Canonical Unit IDs are unique, non-empty symbolic strings.**
6. **Numeric Unit IDs are not a compatibility surface.**
7. **Authored-definition loader APIs use Unit vocabulary only.**
8. **Unit IDs are opaque handles; behavior and progression structure are explicit data.**
9. **Transform operation sentinels are not Unit identities.**
10. **Personal Actor names are never Unit lookup keys.**
11. **Pre-symbolic development saves are rejected rather than supported through numeric fallback.**
12. **Verification fixtures use the same canonical Unit identity domain as gameplay data.**
13. **Legacy records do not redefine Unit semantics and may be removed independently.**
14. **Storage migration, field-name cleanup, and Actor/Battler object cleanup remain separately diagnosable changes.**
