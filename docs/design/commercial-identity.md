# Commercial Identity — Working Direction

> **Intent, not status.** This document describes what we mean to build and why.
> For what is actually implemented right now, read the generated
> [`docs/ENGINE-STATE.md`](../ENGINE-STATE.md) (gated by G4); for how the engine
> works, `docs/SPEC.md`. Where this document and those disagree about current
> implementation, they win.

Status: working product and narrative direction. This document records current
owner intent; it does not replace the technical specification, authored
walkthrough, or detailed mechanic-specific design documents.

## Name and framing

- The player-facing game title is **Second Gate**.
- **The Second Rite** remains valid in-fiction terminology for the ritual/bond
  concept already present in the game's lore. Product naming and in-world naming
  are intentionally distinct.
- Internal repository/tool identifiers may retain historical codenames under the
  naming policy tracked separately; this document is not an identifier authority.
- **Thestra Studio** is the authoring environment, not the title of the game.

## Aesthetic and cultural position

Second Gate should feel like a dark, strange PSX/SNES-era RPG remembered through
another culture rather than like a generic modern retro pastiche. Its strongest
visual identity is increasingly **first-person, low-poly, PSX-like 3D** joined to
period-shaped RPG interfaces, sparse but expressive character art, and authored
moments that spend visual detail in odd places.

The game is a Brazilian developer's homage to the experience of encountering
Japanese games, songs, fantasy and localization from outside Japan and outside
the anglophone center. Intentional awkwardness may appear in writing and
presentation when it is comprehensible, specific and evocative rather than
randomly incorrect.

Queer experience can remain embedded in relationships and world texture without
needing to become a marketing category.

The setting may also admit unmistakable fragments of the creator's own lived
world without immediately explaining them through conventional fantasy lore. The
planned São Paulo Metro stratum is the strongest current example; see
[`../game design/sao-paulo-metro-stratum.md`](../game%20design/sao-paulo-metro-stratum.md).

## Product promise

**Second Gate is a compact first-person summoner dungeon RPG about descending
beneath remote St. Maria with contracted spirits, deciding how much danger and
resource pressure you can afford, and living with who makes it back.**

The core emotional promise is **attachment under logistical pressure**:

> Bring strange companions into a place that wants you to keep going, and learn
> when power is worth the cost of getting everybody home.

The core narrative promise is **place, memory and unexplained recurrence**:

> Return to a small town that remembers what happened on the expedition while
> the Labyrinth becomes less compatible with any simple history of the world.

Second Gate should be marketable through concrete situations before abstract
system explanation. Saban in the rented room, the Crossing Writ, the first gate,
Cerberus collapsing the player's safe resource margin, an altered room after a
loss, and later impossible strata are stronger hooks than a list of economy
subsystems.

## Player, St. Maria, and spirits

- The player is a Summoner and outsider arriving in St. Maria for money/power,
  not a chosen hero awaiting prophecy.
- St. Maria is a small authored place the player physically inhabits rather than
  a shop/menu abstraction.
- Townspeople should remember expedition history through restrained authored
  reactions, services, relationships and altered spaces.
- Saban is the opening attachment anchor: an already-contracted Moa whose prior
  owner has been erased from the contract.
- Spirits/creatures are contracted beings with individual persistence and
  history, not disposable collectible tokens. A species may have many possible
  instances, but attachment should come from the particular companion the
  player actually took with them.
- Powerful creatures should create concrete expedition tradeoffs rather than
  being strictly dominant upgrades. Cerberus's extreme resource pressure in the
  opening is the model: power can shrink the distance the player can safely
  afford to travel.

## Expedition, return, and loss

The **return journey matters as much as the descent**.

Second Gate should repeatedly ask the player to judge whether one more room,
one more battle, one more recruit, or one more treasure is worth reducing the
margin needed to come home.

Current durable principles include:

- shared Summoner MP is expedition pressure, with exact spend formulas owned by
  the active balance work rather than this commercial document;
