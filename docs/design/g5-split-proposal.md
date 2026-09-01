# Splitting G5 into an invariant gate and an asset gate

Status: **proposal.** Nothing implemented.

---

## 1. The problem

G5 photographs frames that are a function of three independent things:

```
frame = engine/layout code  ×  renderer  ×  authored assets
```

A red tells you one of those three moved. It does not tell you which, so every
red costs a human triage pass. That cost is not theoretical: changing the title
art on 31.08.2026 turned eight frames red in both the classic and the wide sets,
and none of those eight were about the title art. They are `00-initial`,
`after-down`, `after-return`, `after-escape` — they photograph **menu
navigation state**, over whatever art happens to be behind it.

So an intentional asset change destroyed the signal from eight frames of
menu-transition coverage, and the only way to restore it was to recapture all
eight and hope nothing else had moved inside them.

## 2. The correction that shapes the design

The tempting split is "G5a is systems, G5b is assets, a G5b red means somebody
changed a picture."

**That is wrong, and it is the thing to get right.** A renderer change moves
asset frames too. G5b is not asset-only and never can be: it is still rendered.

```
G5a  (synthetic skin)  sensitive to:  engine/layout  ×  renderer
G5b  (real assets)     sensitive to:  engine/layout  ×  renderer  ×  assets
```

G5b's population is a superset. Read on its own, a G5b red is **uninterpretable**.

## 3. What the split actually buys: an interpreter

The two gates are not independent checks. **G5a is the discriminator that tells
you how to read G5b.**

| G5a | G5b | What moved | Action |
|---|---|---|---|
| green | green | nothing | — |
| green | **red** | **assets only** | acknowledge, recapture G5b |
| **red** | **red** | engine or renderer | fix it; G5b is collateral, do not triage it separately |
| **red** | green | engine or renderer, in a path the real-asset frames do not exercise | investigate — this is a **G5b coverage signal**, not good news |

Two things follow, and they are the real deliverables:

**G5b must report `INDETERMINATE`, not `FAIL`, when G5a is red.** Reporting it as
a failure invites someone to triage frames whose cause is already known and
already reported one gate over.

**Recapturing G5b must be BLOCKED while G5a is red.** This is the strongest
argument for the split and it is a genuine safety property the current gate
cannot offer. Today, a renderer regression and an intentional asset change
landing in the same window are indistinguishable, and the owner-signed recapture
would **bake the regression into the goldens permanently**. After the split that
is structurally impossible: you cannot sign off asset frames until the invariant
frames are green.

## 4. How G5a becomes asset-independent

Not by curating which frames "count as systems" — that judgement rots the first
time someone adds a frame, and it is the same judgement that put eight menu
frames behind a logo.

**Render G5a against a synthetic asset set.** A test-pattern skin: flat
placeholder plates, a checkerboard where art goes, a known glyph atlas, fixed
palette. Then a title change *cannot* move a G5a frame, because G5a never
renders the title art. The separation is structural rather than curatorial.

It stays fully sensitive to the renderer, which is the point — G5a must catch
renderer regressions, and it does, because a checkerboard is still rendered.

### Feasibility

The runnable tree is already materialised through **one** boundary —
`stageRuntimeGame`, via `tools/golden/gate-stage.ps1` and
`tools/ci/stage-project-gates.js`. A synthetic skin is a **staging variant**, not
a change threaded through the harness. That single choke point is what makes
this affordable.

## 5. The title frames, worked

| Today | After |
|---|---|
| 8 classic + 8 wide frames, real logo | 8 classic + 8 wide **G5a** frames, placeholder logo — menu transitions, never move when art changes |
| — | 1–2 **G5b** frames, real logo — the art itself |

The 31.08 logo change would have recaptured **two** frames instead of sixteen,
and menu-transition coverage would have stayed green the entire time.

## 6. What this does not fix

- **A real asset that breaks the layout** — wrong size, wrong aspect — becomes
  invisible to G5a by construction, because G5a never sees the real asset. That
  failure has to be caught by G5b.
- Which is why **G5b is not the low-status gate.** A gate treated as
  "less important" goes permanently amber, stops being read, and trains people
  to promote goldens without looking — the exact habit the owner-signed rule
  exists to prevent. G5b is not lower priority; it has different *semantics*.
  Its reds are **acknowledged**, not fixed.

## 7. Cost

- A second render pass. Mitigate by running G5b only when asset paths change,
  and G5a on every commit.
- A synthetic asset set to author and maintain.
- Two golden trees per surface — G5 already carries classic and wide, so this is
  four, and the tree layout should be reviewed before it becomes six.

## 8. Open questions

1. **Does the town belong in G5 at all?** Rewiring six exteriors, moving three
   interiors and adding a whole new screen changed **zero** golden frames. G5
   does not photograph St. Maria. That is a coverage gap independent of this
   split, and it should probably be fixed as G5b frames.
2. **Naming.** `G5a`/`G5b` reads as a hierarchy, which §6 argues against. Names
   that describe the population — invariant frames and asset frames — may serve
   better.
3. **How synthetic is synthetic?** A checkerboard everywhere maximises
   independence but makes a failing frame hard to read by eye. A muted flat
   palette may triage better at a small cost in independence.
4. **Which gate is required?** G5a is the obvious required check. Whether G5b
   blocks a merge, or reports and requires acknowledgement, is a policy call.
