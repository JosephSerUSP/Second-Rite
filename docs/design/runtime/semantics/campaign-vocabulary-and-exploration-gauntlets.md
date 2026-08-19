# Campaign vocabulary and exploration gauntlets

This document records two related design conventions:

1. what **Campaign** means in Thestra/Second Gate design language; and
2. how **exploration gauntlets** may be used as an authoring and design-research method.

> **Intent, not status.** This is a design vocabulary and method document. It does not assert that Thestra Studio currently implements a Campaign object, gauntlet runner, model integration, rating UI, or any other feature described here. `docs/ENGINE-STATE.md` remains authoritative about what exists.

The two conventions belong together because campaign-scale gauntlets need a word for the complete designed game experience they are perturbing. The word must remain useful without reviving the retired architectural meaning of Campaign as a runnable root alongside Project.

---

## 1. Vocabulary

### Project

A **Project** is the canonical independently runnable and authored game identity.

Project is an architectural and ownership concept. It defines the game whose authored resources, metadata, dependencies, runtime compatibility, export, and Project-local overrides are being resolved.

Project is therefore the word to use when discussing:

- what opens in Thestra Studio;
- what owns authored game content;
- what can be validated, previewed, test-played, or exported;
- what declares RTP/package/runtime dependencies; and
- what constitutes one independently runnable game.

### Campaign

A **Campaign** is the designed totality of a sustained playable progression inside a Project: the game as an experience from beginning to end, including the relationships among its situations, places, encounters, characters, discoveries, rewards, pacing, optionality, escalation, and endings.

Campaign is a **design/content concept**, not a runtime root or storage ontology.

A Campaign describes a space of authored possibilities. It may contain branches, optional content, mutually exclusive outcomes, systemic variation, and other structures that no single player experiences in full.

Campaign is therefore useful for statements such as:

- “Second Gate has one primary Campaign.”
- “This proposal changes the Campaign’s middle without changing the combat system.”
- “The Campaign repeatedly alternates expedition and return-to-town consequences.”
- “This optional arc exists in the Campaign but did not occur in this playthrough.”

A Campaign may be highly linear, highly branching, systemic, episodic, or some mixture. The term does not imply a quest log, chapter menu, D&D-like scenario format, or any particular engine representation.

### Playthrough

A **Playthrough** is one realized traversal of a Project’s playable content.

Where a Campaign describes authored possibility, a Playthrough describes what actually happened during one run. A Playthrough may omit optional Campaign content, choose one branch among several, fail to discover secrets, or produce systemic outcomes that differ from another run.

The distinction is important:

```text
Project
  -> Campaign: designed possibility space
       -> Playthrough: one realized traversal
```

### Arc, chapter, scenario, sequence

These are ordinary subordinate design terms rather than engine ontologies.

- **Arc** emphasizes a coherent development across multiple situations.
- **Chapter** emphasizes explicit authored segmentation.
- **Scenario** emphasizes a bounded playable situation or premise.
- **Sequence** emphasizes ordering without implying a stronger narrative structure.

Projects may use whichever terms fit their form. Thestra does not need to force every game into the same hierarchy.

### Campaign interpretation / campaign proposal

A **Campaign interpretation** or **Campaign proposal** is a hypothetical unfolding of current design premises into a complete or partial Campaign.

It is exploratory material, not canonical content merely because a model, agent, or author produced it.

This term is especially useful for gauntlets: several Campaign interpretations can be compared without any of them becoming the Project’s authored Campaign.

---

## 2. Hard architectural boundary

**Campaign must never become an alternative Project ontology again.**

Campaign is not:

- a runnable root beside Project;
- a Project lifecycle state;
- a filesystem ownership boundary;
- a protocol for opening or switching games;
- an export unit that competes with Project;
- a hidden replacement for Package or RTP; or
- a second namespace through which Project-owned content resolves.

A Project may contain one Campaign, several Campaigns, or no useful Campaign concept at all.

For example:

- a conventional RPG may have one primary Campaign;
- an anthology Project may reasonably contain several Campaigns;
- a tactics Project may contain multiple independent Campaigns;
- Pong may not benefit from the term Campaign whatsoever.

The absence of a Campaign concept must never make a Project less valid.

If Thestra later gives Campaign a first-class authoring representation, that representation must remain **Project-authored content inside the Project boundary**, not a competing root identity.

---

## 3. Exploration gauntlets

An **exploration gauntlet** repeatedly subjects an incomplete creative hypothesis to controlled counterfactual unfoldings so the author can inspect what possibilities, weaknesses, recurring structures, and unexpected consequences are latent inside it.

The purpose is not necessarily to generate shippable content.

The useful loop is:

```text
explore
  -> evaluate
  -> articulate findings
  -> author deliberately
```

not:

```text
generate
  -> import
```

