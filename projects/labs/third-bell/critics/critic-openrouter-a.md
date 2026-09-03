# Critic: openrouter-a

- requested model: `nvidia/nemotron-3-ultra-550b-a55b:free`
- model reported by provider: `nvidia/nemotron-3-ultra-550b-a55b:free`

---

**1. Central Design Thesis**

The campaign's thesis is: *Second Gate's expedition horizon (MP as fuel, MPD as creature upkeep) becomes a literal ledger—names are currency, contracts are debt, and the Labyrinth keeps the books.* The Third Bell doesn't just extend the dungeon; it recontextualizes the Summoner's profession as clerical work for an entity that has been ringing a bell for eleven years with no clapper and no name. Every authored room (Rusted Choir, Weighing Room, Half-Contract) is a transaction interface where the player pays MP, gold, a creature, or their own name—and the ending forces them to choose which debt they'll settle. The compression from three pre-Vigil incursions to two is deliberate pressure: you arrive at Act II "roughly one incursion under-levelled versus canon pacing" (VALIDATION.md), so the expedition horizon bites harder.

**2. Strongest Three Moments/Ideas**

**A. The Weighing Room's "weigh your name" option** (maps/5.json, `weigh_name` branch). You place your *name* on a merchant's scale opposite an invisible counterweight. It "weighs about as much as a coat." The Vault pays you an Ether Seed, a second Bellroot Leaf *with your name on it in a hand nearly yours*, and full MP refill—but charges 10 MP and flags `weighed_name`. The ending reflection reads: "The Vault still has your name on its counterweight. You got a seed and a leaf for it. Nobody has mispronounced you yet." This is Second Gate's fiction (summoners sign contracts, names have weight) made literal machinery.

**B. The Rusted Choir as a greed ladder priced in the expedition horizon** (maps/4.json). Five bells, each strike costs more and pays better: Bell 1 = 60 XP party-wide + "something in the pit rolls over"; Bell 2 = 180 gold + 8+floor*2 HP damage to all allies; Bell 3 = Ether Seed + **25 MP deducted from your walk home** + forced battle. The fee is taken *out of MP*, not gold. The flags (`choir_struck_one/two/three/declined`) feed distinct ending reflections: "You still have the small change from the Rusted Choir. St. Maria mint. It spends." / "The clean bell... knew your name before you gave it away."

**C. The Half-Contract's physicality and the blue chalk line** (maps/6.json). The contract is "torn straight down the fold. The Summoner's half is gone. The creature's half has been signed four times. The fourth one is still wet." Taking it extinguishes the blue chalk line "all the way back to the entry hall, floor by floor, like a lamp being turned down." If you have Agnes's Bellroot Leaf, it updates: "FIVE DOWN. ONE TO GO." The mandatory return beat (CE 45) makes you carry this paper up the stairs: "The Half-Contract has dried on the walk up... Someone has been in the room. The bed is made the way you do not make it... Something has been added: a second bowl, smaller, dry, and never used." The town *reacts* to you bringing the contract up.

**3. Weakest Three Moments/Ideas**

**A. The Red Dragon on Floor 3 is mentioned in the README's beat table ("The Red Dragon holds the descent") but does not exist in the authored source.** No troop, no map event, no encounter in maps/4.json. The validation evidence confirms: "Neither has the Red Dragon at the level this compressed ramp will deliver the player at... unmeasured." It's a beat table ghost.

**B. The Eternal Warden's relight mechanic spawns `warden_second_bell` (a single level-9 Wisp) when `enemies.aliveCount <= 1`** (troops.json, `warden_relight` event). The Warden is Hyperion 13 + two Wisps 9. By the time only one enemy remains, the player has likely killed two of three. Spawning *one* level-9 Wisp as "the second bell relit" is trivial compared to the opening trio. The fight is "authored to run long enough to reach Battle Strain" but the reinforcement is a wet firecracker.

**C. The Garden Without Wind's payload is entirely text and flag-setting** (maps/7.json, modified event). It reads your Bellroot Leaf back to you ("THE THIRD BELL RINGS FOR WHOEVER IS NAMED. NOBODY HAS BEEN NAMED FOR ELEVEN YEARS"), sets `garden_read_the_leaf`, and... that's it. No resource exchange, no choice, no mechanical consequence. For the penultimate room before the Warden, it's a lore terminal. The validation notes "Long TEXT bodies... may wrap badly"—this is the longest uninterrupted text dump in the campaign.

**4. Where Pacing Most Likely Collapses**

**Floors 3–5 procedural spawn placement of the three authored rooms.** All three (Rusted Choir, Weighing Room, Half-Contract) use `spawn: "Random"` wall events (maps/4.json, 5.json, 6.json). The validation explicitly states: "They are guaranteed a legal position, not a *findable* one, and a player could plausibly cross a floor without meeting one." The minimap colors them distinctly, but if a player misses the Half-Contract on Floor 5, they cannot get the Warden's Clapper (Floor 6 checks `hasItem:209` for the cold-in-pack reaction) and the ending is gated behind the Clapper. The spine audit only checks that the *stages exist*, not that they're reachable in a single run. A player who speedruns stairs → stairs → stairs hits Floor 6 with no Clapper, no Half-Contract, no Weighing Room resolution, no Choir interaction—and the Third Bell event says: "You are missing the piece. You had it. Go and find where you put it." That's a softlock masked as a hint.

