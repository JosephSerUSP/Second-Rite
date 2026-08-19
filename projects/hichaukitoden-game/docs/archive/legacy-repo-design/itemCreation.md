# Item Creation

> **Intent, not status.** This document describes the player-facing system and
> its design constraints. For implementation inventory use
> [`docs/ENGINE-STATE.md`](../ENGINE-STATE.md); for reviewed engine behavior use
> `docs/SPEC.md`.

The appeal is **breadth** — a vast combination space that dangles possibilities
in front of the player, like exploring a latent space of items. That is why
there is deliberately **no recipe table**: authored exact-match recipes would
narrow the very thing that makes the system exciting.

The first model undercut that ambition by compressing two ingredients and a stat
into one scalar and then one of a few tier brackets. Everything reached the
outcome through a tiny channel, so ingredients had little identity and nothing
the player learned accumulated. This design widens the space instead of adding
more content to a narrow lookup.

---

## 1. Each discipline is its own space

**Form is categorical and comes from the crafter. Element and intensity are
continuous and come from the ingredients.**

A cook cannot forge a sword — not because a rule forbids it, but because
cooking *is* the act of making food. The gate is definitional, so it needs no
threshold, penalty, or rare cross-discipline escape hatch.

There is no single craft space. There are four, one per discipline, each small
and dense rather than one huge sparse map: **hue plane × value axis ×
intensity**. Recruiting a crafter unlocks another way of navigating that space.

## 2. Elements are a colour space

The element relationships have different geometry:

- **Red > Green > Blue > Red** is a cycle, so the three sit 120° apart on a hue
  plane.
- **White ↔ Black** is a true opposition, so it is one signed value axis.
- **Non-elemental** is the origin of both.

Consequences follow from that geometry:

- mismatch relocates rather than subtracting a flat penalty;
- White/Black can cancel fully while RGB mixtures grade toward the centre;
- deep-element outcomes require scarce saturation/purity;
- blending may use the same authored element-relation vocabulary that battle
  uses so crafting and combat do not invent contradictory elemental topology.

## 3. Signatures are read, not redundantly authored

An item's position should be derived from properties it already owns. Parallel
hand-authored "craft potency" fields are dangerous because they can drift away
from price, effects, traits, name, and fiction.

Useful sources include:

| source | contributes | design confidence |
|---|---|---|
| semantic traits | element | exact when a trait names an element |
| semantic effects | element | strong when an effect implies an element |
| name / description | element | deliberately weaker authored-language signal |
| cost | intensity | the game's authored statement of worth, transformed nonlinearly |

New semantic effects/traits should participate through registry metadata or
another shared mapping, not a growing set of item-specific crafting branches.

Naming therefore matters: an authored name can be a weak semantic signal, but it
must not outweigh explicit mechanical identity.

**Intensity may have a small enumerated override family** for deliberate cases
where price is not the intended statement of rarity/power. Prefer named grades
multiplying the derived value over another free absolute number that can drift.

## 4. Membership says what a craft can produce

An item may belong to one or more crafting disciplines. Obvious membership can
be derived from what the object is; authored membership exists for meaningful
fictional overlap such as a spring-loaded blade that belongs to both tinkering
and blacksmithing.

Overlap is an efficient density multiplier: a useful item can populate more
than one discipline's neighbourhood without duplicating content.

## 5. The craft

**The crafter is the third vertex.** Two ingredients define a line; the crafter's
innate elements pull the ideation point away from that line. Crafting identity
comes from what a creature *is*, not what it temporarily wears, so equipment
cannot make the whole roster equivalent.

Ingredients are ungated, but a foreign ingredient should steer more readily than
it empowers. That lets strange materials influence an attempt without making a
non-native discipline trivially reach the same high-value region.

**Precision is scatter.** Better discipline aptitude narrows the random
displacement around the ideation point. Mastery means the same intended mixture
becomes more predictable rather than merely adding a larger success number.

**Reach is a falloff, not a wall.** Difficult outcomes remain possible near the
edge of a crafter's capability; excess distance makes them unlikely rather than
forbidden. There is no separate anomaly/critical-craft jackpot required — the
interesting result is the edge-case outcome produced by a coherent mix.

**Determinism is per attempt.** The attempt's seed belongs to save state so
reloading the same attempt reproduces its result while a genuinely new attempt
rolls fresh. This prevents simple save-scumming without turning crafting into a
public recipe lookup.

**Resolution is nearest-neighbour** over producible items in element/value/
intensity space plus reach cost. Both ingredients are consumed and an attempt
always resolves to something; incoherent mixtures should naturally fall toward
weak central outcomes rather than requiring a special failure item category.

## 6. What the player sees: nothing numeric

Numeric expected-yield/tier readouts collapse discovery into optimization. The
confirm screen should instead communicate through diegetic signals:

1. **Crafter reaction** — a line that reflects coherence before commitment.
2. **Outcome reel** — nearby possibilities pass in distance order; decisive or
   wandering motion communicates coherence.
3. **Unknown silhouettes** — nearby but undiscovered items can appear as `???`,
   making the space feel explorable.
4. **Colour** — because the ideation point is literally an elemental colour
   coordinate, light/hue can communicate direction without exposing numbers.

The player should learn to read the crafter and the space, not a formula sheet.

## 7. Why the roster is the real content

Crafting aptitude should reuse meaningful creature levers rather than inventing
one universal Craft stat. A creature can be poor in battle but valuable as a
specialist crafter; innate element and discipline aptitude create recruitment
reasons outside combat.

Products and ingredients share the same item space, so a crafted object can
become a new coordinate the player owns and use it to reach elsewhere.

This yields the durable authoring rule:

> **Every discipline wants low-to-mid-intensity steering material across the
> elemental space and crafters with meaningfully different innate directions.**

A discipline missing an element from both its reagent pool and its crafter
coverage has a real hole that tuning scatter cannot repair. Item counts and
coverage are implementation/content census and therefore belong in generated
state or analysis tooling, not this design document.

## 8. What crafting is for

Crafting is allowed to reach progression-changing objects such as promotion
keys, skill-learning items, and permanent parameter gains when the surrounding
progression design permits them. Their rarity should come from reach, pool
composition, and authored eligibility rather than an arbitrary rule that
"important items cannot be crafted."

Skill-teaching safety remains stricter because generative inheritance can bypass
progression accidentally; see `content-engine-gaps.md` for the durable tome
policy.

## 9. Design questions, not delivery status

Two choices remain legitimate to revisit as playtesting evidence accumulates:

- whether crafting should gain a dedicated precision-modifying trait distinct
  from reach/yield modification;
- whether **alignment depth** should strengthen a crafter's pull, or whether
  repeated alignment of the same element should remain directionally equivalent
  for crafting.

These are balance/system-design questions. They should not be represented here
as claims about which fields, holders, item counts, or promotion schemas happen
to exist in a particular revision.