A model in a gauntlet is therefore closer to a tireless improviser, critic, dramaturg, simulated player, or design probe than an outsourced content author.

The output of a gauntlet is a set of **specimens** for human judgment.

The human author remains the fitness function and the authority that decides what, if anything, becomes canonical.

---

## 4. Why gauntlets are useful

Ordinary brainstorming asks what the author can consciously propose from the current design state.

A gauntlet instead creates many objects for the author to react to.

This is valuable because creative preference is often easier to identify through selection and rejection than through prior specification. “Absolutely not this,” “this tiny consequence is fascinating,” or “all five models accidentally made the same assumption” can expose design truth that another page of abstract intent would not.

Gauntlets can therefore help distinguish:

- an idea that sounds attractive from one that actually produces interesting downstream consequences;
- a character biography from a character who generates distinctive behavior under pressure;
- a system premise from the Campaign rhythms it naturally creates;
- a missing design decision from a genre convention models are silently filling in;
- a fertile idea from a sterile but superficially exciting one; and
- a real architectural limitation from one model’s failure to use the available authoring grammar.

### Generativity as a design property

A particularly useful criterion is **generativity**:

> If this idea is accepted, how many worthwhile consequences, situations, decisions, relationships, or reinterpretations does it create?

A strong design idea often does more than solve one problem. It creates a network of consequences that can sustain content.

Gauntlets are well suited to discovering that fertility because the same premise can be unfolded repeatedly under different pressures.

---

## 5. Useful gauntlet families

The following are families of inquiry, not required Studio features.

### Character gauntlet

Place one provisional character under many mundane, social, emotional, and practical pressures.

The goal is to test whether the character remains recognizable, surprising, and behaviorally productive without relying on biography exposition, catchphrases, or one dramatic secret.

Useful tests include boredom, embarrassment, being wrong, needing a favor, refusing a favor, lying, misunderstanding, losing status, gaining leverage, routine work, and encounters with people they know differently.

### Relationship gauntlet

Test pairs or small groups rather than isolated character sheets.

The goal is to discover asymmetric obligations, resentment, affection, dependency, shame, rivalry, misrecognition, habits, and other structures that reliably generate scenes.

A relationship is stronger when A-with-B produces a dynamic that is not interchangeable with A-with-C.

### Settlement / social-system gauntlet

Simulate a small community without the player at the center.

The goal is not to canonize autonomous simulation logs. It is to discover routines, gossip paths, dependencies, recurring conflicts, mundane habits, social bottlenecks, and consequences worth deliberately authoring.

### Campaign unfolding gauntlet

Give several models the same frozen Project/design premises and ask each to unfold them into a complete Campaign interpretation under different constraints.

Useful lenses include:

- conservative expansion;
- systems-first expansion;
- character-first expansion;
- mystery-first expansion;
- severe low-budget expansion;
- deliberately eccentric or nonlinear expansion;
- hostile-critic expansion; and
- minimum-content complete-game expansion.

The purpose is to explore the possibility-space of the existing design, not to select a machine-written Campaign wholesale.

### Missing-middle gauntlet

Freeze a known beginning and a known later state, then generate many structurally distinct ways of making the transition meaningful.

This is useful when the project knows **A** and **Z** but the interesting design problem is what experiences make Z feel earned, surprising, legible, or inevitable.

Prefer structural sequences and consequences over prose scenes when the question is fundamentally one of game design.

### Mechanic-consequence gauntlet

Hold a mechanic fixed and repeatedly ask what Campaign, economy, encounter, social, or progression consequences follow if that mechanic is taken seriously.

This is useful for discovering whether a mechanic is fertile enough to deserve its complexity.

### Scope-reduction gauntlet

Ask how much can be removed while preserving the work’s identity and satisfying structure.

This is not merely production triage. Removing content can expose which relationships and rhythms are actually carrying the game.

### Hostile-critic gauntlet

Ask the model to falsify the design rather than complete it.

Examples:

- Where does this premise run out of fuel?
- Which current mechanic produces no worthwhile Campaign consequences?
- Which supposed mystery can only be sustained by characters behaving irrationally?
- Which content requirement is likely to explode production cost?
- Which two concepts are redundant?

A gauntlet that only tries to make the current design succeed will systematically hide some of the most useful evidence.

---

## 6. A practical gauntlet protocol

### 6.1 Freeze the seed

State the current known premises, invariants, and deliberate unknowns.

Do not allow each model to silently repair the seed by inventing a different game.

Separate:

- **fixed facts** — assumed true for this run;
- **open questions** — intentionally available for exploration;
- **forbidden substitutions** — core premises the model may not replace; and
- **scope constraints** — budget, length, available systems, cast size, asset constraints, or other realities.

### 6.2 Vary one meaningful pressure at a time when possible

