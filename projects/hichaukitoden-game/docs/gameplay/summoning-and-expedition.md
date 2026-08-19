---
type: design
scope: game
status: active
---

# Summoning and expedition

## Summoner role

The protagonist's strategic identity is the **Summoner**: a commander/support driver whose main decisions are which spirits to contract and field, how to arrange them, when to spend limited expedition resources, and when to stop pushing deeper.

The Summoner should not collapse into a conventional seventh damage dealer. Direct intervention can exist, but the game should keep composition, support, positioning, consumables, and spirit management at the center of the player's agency.

## Contracts and spirits

Spirits are persistent individual beings. A contract is therefore both a party-building decision and an attachment decision, not merely acquisition of a species token.

A strong contract should change the shape of an expedition. Power is allowed to carry logistical cost: a creature can be desirable precisely because taking it changes what is safely possible afterward.

Saban is the opening attachment anchor and establishes the intended relationship between Summoner and spirit: companion/carrier/contracted being rather than a disposable collectible.

## Shared expedition pressure

The design uses a shared Summoner resource as a major pressure on party and expedition decisions. Its purpose is to make powerful commitments compete with endurance and to give the player reasons to forecast the return journey.

**Do not freeze old MP formulas here.** Exact activation, traversal, Veil, regeneration, and starting-capacity behavior is active balance/implementation work. In particular, GitHub issues [#372](https://github.com/JosephSerUSP/Second-Rite/issues/372) and [#373](https://github.com/JosephSerUSP/Second-Rite/issues/373) own current experiments around the MP economy.

The stable design requirement is the pressure relationship, not one historical formula.

## Push versus return

An expedition should repeatedly create an understandable choice between gaining more by continuing and preserving enough safety to return. The player should be able to form a reasoned opinion about that choice before disaster, even when the information is imperfect.

Returning is part of play. Extraction/portal behavior must support this tension rather than erase it; current implementation questions belong to [#686](https://github.com/JosephSerUSP/Second-Rite/issues/686).

## Loss and aftermath

Spirit loss may be permanent and should matter because the lost spirit was an individual part of the player's plan and history. Loss is not valuable merely because it is punitive.

Emergency reserve behavior may prolong a failing expedition, but terminal failure must remain legible and authored. Current full-wipe/Game Over direction belongs to [#689](https://github.com/JosephSerUSP/Second-Rite/issues/689).

Consequences should be felt diegetically where possible: altered party composition, changed rooms or reactions, absence, memory, and practical consequences are stronger than an abstract “permadeath” label carrying the entire meaning.

## Formation and autonomy

Creature roles should remain legible enough that the player can plan a formation and understand why it behaved as it did. Autonomy is valuable when it expresses temperament/role and reduces menu micromanagement without making outcomes feel arbitrary.

Exact AI/formation rules are authored/runtime facts and should be documented in data/technical authorities when implemented; this note only owns the game-design purpose.

## Authority note

This is design intent, not a balance table or implementation ledger. Current numeric values live in Project data; unresolved work lives in GitHub Issues. Historical source notes are preserved under [Legacy repo design](../archive/legacy-repo-design/README.md).
