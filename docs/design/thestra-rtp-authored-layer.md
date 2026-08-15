# Thestra RTP authored layer

Status: durable architecture intent for #385. Current inventories and file-level evidence belong in `docs/reports/thestra-rtp-authored-layer-audit-2026-08-13.md`; this document defines stable ownership and resolution semantics rather than current migration status.

## Layering

Use **RTP** as the working name for Thestra's versioned authored layer. It is not a player-installed runtime pack.

```text
Lua/LÖVE implementation substrate
        ↓
reusable Thestra semantic primitives
        ↓
Thestra RTP
  ├─ baseline/default authored compositions
  ├─ baseline/default player-facing resources
  └─ optional authored template/library content
        ↓
explicit Packages/dependencies
        ↓
Project-local authored content/overrides
        ↓
hermetic exported player game
```

A Project is the independently runnable/authored game identity. The RTP is supplied by Thestra during authoring; Packages are explicit additional reusable dependencies; Studio is the authoring application. These owners remain distinct even if future implementation shares resolver infrastructure.

## Default, template, Project, Package and Studio semantics

**RTP default** is baseline authored RPG behavior/presentation that an ordinary Project may inherit and intentionally override. Examples may include a house title/menu composition, baseline UI frame resources, baseline UI sounds, progression policy, or reusable system animation compositions.

### The baseline is a house style, not a claim of neutrality

RTP defaults are intentionally opinionated. Thestra is primarily JosephSeraph's authoring environment, so when a reusable RPG default requires a design direction it should reflect recurring JosephSeraph game grammar rather than attempt to approximate a genre-neutral universal engine.

Canonical principle:

> **Thestra runtime should strive for semantic generality. Thestra RTP should strive for JosephSeraph coherence.**

The distinction is ownership and replaceability, not absence of taste. A compact JRPG-shaped progression curve, menu convention, numerical range, recovery convention or presentation grammar may be a healthy RTP default when it is reusable across the owner's work, pinned/versioned, inspectable and cleanly overridable. Concrete Second Gate lore, IDs, characters, branded assets, one-game balance rules or other Project identity remain Project-owned.

Use "neutral" only where it has a literal technical meaning, such as a non-Project-branded preview placeholder. It is not the normative design target for gameplay or presentation defaults.

A useful scope rule is: **generalize from the body of work, not from the universe of possible games.** Thestra may have a strong center of gravity without turning that center into a native-code restriction.

**RTP template** is optional authored library content. It does not become active merely because the RTP is installed. An author deliberately instantiates/references/forks it. A successful authored pressure test such as a Pong Scene belongs here as reusable composition rather than becoming a native `pong.lua` scene or Second Gate content.

**Project resource** is owned by one game: concrete maps, narrative, branded title material, game-specific economy, and normally concrete Items/Skills/Units/Troops/etc. Project resources do not gain RTP fallback merely because a similarly named default could exist.

**Package resource** comes from an explicitly declared dependency beyond the baseline. Packages solve intentional reuse/composition and have declared public authored contracts; they are not an implicit mod-overlay filesystem.

**Studio chrome** exists only for authoring UI. Toolbar/editor icons, themes and other chrome never enter player resolution or export merely because Studio previews game resources.

**Authoring/production libraries** are source inputs and reusable working material. They enter a Project/RTP/Package only through deliberate import/materialization or an explicit authored dependency.

## Ownership follows semantics, not path or file type

JSON is not inherently Project-owned. A reusable Scene/Event composition may belong to RTP; a Project-specific `system.json` remains Project-owned. Conversely, an asset under a generic `system/` directory is not automatically RTP.

Classify by:

- who authors and is expected to customize the resource;
- which runtime/Studio consumers require it;
- whether a fresh Project legitimately inherits it;
- whether absence means “use baseline,” “optional feature not selected,” or “broken Project”;
- whether export must include it because the resolved game actually depends on it;
- provenance/licensing suitability for redistribution.

## Resolution is per resource class

There is no blanket missing-file fallback chain.

For resources that legitimately support inheritance, the conceptual precedence is:

```text
Project-local explicit override
    ↓
explicit Package contribution/override where its contract permits
    ↓
pinned Thestra RTP baseline
    ↓
fail visibly
```

This order is not permission for arbitrary path shadowing. Resource identity, provider, precedence and collision behavior must be declared, inspectable, deterministic and validated.

Project identity/content resources that are required by the game have **no silent RTP fallback**. A missing map, concrete Unit, branded title asset, or other Project-owned dependency fails validation rather than borrowing Second Gate or a convenient default.

Optional RTP templates are selected explicitly; their absence from a Project is normal. Studio chrome resolves only from Studio. Preview placeholders resolve from an explicit RTP preview/default contract when needed and never borrow Second Gate content implicitly.

## Pinned reproducibility

A Project that inherits RTP declares an explicit RTP revision/version identity. Opening the Project under a newer Studio must not silently change gameplay or presentation because a newer RTP happens to be installed.

The architecture therefore requires:

- an RTP revision pin or equivalent immutable resolution identity;
- a compatibility check between the Project, RTP and installed Thestra runtime family;
- explicit pins for Packages when used;
- inspectable provider provenance for inherited resources;
- explicit migration/update when an author chooses a newer RTP.

A linked development mode may make live RTP edits visible during coordinated
development, but reviewed/exported builds resolve explicit revisions.

### Revision identity and metadata (frozen 2026-08-13)

This was left open above until two implementations needed it at once and chose
differently — `A` versus `2026-08-13-390.1`, and `resources.json` versus
`manifest.json`. Both are reasonable; shipping both in one directory is not.
Owner decision:

