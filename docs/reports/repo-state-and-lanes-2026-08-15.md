# Repository state report and lane plan — 2026-08-15

Status: **dated point-in-time assessment and planning proposal**. Not a status
authority. `docs/ENGINE-STATE.md` owns what exists; `docs/SPEC.md` owns reviewed
behavior; GitHub Issues own open commitments.

Audited revision: `main` @ `185e02a4` (fast-forwarded from `d9ed9d4a` during this
session — the primary checkout was 36 commits behind origin).

Comparison baseline: the last comparable assessment recorded in my working
memory, **2026-08-08** (`golden-recapture-2026-08-08`, `github-housekeeping-2026-08-08`).

---

## 1. Headline: the project changed shape, not just size

The one-week delta is not incremental. On 08.08 this was *Second Rite: a LÖVE
dungeon RPG with a JS editor attached*. On 08.15 it is **a three-product
monorepo**:

| Product | What it is | Where it lives |
|---|---|---|
| **Thestra runtime** | the engine that plays a Project | `engine/`, `presentation/`, `main.lua` |
| **Thestra Studio** | the authoring application (Electron + Node + JS) | `main.js`, `tools/editor/`, `tools/export/` |
| **Second Gate** | *one* authored Project that happens to be the flagship game | `data/`, `assets/`, `docs/game design/` |

The evidence for that reframing is structural, not rhetorical:

- `projects/labs/` and `tools/labs/` now exist — Projects that are **not**
  Second Gate, produced to prove the runtime is Project-neutral.