Different models, temperatures, or prompts are less informative if every run also changes the design question.

Controlled variation makes disagreement interpretable.

### 6.3 Preserve specimens before synthesis

Do not immediately ask another model to merge all outputs into one “best” answer.

Early synthesis destroys useful disagreement.

The author should be able to inspect individual specimens and react to specific decisions before patterns are summarized.

### 6.4 Human evaluation is primary

Numeric ratings may help compare runs, but qualitative reactions are more informative.

Useful Campaign-scale criteria include:

- deepens existing concepts instead of adding unrelated ones;
- creates worthwhile consequences on return to earlier spaces;
- gives characters genuine structural functions;
- gives mechanics emotional or dramatic meaning;
- produces strong pacing/rhythm;
- preserves desired ambiguity;
- is surprising without feeling arbitrary;
- is materially achievable;
- is generative;
- feels specific to this Project;
- relies too heavily on genre defaults;
- inflates scope;
- over-explains lore;
- resolves conflict too neatly; and
- adds systems where content would suffice.

The most useful evaluation field is often freeform: **what specifically caused the reaction?**

### 6.5 Extract findings, not just winners

A gauntlet run can succeed even when every specimen is rejected.

Record findings such as:

- “Every version that makes X central causes Y pacing problem.”
- “The town becomes more interesting whenever dungeon discoveries have mundane social consequences.”
- “This NPC only works when paired with someone who can refuse them.”
- “Models keep inventing a boss at this point because the design leaves the beat unspecified.”
- “Removing this mechanic barely changes any Campaign interpretation.”

These are more reusable than a single preferred output.

### 6.6 Canonicalization is explicit

No gauntlet specimen becomes Project truth automatically.

Promotion should be a deliberate authoring act: rewrite, adapt, or encode the chosen insight in the Project’s actual design/content sources.

---

## 7. Recurrence across models: evidence, not proof

If several models independently produce the same solution, that recurrence is interesting but ambiguous.

It may indicate:

1. **design pressure** — the current premises genuinely make that solution attractive;
2. **genre gravity** — models are filling an underspecified gap with a common convention;
3. **prompt leakage** — wording implicitly suggested the same answer; or
4. **training-set familiarity** — the models share the same cultural prior.

A useful follow-up is to explicitly forbid the recurrent solution and see what alternatives emerge.

For example, if nearly every Campaign interpretation ends each dungeon stratum with a boss, do not immediately conclude that the game structurally requires bosses. Run a second gauntlet in which strata are forbidden from ending in boss fights. If the alternatives collapse, the boss may be serving real structural needs; if they flourish, the original recurrence was probably genre gravity.

---

## 8. Character-simulation failure modes

LLM simulations have predictable social-writing biases that should be treated as adversarial test targets rather than accepted style.

Watch especially for:

- premature reconciliation;
- therapeutic emotional literacy from every character;
- characters correctly explaining their own motives and trauma;
- symmetrical relationships;
- tidy scene arcs;
- escalation toward significance in every exchange;
- everyone becoming unusually interested in the protagonist;
- exposition disguised as intimate dialogue;
- eccentricity reduced to catchphrases; and
- every conflict becoming an opportunity for growth.

Mundane unresolved friction is valuable evidence. People may misunderstand one another for years, avoid questions, behave differently around different peers, retain petty resentments, or simply have conversations that do not advance the plot.

A character should ideally be identifiable by how they perceive and act on a situation, not merely by verbal tics.

---

## 9. Relationship to Thestra authoring

Exploration gauntlets are compatible with Thestra’s broader authoring philosophy precisely because they need not become runtime AI.

They can remain an upstream design practice:

```text
Project/design truth
  -> counterfactual simulations
  -> human comparison and rating
  -> articulated findings
  -> deliberate authored changes
  -> ordinary Project data/assets/events
```

This permits AI-assisted exploration while preserving a fully authored shipped game.

A future Thestra Studio tool could make this workflow easier — for example by packaging selected Project facts, presenting specimens, collecting ratings, or retaining experiment history — but such a tool should not silently write generated material into canonical Project data.

The important capability is not “generate content.” It is **increase the number and diversity of counterfactual versions an author can think through before committing**.

---

## 10. Non-goals

This document does not propose:

- runtime LLM-driven NPCs;
- autonomous canonical story generation;
- an AI requirement for shipped Thestra games;
- automatic import of generated dialogue, maps, encounters, or Campaigns;
- a new Campaign protocol or filesystem root;
- a Campaign lifecycle parallel to Project;
- a mandatory Campaign editor for every Project type; or
- implementation of a gauntlet runner merely because the design method is useful.

The method should earn tooling through repeated use. If manual gauntlets already produce valuable design discoveries, that evidence can later justify the smallest reusable authoring support.