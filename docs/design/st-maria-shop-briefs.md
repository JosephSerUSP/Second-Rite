# St. Maria shop briefs — Alicia's Padaria and Laura's smith

Design context for the two authored interiors, and the context file the
adversarial review harness is fed:

```bash
python tools/design-critique/critique_renders.py \
    --image "..." --context docs/design/st-maria-shop-briefs.md --out out/....json
```

The camera, the shell vocabulary, the axes and the non-negotiables are in
[`st-maria-interior-authoring.md`](st-maria-interior-authoring.md). **This file
adds only what makes these two places themselves**, and every fact below is
quoted or derived from authored game text — `data/commonEvents.json`,
`data/shops.json` and `projects/hichaukitoden-game/docs/walkthrough/`. Nothing
here is invented atmosphere.

The two rooms are also a matched pair: they are the town's two shops, the
player visits them back to back on the opening loop, and the women who run them
are in love with each other and no good at saying so. **If the two rooms read as
one room redressed, both have failed** — that is the specific failure the review
harness exists to catch.

---

## 1. Alicia's Padaria

> "I'm Alicia. Please drink water before you descend. People return looking
> like they forgot they have bodies."

> "I sell things that keep you alive! It makes me happy. Watching people leave
> with full bags... it means they might come back."

### What the place does

Three trades under one roof, and the room has to show all three:

1. **A bakery.** The wood-fired oven (*forno a lenha*) is the room's reason to
   exist and its heat source.
2. **The village's general staples.** Townsfolk buy flour, oil, salt and
   preserved goods here. This is the everyday half.
3. **Basic supplies for summoners.** Shop 1, *Basic Consumables* — recovery
   food, water, expedition provisions. She stocks it because people come back
   from the Labyrinth hollow.

### Facts that must be visible

| Authored fact | What it puts in the room |
|---|---|
| "Alicia is scraping wax from a tray." | She is also the town's **candle and lantern maker** — the Vigil's lanterns come from here. Wax trays, dipping frames, and a *reason* the oven's heat is used twice. |
| "One small lantern, hidden behind the counter, bears no human name." | The counter has a **behind** — a private side the player never gets to, with something in it. |
| "Alicia ties bread, cheese and a bruised pear into a cloth." | Cloth, string, and things wrapped for carrying. Not everything is on a shelf. |
| "I saved you a honey roll." | The stock is personal. Somebody's portion is set aside. |
| "Watching people leave with full bags" | Bags. Sacks. Volume of goods, not a token display. |
| "I like listening to the rain." | Colonial shutters and a window she stands near. |

### The identity to hit

**Warm, generous, over-stocked, and slightly too much for one person to run.**
Alicia's failure mode in the render is a tidy museum of three props. Her room
should look like a business that is *coping*: goods stacked because there is
nowhere else, the counter doing four jobs at once, the sweet smell implied by
how close the bread is to the customer.

Colour: warm — terracotta, bread crust, straw, honey. Whitewash carries the
light. The azulejo dado is the one cool note and it should stay a note.

### The failure to avoid

A rustic-fantasy generic bakery: three loaves on a plank and an oven mouth.
Alicia's is a **shop first**: the customer-facing threshold — where the money
is taken and the bundle handed over — is the centre of the plan.

---

## 2. Laura's smith

> "Fire purifies. Metal obeys. People... people lie. Steel never lies to you.
> It just is. That's why I like it."

> "New Summoner? Don't buy a heroic weapon. Buy something that still works
> while you're running home."

### What the place does

Shop 2, *Basic Weapons*, and the town's only metalworker. She sells opening
weapons and armour, buys salvage, and takes commissions.

### Facts that must be visible

| Authored fact | What it puts in the room |
|---|---|
| "She is hammering old lantern frames flat for reuse." | **Salvage is the business.** Scrap iron, flattened frames, a stack of stock that was something else first. |
| "Bring me anything the Labyrinth failed to digest." | A buying side: things brought up from below, unsorted, not yet worth anything. |
| The gold signet; "The gold is pure... untouched." | **Fine work as well as heavy work** — a small bench with small tools, distinct from the anvil. |
| `flag:shattered_blade_reforged` | Work in progress that is somebody's specific commission. |
| "Don't buy a heroic weapon." | The rack is workmanlike: short, plain, serviceable. Nothing ornamental. |
| "Back again? Blade dull already? Or are you just looking for warmth?" | The room is **the warmest place in St. Maria** and people come in for that. There is somewhere to stand and be warm. |
| "She smells like vanilla and iron." (Alicia, about Laura) | The lunch cloth arrives here, and goes back folded into a perfect square. |

### The identity to hit

**Hot, dark, loud and controlled.** Laura's room is Alicia's inverted: where the
Padaria is bright, soft and over-full, the forge is dark, hard and *ordered* —
tools on a rail in sequence, stock stacked square. The disorder is only in the
salvage heap, which is material she has not decided about yet.

Light: the fire is the key and almost everything else is silhouette. This is the
one interior in St. Maria where a dark frame is correct — but the black backdrop
discipline still binds, and every shadow still needs its source in the room.

Colour: iron grey, forge scale, charcoal, ember orange. Whitewash exists but is
smoke-stained. **The azulejo dado is a domestic thing and should be scarce or
absent here** — that contrast alone does a lot of the work of telling the two
rooms apart.

### The failure to avoid

A fantasy blacksmith: anvil centre, glowing forge behind, swords fanned on the
wall. Laura's is a **working shop with a customer counter she resents**. The
distinction between the fine bench and the heavy anvil is what makes it hers.

---

## 3. What the pair has to prove

1. **Two different rooms, not one redressed.** Different plans, different light
   directions, different colour temperature, different density.
2. **Trade legible at 256×240 without a caption.** A player who walks in should
   know what is sold before anyone speaks.
3. **Every hard shadow motivated** by the oven, the forge, a window or a lamp
   that is in the room.
4. **The composition lives above native Y=144.** What falls under the menu is
   floor, and nothing else.