**5. What the Owner Will Most Likely Name as Their Favourite**

The **ending choice structure and its epilogue specificity** (CE 44). Three mutually exclusive options (name yourself / name your oldest creature / cut the rope), each with distinct mechanical resolutions (flag + gold + creature history recording / 4200 gold + Laura refuses commission / pure narrative), distinct credit slides, and—crucially—the epilogue town registers *which ending you took*. Alicia, Laura, and the gate guard have unique lines per ending flag (`ending_named_self`, `ending_named_creature`, `ending_cut_rope`). The gate guard's "Thank you. Nobody else is going to say it" (cut rope) vs "It is written here that you did" (named self) vs "I am not going to argue with the book" (named creature) makes the choice feel like it rewrote the town. The reflections array reads back *every optional room you visited this run*. That density of reactivity is the campaign's signature.

**6. What the Owner Will Most Likely Complain About**

**The Eternal Warden fight is either a pushover or a party wipe, and Battle Strain math is untested.** The validation states twice: "The Eternal Warden... has never been fought by a human. If it is absurd in either direction, that is the single most useful thing you can tell me." The troop is Hyperion 13 + two Wisps 9 with a one-time relight of one Wisp. The Warden's `warden_last_phase` at 35% HP deals 10% max HP piercing damage to all allies and shakes the screen. But the player arrives "roughly one incursion under-levelled versus canon pacing" (VALIDATION.md). If the party's MP is drained from the Choir's 25 MP fee + two floors of MPD, Battle Strain (which "punish[es] a party that arrived with no MP left") may activate immediately. Conversely, if the player bought Town Portal (unlocked after first return) and Bell Salt, they can retreat freely. The fight is the *only* mandatory combat gate to the ending, and its tuning is a black box.

**7. Generic RPG Content vs. Specifically Second Gate**

| Generic RPG Content | Specifically Second Gate |
|---|---|
| "Five bells hang over a dry pit on a rail... each bell pays better and costs more" (Rusted Choir structure) | **The fee is 25 MP taken from "the summoning"—your walk home currency. The coins are "St. Maria mint. It spends."** |
| "A merchant's balance scale... weigh your money/creature/name" (Weighing Room) | **MPD logic: "NOT YOURS TO WEIGH. YOU ARE HOLDING IT FOR SOMEONE." The creature *refuses* to be weighed because the contract binds it to another summoner.** |
| "Final boss holds a rope, drops a key item, triggers ending choice" (Eternal Warden) | **The clapper "fits. Of course it fits." A name goes in with the clapper. "Whoever is named is what the bell means." The bell has rung for 11 years *with nothing inside it*.** |
| "Town NPCs react to ending" (epilogue) | **Agnes rings two bells at the next Vigil; the third answers *in your voice* and the village says RETURNED. The gate guard has a writ book that *disagrees with reality* after the creature ending.** |
| "Paper leaf cut from ledger" (Bellroot Leaf) | **It starts blank. "When it stops being blank, you will know how far down you are." It updates to "FIVE DOWN. ONE TO GO." In the Garden, it hangs at face height and reads the terms aloud.** |

The Second Gate specificity is: **MP as expedition horizon, MPD as creature upkeep, contracts as physical objects with two halves, the Vigil as a bureaucratic ritual, and St. Maria as a town that processes loss administratively.**

**8. ONE Thing Worth Stealing Into Canon**

**The Weighing Room's "weigh your name" mechanic and its counterweight persistence.** The idea that a summoner's name has measurable weight ("about as much as a coat"), that the Vault keeps it on the counterweight after the transaction, and that the ending reflection reads "The Vault still has your name on its counterweight. You got a seed and a leaf for it. Nobody has mispronounced you yet"—this turns the Summoner's ledger fiction into a physical object the world retains. It explains why names matter in this setting: they have mass. The Labyrinth *literally* weighs them. This should exist in the base game as a rare room type.

**9. ONE Thing to Absolutely Leave Experimental**

**The ending's dead-end into a changed St. Maria map instead of returning to title screen.** The validation records this as a Thestra gap: "A campaign cannot end. `QUIT_GAME` and `SCENE_EVENT` are scene-context only... Every authored ending in this engine must currently dead-end into a map." The campaign leans into it: after credits, `LOAD_MAP 1` drops you into an epilogue town with altered fog/ambient (`ambientR: 0.30, ambientG: 0.28, ambientB: 0.22`) and the instruction: "Close the game from the menu when you are finished." This is not a workaround—it's a *design decision* to make the epilogue playable. Canon Second Gate should not adopt this until the engine supports proper campaign termination; it would confuse players expecting a clean exit. But as an experimental statement—"the town keeps going without you; that is rather the point of it"—it works precisely because it's broken.
