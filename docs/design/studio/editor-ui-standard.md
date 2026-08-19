# Editor UI Standard

**Status: draft, owner to confirm.** This records the layout rules for Thestra
Studio so that UI criticism can be judged against a stated standard rather than
invented per reviewer. Items marked *(established)* come from decisions the owner
has already made; items marked *(proposed)* are inferred from those decisions or
from the current editor, and need confirming or replacing.

Intent only, per `AGENTS.md` — this describes how the editor **should** look, not
how it currently does. Where the editor disagrees with this document, the editor
is wrong or this document is, and someone must decide which.

This governs the **editor**. Game UI text is governed separately by
[`ui-text-style.md`](../../../projects/hichaukitoden-game/docs/archive/legacy-repo-design/ui-text-style.md); the two do not overlap.

## 1. Density

**Tight and compact. Generous spacing is explicitly rejected.** *(established)*

The reference point is the RM2003-era tool aesthetic: dense, boxy, information-
first. This is deliberate and matches the engine's own lineage. A screen that
would be called "cramped" by contemporary web-design convention is usually
correct here.

Consequences *(proposed)*:

- Prefer showing more fields at once over scrolling or progressive disclosure.
- Do not add padding to "let a form breathe". Breathing room is not a goal.
- Vertical rhythm matters more than whitespace: consistent row heights beat
  generous gaps.

## 2. Grouping

**Related fields live in a titled groupbox. Ungrouped floating fields are a
defect.** *(proposed — this is the rule the current editor most often breaks)*

A groupbox is the unit of meaning. If a set of controls is only comprehensible
together, it needs a visible border and a title saying what it is.

A field that sits alone with no group and no heading forces the author to infer
its scope from position, which is exactly the failure mode that makes a tab feel
bad to use even when every individual control is fine.

Corollary: a group with one field is usually a sign the grouping is wrong, not
that the field needs a box.

## 3. Cross-tab consistency

**The same concept is presented the same way in every tab.** *(proposed)*

This is the most objective rule in this document, because it is a comparison
rather than a preference. If an atlas coordinate is a paired row/col input in one
tab and a single combined field in another, one of them is wrong regardless of
which is nicer.

Applies to at least: atlas coordinates, colour pickers, asset/model pickers,
weight and probability fields, condition or `where` expression editors, and
enable/disable toggles.

## 4. Labels and affordances

*(proposed)*

- Every control has a visible label. A control identified only by placement,
  icon, or placeholder text is a defect.
- An icon-only control needs a tooltip naming the action.
- A control whose effect is not observable from the same screen should say what
  it affects.

## 5. Scope boundaries

*(proposed)*

- A tab edits one kind of thing. If a tab edits two unrelated kinds, that is a
  structural defect, not a layout one — record it as such.
- Modals are for a single decision or a single sub-record. A modal that contains
  its own tab strip is a sign the surface belongs elsewhere.

## 6. What is NOT a violation

This list exists because UI criticism expands to fill available attention, and
an audit is worthless if it reports everything.

- Colour choices, unless they break a distinction the author relies on.
- "Looks dated." Dated is the intent — see §1.
- Density that feels high. Also the intent.
- Anything requiring product judgement about what the feature *should do*. That
  is a design question, not a layout finding.
- Absence of animation, transitions, or modern web-app conventions.
- A layout that is ugly but unambiguous. Prefer reporting ambiguity over taste.

## 7. Using this in review

A finding should name the rule it violates and the frame or surface where it
occurs. A finding that cannot cite a rule from this document is either taste, or
evidence that this document is missing a rule — say which.

Because a G6 frame exists for most editor surfaces, most findings should be
citable to a specific screenshot. Surfaces with **no** G6 frame cannot be
audited visually at all; note them rather than guessing, and treat the gap as
input to #254. As of writing, Tileset Studio has exactly one frame
(`tileset-studio/default.png`) and its role tabs and variant panel are
uncaptured.
