
> **Intent, not status.** This document describes what we mean to build and why.
> For what is actually implemented right now, read the generated
> [`docs/ENGINE-STATE.md`](../ENGINE-STATE.md) (gated by G4); for how the engine
> works, `docs/SPEC.md`. Where this document and those disagree, they win.
The Summoner is no longer a battle participant. They have no HP, no command phase, and no turn — they don't fight. What remains is their name, their MP pool, and their equipment. Equipment no longer buffs personal combat stats (there's no combat to buff); instead it shapes the MP economy itself — max MP, summon cost discounts, drain reduction, MP regen.

MP is intended to remain the Summoner's central resource rather than only a spell-cost meter, but its spend model is still under active design in #372 and #373. The current prototype direction is to avoid charging party MPD merely for ordinary traversal, charge manifestation/activation around battle entry, and make Veil-style encounter avoidance a deliberate traversal sink; prolonged-battle Strain may remain as separate anti-stall pressure. Exact activation and Veil costs, starting Max MP, progression, restoration pacing, and zero-MP consequences are not settled by this document.

The party is 4 active slots plus an 8-creature reserve. Reserve creatures are fully dormant — no MP drain, no actions, can't be targeted — and swapping between active and reserve is a free action from the field menu. Summon and Sacrifice both live in the field menu only; neither can be done mid-battle.

Summoning mints a fresh instance of a species — normally level 1, though paying extra MP lets you summon in at a higher level via a formula. Every species in the game is potentially summonable from the start, but gated behind an unlock flag that's off by default (except a handful of starting species). Unlocks come from diverse sources: defeating a species in the field, striking a contract, negotiation, an NPC offering one directly, and more — deliberately varied rather than one universal gate. Low-tier creatures tend to be cheap and easy to unlock and summon; stronger ones carry steeper MP costs and more elaborate unlock conditions.

Creatures are meant to be expendable, and that's what makes losing one hurt: raising a fragile, cheap Pixie into something powerful is a real time investment. Lose it to Permadeath or Sacrifice and you're starting that creature's growth over from a fresh level-1 instance.

Sacrifice is permanent. In exchange, it returns MP (scaled by the sacrificed creature's level) and can yield items — gated by the creature's state at the time (HP%, level, conditions) and by its species/discipline. Rewards scale with investment: a raised creature is worth more to sacrifice than a fresh one, both in MP and in what it can drop.

Promotion (Pixie → High Pixie → Titania, using the `evolutions` data already present in actors.json) is a ritual triggered at the creature's level threshold. Cost is flexible by design: sometimes it's free, sometimes it costs MP, and sometimes — often — it requires promotion key items. Those key items come from diverse sources, sacrifice being one of them: some creatures yield poor sacrifice rewards but excel at Item Creation, others are mediocre at both but strong in battle, some level easily but stay weak, some are slow to raise but hit hard once they do. The three creature-facing systems — battle performance, Item Creation aptitude, and sacrifice value — are meant to pull in different directions per species, so no single creature is strictly best and a diverse roster matters.

In battle, with the summoner gone from the command loop, Item joins each creature's own command list alongside Attack/Skill/Defend/Flee — using an item spends that creature's turn.