- **A revision is identified semantically: `1.0`, `1.1`, `2.0`.** The directory is
  `rtp/revisions/<version>/` and `data/system.json` -> `rtp.revision` holds that
  same string verbatim. A major bump signals a change that can break an existing
  Project's authored defaults; a minor bump signals additive content. Someone must
  therefore judge breakage per revision — that judgement is the point, and it is
  what a date or a serial letter cannot express.
- **Exactly one metadata file per revision: `manifest.json`.** It describes
  everything the revision provides — authored data defaults *and* player-facing
  binary resources — with provenance and licensing fields carried on the entries
  that need them.

Two metadata files describing one revision will drift, and licensing evidence
belongs attached to the resource it licenses rather than in a parallel document.
Provenance that a dated directory name would have carried (origin date,
originating issue) lives in manifest fields instead, where it cannot silently
disagree with a path.

The manifest's field-level schema is still open; its filename, location and
single-file-per-revision rule are not.

## New Project: sparse baseline plus Make Local

The preferred authoring model combines **hybrid/sparse materialization** with **explicit Make Local**.

A new Project materializes only the resources that define its own minimum identity/required authored contract. Legitimate baseline RPG resources remain inherited from the pinned RTP. Studio clearly displays their provider and treats them as inherited rather than silently editable Project files.

When an author wants divergence, **Make Local** materializes the resolved authored resource into the Project and deliberately breaks inheritance for that resource. Optional templates are deliberately instantiated/forked; they are not automatically active defaults.

This avoids copy-everything Git noise while preserving reproducibility and explicit ownership. It also avoids unversioned inherit-everything behavior that makes Projects depend on whichever Studio happens to open them.

A sparse Project is therefore **locally sparse, not semantically blank**. It may omit a local copy of legitimate house-baseline behavior while the resolved pinned game still knows how to perform those ordinary operations. Moving policy from Lua into authored data must not make New Project forget how to function; the pinned RTP is the authored provider, not an unversioned native fallback.

## Preview semantics

Studio previews fall into two classes:

1. **Project-specific preview** — resolves the Project's actual resource graph, including its RTP/Package dependencies and local overrides;
2. **generic authoring preview** — uses explicit Studio chrome and, when player-facing representative content is genuinely required, a pinned RTP preview/default resource.

A generic preview must never silently borrow a Second Gate battler, model, sprite, icon, windowskin, tileset or effect because that file happens to be available in the source checkout.

“No representative sprite” is a valid preview state where the renderer can support it. When a representative resource is semantically required, use a deliberate neutral RTP placeholder and fail visibly if it cannot resolve.

## Authored semantic layer and Packages

The RTP is more than fallback assets. It is a Thestra-authored library built from the same Scene/Event/command substrate available to Projects.

Native runtime code should own stable reusable semantic capabilities. Higher-level reusable compositions should remain authored where the substrate is expressive enough. RTP templates provide a built-in library of such compositions; future Packages provide explicit reusable dependencies beyond the baseline.

Do not force RTP templates to become Packages before #325's package contract is mature. Conversely, do not use RTP as a dumping ground for every reusable system that should eventually be an explicit dependency.

## Export invariant

Authoring may resolve:

```text
installed compatible Thestra runtime
+ pinned RTP
+ pinned explicit Packages
+ Project
```

A normal export resolves and materializes the complete depended-upon player game. It contains all required runtime code, RTP resources/compositions, Package resources and Project-local content. The player does not install Studio, RTP, or Packages separately.

No exported game may reach back to the source checkout, an installed authoring library, a global RTP directory, or a Package development checkout.

## Relationship to the monorepo move

Before `projects/second-gate/` is physically populated wholesale, ownership must be classified sufficiently that:

- runtime implementation support does not remain inside Project `data/`;
- mixed authored semantic registries are not moved wholesale merely because they currently live under `data/`;
- baseline Scene/menu/UI resources are not accidentally declared Second Gate-owned;
- Second Gate branding, game policy and content are not promoted into RTP merely because Studio currently depends on them;
- Studio chrome remains Studio-owned;
- shared authoring/production sources do not become shipped Project resources by directory accident.

Unresolved resources stay unresolved until a bounded implementation/audit slice establishes their semantic owner.

## Durable acceptance invariants

- Players never need a separately installed RTP for normal exported games.
- Projects never resolve against unversioned “latest installed” defaults.
- RTP defaults are inherited only for resource classes where inheritance is legitimate.
- RTP gameplay/presentation defaults may be deliberately JosephSeraph-shaped; neutrality is not a design acceptance criterion.
- Missing required Project resources fail visibly rather than silently substituting defaults.
- Optional templates are explicitly selected/instantiated.
- Studio exposes resource provider/ownership for inherited content.
- Make Local is an explicit ownership transition, not an accidental edit of shared source.
- A sparse Project may be locally minimal while remaining semantically functional through its pinned house baseline.
- Project, Package, RTP and Studio identities do not collapse into filesystem precedence.
- Generic Studio previews do not borrow Second Gate content implicitly.
- Export materializes the exact resolved dependency graph into a self-contained player game.
- Current concrete Items/Skills/Units remain Project-owned by default; reuse is demonstrated, not assumed.
- Battle's owner-supervised native files are not modified merely to establish RTP ownership.

Agent-Signature:
  platform: ChatGPT
  model: GPT-5.6 Sol
  role: documentation
  task: "#385 / #548 house-baseline clarification"
  base: 12f53777d883510ab2cb133beea7cf15d434b31f