- `rtp/revisions/` exists — a frozen, versioned shared-resource layer (the
  RPG-Maker "RTP" analogue from #237).
- New Project lifecycle: create / open / relaunch, sparse creation into a chosen
  empty folder, Project-switch guards, CLI Test Play (#479, #485, #500, #503).
- Five new CI workflows exist purely to police that boundary:
  `sparse-project.yml`, `project-lifecycle.yml`, `studio-host.yml`,
  `lab-project-validation.yml`, `encounter-lab.yml`.

**`AGENTS.md` has not caught up with this.** It still opens "A LÖVE2D (Lua)
first-person dungeon RPG … plus a vanilla-JS+Node editor under `tools/editor`",
and its `Where things live` block lists none of `projects/`, `rtp/`,
`tools/labs/`, `tools/encounter-lab/`, `tools/design-studies/`. This is the
single highest-leverage doc defect in the repo right now: it is the file every
fresh agent reads first, and it describes the previous architecture.

---

## 2. Quantitative delta since 2026-08-08

| Measure | Value |
|---|---|
| Commits to `origin/main` | **507** in 7 days (peak 133 on 08-14) |
| Diff vs. ~500 commits back | 3,232 files, +412k / −27k lines |
| Issues opened | 147 |
| Issues closed | 112 |
| Open issues now | 47 |
| Open PRs | 4 (`#516`, `#512`, `#507` draft, `#257` DO-NOT-MERGE) |
| CI workflows | 10 (was effectively 1 — "Phase A" verify) |

Churn concentration (files touched, since 08-08):

```
801  tools/asset-gen      art generation still the single busiest surface
296  tools/golden         gate expansion (Thestra/Studio coverage)
292  tools/editor         Studio: Map workspace, Inspector, lighting, gizmos
203  assets/keyArt        commercial/store material
156  assets/models        Blender item/prop models
 74  data/units           content authoring
 48  .github/workflows    the boundary-policing CI build-out
 42  tools/design-studies
 40  projects/labs
```

Read that top-to-bottom and the week's real theme is legible: **art production
and Studio authoring UX, verified by a rapidly widening gate/CI surface.**

## 3. Gate and health status (verified this session, not asserted)

| Gate | Result |
|---|---|
| G1 `lovec . validate` | **VALIDATE OK** — 85 SCRIPT usages, 0 deprecated |
| G2 battle logs | **green** (affinity / default / growth all match) |
| G4 engine state doc | **green** ("Engine state doc matches") |
| G3 / G5 / G6 | not run this session (G5/G6 are slow, owner-bound, GPU/Chrome-fingerprinted) |
| CI on recent branches | `studio host`, `shim provenance`, `sparse project`, `project lifecycle`, `encounter lab`, `lab project validation` all **success**; `verify` still running on the two live branches |

Notable: 85 SCRIPT usages is worth watching. The validator prints it precisely so
growth stays visible, and I have no 08.08 number to compare against — **record it
now so the next report has a baseline.**

## 4. Verification surface: the genuinely good news

Since 08.08 the gate story went from "six gates the owner runs locally, plus a
thin Windows CI" to a layered system:

- **Relative visual A/B** (`relative-golden-ab.yml`) with a mandatory base-A →
  base-B repeat control — this is the correct answer to the long-running
  problem that G5/G6 red could mean "GPU drift" or "real regression" and nobody
  could tell without the owner.
- **Lab Project validation matrix** (#513/#514) — isolates evidence per matrix
  entry, i.e. it proves the runtime works on Projects that aren't Second Gate.
- **Fail-closed runtime boot in CI** (`a3aecfaa qa: make CI runtime boot crashes
  fail closed`) — this closes exactly the class of hole recorded in my memory as
  `cli-mode-token-typos-boot-the-game`: a run that looked like a pass because
  nothing printed FAIL.
- **Walkthrough + visual evidence required for authored games** (`0218bd1d`).

This is the repo's strongest asset and it improved the most this week.

## 5. Where the debt actually is

### 5.1 Worktree and branch sprawl — worse than 08.08

`git worktree list` shows **10 worktrees**; `git branch -vv` shows 17 local
branches, of which **11 track a remote that is `gone`**. Five worktrees hold
stale codex branches (`161-prepared-map-candidate`, `254-g6-picker-coverage`,
`fix-253`, `pr342`, `prebake-profile`), two are locked codex detached HEADs, and
one is a temp G6 baseline in `AppData\Local\Temp`.

The 08.08 housekeeping note says origin was pruned 17→12. Origin has since
regrown. Each stale worktree is a live trap for the two gotchas already in my
memory (`bash-cd-worktree-mismatch-gotcha`, `preview-worktree-mismatch-gotcha`),
and worktree removal is classifier-blocked when batched — so this has to be a
deliberate, one-at-a-time cleanup pass, not a background chore.

### 5.2 Documentation authority drift — diagnosed, not fixed

`doc-status-drift-2026-08-13.md` is a careful audit that identifies eight
documents still asserting implementation status inside design docs (`Status:
implemented`, `Done`/`FIXED`/`Closed` ledgers). It explicitly says it "does not
edit any of the documents above" and is "intended to be the evidence source for
one later bounded documentation-authority cleanup issue/PR". **That PR does not
appear to exist.** PR #512 is titled "Design-document status drift report" — i.e.
another report, not the cleanup.

This is the exact failure mode `AGENTS.md` warns about — four documents once
asserted false facts and cost a full wasted planning pass. The audit has been
done twice (08-12 and 08-13) and executed zero times.

### 5.3 Monorepo boundaries — census done, move not done

`monorepo-ownership-census-2026-08-13.md` names a concrete mixed-ownership
defect: `data/authored_storage.lua`, `data/json.lua`, `data/loader.lua`, and
`data/authored_storage_manifest.json` are **Thestra runtime files living inside
the Second Gate Project's `data/` directory**, and the exporter has to special-
case them via `dataRuntimeFiles`. Also unresolved: root `conf.lua`,
`tools/campaign-gen/**` (declared stale pending #369), and `.census-bootstrap/**`
residue.

Issue #382 says "define boundaries **before** reorganizing". The boundaries are
now defined. The reorganization is the open commitment.

### 5.4 Issue backlog shape

47 open, and it is not sludge — but it *is* unstratified. Reading it, there are
at least six distinct programmes tangled together with no milestone separating
them (only one milestone exists, "LÖVE 12 migration", carrying #251 and #212).
Roughly:

- **Map lighting authoring** (#467 audit + #474/#475/#476) — 4 issues, one audit
  landed 08-14, clearly a coherent unit of work.
- **Authored state substrate** (#400, #407, #409, #410, #411, #472) — 6 issues,
  a real architectural programme with a defined sequence.
- **AI-playable Projects** (#366, #375, #381) — the membrane work.
- **Scene portability / boundaries** (#414, #417, #418, #386, #325, #237, #382).
- **Studio/Project UX** (#404, #402, #487, #486, #493, #515).
- **Second Gate content and combat design** (#308, #232, #234, #236, #281,
  #372, #373, #167, #202, #405).

Plus two things that are neither: **#354 licensing** (owner decision, blocking
anything commercial) and **#288 display-name rename**.

---

## 6. Proposed lanes and milestones

The organising question for the next phase is: *what is the shortest path to the
Release Plan's Stage 1 — the "opening sales proof"?* `docs/commercial/release-plan.md`
sets a hard target: **Steam Next Fest, 22 Feb – 1 Mar 2027**, with a 25–45 minute
public demo, and an explicit "hard no" to October 2026. That is ~6 months out.
Everything below is ordered against that date.

The reason the repo currently feels diffuse is that it is running platform work
(Thestra/Studio) and product work (Second Gate) at the same velocity with no
declared priority between them. **They need different lanes with different
success criteria.**

### Lane A — Product: Second Gate playable slice
*Success criterion: an uncoached tester completes St. Maria → gate → descent →
return and wants another incursion.*

This lane owns the release plan's Stage 0–2. It is the only lane with an external
deadline. The `opening-vertical-slice-gap-audit.md` already scores chapters 01–03
and is mostly `PLAYABLE_AND_VERIFIED` — the residue is presentation polish
(Ines blue line, Vigil ceremony), balance/testing (Cerberus first contract), and
two `DESIRED_MEMORY_ONLY` gaps (room-3 inspection flags, Saban absence reactions,
the latter genuinely blocked on durable identity/death history).

Issues: #405 (ward status presentation), #202 (Reserve golden), #167, #281, #372,
#373. Design-only issues (#232, #234, #236, #308) should be **explicitly deferred
out of this lane** — they are catalogue-expansion, not slice-completion.

### Lane B — Platform: Thestra Project neutrality
*Success criterion: a lab Project that shares no Second Gate ontology boots,
plays, and passes its own gates in CI.*

Largely already working (the lab matrix is green). What remains is the
reorganization: #382 monorepo move, the `data/` runtime-file extraction,
`conf.lua`'s seam, campaign-gen's disposition (#369), and #237's RTP layer.

This lane's discipline: **it must not regress Lane A.** #488→#490 (revert) →
#491/#492 (reland) this week is the cautionary example — a Studio change broke
and had to be hotfix-reverted, then relanded twice. Platform work touching
shared surfaces should land behind the relative A/B gate every time.

### Lane C — Authoring UX: Studio
*Success criterion: the owner can author a map's geometry and lighting without
waiting on a cold LÖVE recompile.*

#487 states this explicitly ("decouple gestures from cold LÖVE recompilation").
The lighting cluster (#467/#474/#475/#476) belongs here, as does the Map
Inspector (#493, landed) and layout UX (#404, #402).

This lane is genuinely productive right now and should keep its pace — but note
it is **instrumental**, not terminal. Studio exists to make Lane A faster. If a
Studio feature doesn't reduce the cost of finishing the slice or of building the
next Gate title, it can wait until after Next Fest.

### Lane D — Substrate: authored state
*Success criterion: variables, switches, self state and scene locals have one
defined home each, and #410's ambiguous `v` state is migrated.*

#400 → #407 → #409 → #410 → #411 → #472 is a real dependency chain and should be
executed in that order as one programme, not opportunistically. It is
prerequisite for Lane A's blocked "Saban absence" content (durable identity /
death history has nowhere to live today).

### Lane E — Hygiene (continuous, low-ceremony)
Worktree and branch cleanup, the doc-authority cleanup PR that two audits have
now earned, and the SCRIPT-count baseline. Small, but 5.1 and 5.2 both actively
cost agent time every session.

### Proposed milestones

| Milestone | Contents | Target |
|---|---|---|
| **M1 — Product lock** | #354 licensing decision, #288 naming, doc-authority cleanup, worktree/branch prune | end Aug 2026 |
| **M2 — State substrate** | #400/#407/#409/#410/#411/#472 in sequence | Sept 2026 |
| **M3 — Slice complete** | Lane A residue: presentation polish, balance pass, blocked content unblocked by M2 | Oct 2026 |
| **M4 — Boundary move** | #382 monorepo reorganization, `data/` extraction, #237 RTP | Nov 2026 (after M3 — do not reorganize while the slice is being finished) |
| **M5 — Demo build** | Stage 2 private test → Stage 3 Coming Soon page | Dec 2026 – Jan 2027 |
| **LÖVE 12 migration** *(existing)* | #251, #212 | opportunistic; needs a GPU host |

The sequencing claim worth arguing with: **M4 after M3.** The monorepo move is
architecturally correct and I would normally want it early, but it touches every
path in the repo, and Lane A has the only immovable deadline. Doing it before the
slice is finished risks a repeat of #488 at ten times the blast radius.

---

## 7. Three decisions I need from the owner

1. **#354 licensing.** It has been open since before 08.08, is tagged
   `question`, and gates anything commercial — including publishing key art. It
   is the oldest cheap unblock available.
2. **Lane priority.** Is Lane A (finish the game) genuinely ahead of Lanes B/C
   (build the platform)? The commit history currently says no — platform and
   Studio work dominate. If that is deliberate, the Next Fest target should move;
   if the target is firm, the balance should shift.
3. **M4 sequencing.** Confirm the monorepo reorganization waits until after the
   slice is demo-ready, or override with reasons.

---

## 8. Immediate next actions (no decision required)

- Update `AGENTS.md`: the opening paragraph and the `Where things live` block,
  to describe the three-product structure and the new directories.
- File the doc-authority cleanup issue that `doc-status-drift-2026-08-13.md`
  was written to justify, scoped exactly to its eight rows.
- Prune stale worktrees and `gone`-tracking local branches, one at a time.
- Record the G1 SCRIPT baseline (85) so drift becomes measurable.
