---
type: design
scope: game
status: active
---

# Items and crafting

## Purpose

Items, food, equipment, and crafting should reinforce Second Gate's expedition loop rather than become a parallel inventory minigame with no relationship to descent, return, creatures, or preparation.

The important questions are practical: what does the player prepare before leaving St. Maria, what can be discovered or made from what comes back, what changes an expedition plan, and what makes a creature or route newly viable?

## Food and recovery

Food can support recovery and preparation while also revealing creature individuality through preferences and interactions. Meals should be useful enough to matter without making all other recovery/resource pressure irrelevant.

Favorite-food or savor-like behavior is valuable when it creates a memorable relationship between a particular creature and a particular item rather than merely adding another hidden multiplier.

## Creation and combination

Crafting may include cooking, fusion/combination, transformation of materials, and authored recipes. The stable design preference is **meaningful conversion**, not recipe-count inflation.

A recipe earns its existence when it creates a new preparation choice, teaches the player something about materials/creatures/world, or changes the value of exploration. Avoid large catalogs whose primary purpose is completion percentage.

## Equipment and item identity

Equipment should have enough identity that choosing it is more than taking the largest number. Effects, tradeoffs, resource relationships, elemental implications, and creature/build fit are more interesting than raw tier replacement alone.

Icon and atlas assignments are presentation/content data, not design authority. Historical item-atlas proposals are retained only as provenance.

## Numeric authority

Historical documents contain concrete prices, values, recipes, icon assignments, and implementation notes. They are not automatically current.

Current item definitions and recipes live in Project `data/`. Use the [legacy repo-design archive](../archive/legacy-repo-design/README.md) when recovering rationale from the older `itemCreation.md` or `item-atlas-expansion.md`, then verify any concrete value against authored data before treating it as current.