- individual spirits may be permanently lost when battle resolution leaves them
  unrecovered;
- reserve/emergency deployment can prolong a disastrous expedition rather than
  making one field wipe equivalent to instant game over;
- ritual sacrifice/reaping may remain mechanically important, but **sacrifice is
  not required to carry the external product pitch**;
- consequences should be individual and diegetic where practical rather than a
  generic batch punishment screen;
- returning to town should create emotional and informational aftermath, not
  merely refill resources.

Do not describe Second Gate as a conventional roguelite unless the shipped game
actually adopts the persistent meta-progression expectations that term implies.

## Dungeon scale and strata

Second Gate is intentionally compact, but compact does **not** mean a three-floor
microgame.

Current owner scope direction:

- **9 dungeon floors:** bare minimum;
- **12 floors:** comfortable working target;
- **15 floors:** desirable if authoring throughput allows equal density rather
  than diluted content.

Do not lock a public floor count until production evidence supports it.

Floors should become memorable through authored discoveries, resource decisions,
encounter identity, revisitation and town consequences rather than through raw
geometry size alone. Strata should function as meaningful changes in what the
player thinks the Labyrinth is.

The São Paulo Metro is intended as one major middle-to-late-game stratum: a
contemporary space the player recognizes while St. Maria can only interpret it
as the work of an unknown/ancient civilization. Its exact floor assignment is
not frozen.

## Narrative and endings

- The antagonist is a person; the deeper route should reveal or reframe their
  identity rather than end only on an abstract cosmic force.
- A surface ending should feel complete enough to matter while leaving an
  unresolved wrongness.
- A deeper ending may demand player knowledge in the tradition of
  *Valkyrie Profile*: possible on a first playthrough for an informed player,
  deliberately non-obvious, and meaningfully reframing rather than merely
  adding a harder boss.
- Creature/spirit history may affect narrative texture and ending conditions,
  but do not turn the whole game into morality accounting.
- The Labyrinth should increasingly resist a single archaeological explanation.
  Contemporary São Paulo appearing beneath St. Maria is evidence, not an answer.

## External presentation

Lead with the fantasy a player can understand in seconds:

> **Descend beneath St. Maria with a party of contracted spirits. Spend your
> Summoner's strength to survive, decide when to turn back, and bring home the
> companions you can.**

Then demonstrate the specificity:

- remote St. Maria;
- first-person dungeon descent;
- Saban and other individually persistent spirits;
- dangerous party/resource tradeoffs;
- strong turn-based battle presentation;
- authored mysteries and altered town states;
- a PSX-like visual and musical identity.

Do not make **procedural generation**, **creature collector**, **permadeath**, or
**sacrifice** carry the entire pitch merely because they are searchable system
terms. Use them when truthful, but sell attachment, danger, strange beauty and
consequence first.

The Metro stratum is a high-value surprise and should not appear in the default
first trailer/store screenshot set merely because it is visually distinctive.

The project may use fake manuals, Summoner notes, magazine-like copy, awkward
instruction screens and other imagined lost-game artifacts. These should direct
attention back toward the actual playable game rather than substitute lore posts
for footage.

## Commercial shape beyond one game

Second Gate is now being planned as the **first released entry in a broader Gate
corpus**, not as one title that must absorb every future idea and every unit of
Thestra investment.

See [`../commercial/gates-franchise-strategy.md`](../commercial/gates-franchise-strategy.md).

The preferred model is a dense paid Second Gate followed by future compact Gate
titles that reuse Thestra production leverage while developing their own
mechanical and narrative obsessions. Recurring characters, superbosses, places,
motifs and impossible guest encounters may connect the corpus without requiring
one exhaustively reconciled continuity.

## Generated development content

LLM-generated Projects, scenes, microgames, campaigns from historical tooling,
and other agentic stress tests are development/authoring evidence. They are not
player-facing Second Gate content merely because Thestra can generate them.

The commercial release is one polished authored Second Gate Project. Future Gate
games are separate authored products unless a specific release decision says
otherwise.
