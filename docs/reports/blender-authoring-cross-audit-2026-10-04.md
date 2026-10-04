# Blender authoring: reconciliation of the two 2026-10-04 audits

## Foundation implementation follow-through

The first implementation slice is on `codex/blender-authoring-foundation-1341`,
stacked on the assessed head of PR #1352. The original shared town checkout
was preserved. The sections below remain the dated comparison; this addendum
records subsequent implementation evidence, not delivery status for the wider
roadmap.

The maintained Blender, surface and First Stratum paths now use a Python
adapter to Studio's existing `tools/semantic-roots.js` authority. Explicit
Project selectors, environment selection, missing/wrong roots, external
Projects and Project-relative input paths have executable checks. Tools and
contracts stay installation-owned. The surface adapter passes its Project
explicitly to asset-gen, including absolute depth-guide paths. Direct
asset-gen's historical no-Project mode and older town/data tools still need
the broader #1341 cleanup; #1341 is not claimed fully resolved.

`tools/blender/README.md` supplies intent-to-entry-point-to-gate routing. Every
lane brief is at most two links from `AGENTS.md`. Migration narratives moved
out of the live core/item contracts into one historical report. Four retired
item builders and the obsolete census-builder test were preserved in
`docs/archive/`, outside live routes and test discovery. Retargeting those
builders would allow old recipes to overwrite Blender-owned products. The
remaining census bootstrap needs a separate decision under #1341/#1342.

Capture installs its own repository-owned probe into a disposable canonical
stage, reports engine traces through a stage-only error handler, and restores
borrowed files. A successful native run produced twelve frames: map 28 at
positions 1, 3 and 6 on classic, 4:3, wide and device surfaces. A deliberately
broken caller probe exited in 14 seconds and both the main file and caller
probe restored byte-for-byte. Mocked timeout, missing payload and ordinary
process failure controls also preserve original main/configuration/probe
bytes. These frames are runtime evidence, not golden or owner-play acceptance.

| Verification on the foundation worktree | Observed result |
|---|---|
| Blender host discovery without an executable | 360 tests, OK, 22 explicit integration skips |
| Same discovery with pinned Windows Blender 5.2.2 and required integrations | 468 tests, OK, no skips; 493 seconds |
| Asset-production suite | 55 tests, OK |
| Asset-gen suite | 37 tests, OK |
| Node root/Studio/courtyard suites | 39 pass, one existing skip |
| Asset-language root tests, contract and regression | 5 root tests and both checks pass |
| Environment source records | Both registered Projects pass |
| Canonical staged G1, G4 and unit | Pass; native Effekseer assertions unavailable in this fresh worktree |
| Real chest builder | Both declared states exported to scratch with build provenance |
| Read-only item source compilation to scratch | All 32 sources compile; 233 seconds; compiler enforces source hashes |

The exact-byte item check is **not green on this Windows host**. MTL finalization
was translating LF to CRLF; the writer now emits canonical LF and a byte-level
test enforces it. After that repair, `chrysalis_sigil.obj` still differs in one
normal (`-0.3608` versus `-0.3607`). The parent compiler produces exactly the
candidate's OBJ bytes, preserving source hash
`d0cefdc0bf31c21bb0dd4e4846570099a443f6a66883aee7b43cd05204ee51c1`.
[Issue #1355](https://github.com/JosephSerUSP/Second-Rite/issues/1355) records
that existing reproducibility gap. No source, OBJ/MTL reference, or golden was
rewritten to clear it. The parent's separate Linux bake-test failure remains
[issue #1354](https://github.com/JosephSerUSP/Second-Rite/issues/1354); a Windows
suite pass does not resolve it.

Five V2 metadata files changed only their `generatorSourceSha256` after the
path repair. A temporary regeneration proved every PNG byte unchanged before
those producer fingerprints were updated. CI now discovers the optional host
suite and gates the asset-production/corpus lane. The pinned Blender job runs
the same full discovery with required prerequisites, replacing its manually
maintained subset of integration tests.

These changes make existing capacity easier to reach and diagnose. They do
not yet prove improved success at a lower reasoning level. The next benefit
test should combine #1345's generated catalogue, a small set of relational
compositions and the bounded lower-effort pilot described below. Record
authoring time, repair rounds, contract failures and blind visual judgments;
require distinct scenes with correct scale and native framing rather than
counting syntactically valid outputs.

The [foundation evidence record](blender-authoring-cross-audit-2026-10-04/foundation-evidence.json)
retains the summaries and boundary proofs. All 122 tracked `.blend` files in
this worktree match their Git blob bytes after verification.

Reproduction logs, parent/candidate compiler proof, capture restoration proof,
scratch exports, surface-provenance proof and timing records are retained in
the worktree's `out/`. The PR checks provide the separate hosted verdict.

## Conclusion

The alternate audit strengthens the earlier assessment. Its most valuable additions are the broken item-production lane, explicit gaps in test discovery, item scaffold/finish proposals, and a set of resumable Issues. The earlier assessment contributes direct inspection of saved Blender sources, precise runtime package selection, native frames, bake/source-role concerns, and an empirical test for whether lower-effort authoring actually improves.

The combined recommendation is to make the maintained tools reliably reachable, then expose a small authoring interface over them. Repair Project resolution and capture preparation, generate context and a catalogue, add relational compositions, and prove the result on bounded tasks. Declarative data is a promising interface for new scaffolds; adopted Blender documents continue to own their art. Reducing intelligence requirements should remove routine inference while preserving artistic choices and visible failure.

I would use #1341–#1350 as the working issue set, with the refinements below, and retain #1339/#1340 and the existing camera/bake issues as explicit dependencies. The alternate plan should absorb the earlier audit's evidence and constraints rather than become a competing roadmap.

## Sources and snapshot boundaries

This comparison reads the [alternate assessment at PR #1352 head](https://github.com/JosephSerUSP/Second-Rite/blob/205f99fb26822e289342b69d8c68875aceb6c869/docs/reports/blender-authoring-assessment-2026-10-04.md), all ten Issues #1341–#1350, the [PR description](https://github.com/JosephSerUSP/Second-Rite/pull/1352), and the [earlier illustrated assessment](blender-expressive-authoring-assessment-2026-10-04.md).

The alternate head inspected is `205f99fb26822e289342b69d8c68875aceb6c869`. The local checkout during this comparison is `5d195b4b9234ae7c5a28405e98c0dc9c4947396c`, on another active branch, with untracked St. Maria studies. Their merge base is `a91321cc97d6f00975ef73fe845f11f6a42c6208`. I fetched the alternate ref and read its files without switching the shared checkout. Changes described as implemented in the alternate PR are branch changes, not verified integration into this checkout.

PR #1352 is broader than its initial report: it contains the corpus path repair, skill routing, Passage Office revision pruning, candidate checks, and the worked exterior example. Its opening method section still says Blender was not run, while its appended follow-up and PR description report later pinned-Blender tests. These describe different phases; the verification record should identify those phases directly. At the checked PR status snapshot, `item-source` and relative G6 were still running. Neither the PR body nor this comparison is a final CI verdict.

Fresh comparison evidence is retained in [cross-evidence.json](blender-authoring-cross-audit-2026-10-04/cross-evidence.json). Full branch text, issue bodies, reproduction logs and the temporary-module probe script are under `out/blender-cross-audit-2026-10-04/`. The earlier audit's 239 focused tests and 32 diagnostic native frames remain its dated evidence; they were not rerun or converted into PR #1352 acceptance here.

## Where the reports reinforce each other

| Finding | Alternate audit contributes | Earlier audit contributes | Combined decision |
| --- | --- | --- | --- |
| Strong core, weak discovery | Intent-to-lane routing; stale skill examples | 47 public builders but one library asset; scattered entry points | Generate a small task index and contextual catalogue from actual tools |
| Coordinate inference costs too much | Named anchors and field-specific spec validation | Map-owned camera/profile resolution; shared projection arithmetic | Named frames must consume the owning map contract |
| Reusable construction is underused | Furnishing catalogue, item templates, place spec | Connected-volume/opening vocabulary and narrative compositions | Catalogue parts, then expose arrangements and relationships above them |
| Feedback is fragmented | Project-path failures and aborted host-test discovery | Capture timeout, used-image dependency failure, native-scale evidence | One entry point should report separate checks and actionable failures |
| Noise hides the maintained route | Studies, surgery scripts, duplicate exporter, history-heavy docs | Role classification and bounded context rather than whole-scene dumps | Route by role first; retire files only after provenance and consumers are checked |
| Source authority matters | One-time scaffolding and read-only item compilation | Adopted environment inspection and source-role/bake boundaries | Generation stops at adoption; later edits target the actual document |

The architectural direction is shared. The difference is emphasis: the alternate audit specifies a data interface; the earlier audit specifies the context, ownership and review that make such an interface dependable.

## Inventory differences reconciled

| Apparent difference | Reconciliation |
| --- | --- |
| 49 furnishing functions versus 47 | AST inspection finds 49 top-level functions, including two private helpers, and 47 public builders. Catalogue completeness should target the public set. |
| 205 Python files versus 256 files under Blender tooling | The former counts Python files; the latter describes all files. Neither is a count of supported workflows. |
| 71 Python test/probe files versus 77 files in the test directory | Extensions and populations differ. Count actual discovered test cases separately from files and Blender probes. |
| 208 item OBJs versus 205 | There are 208 item OBJ files on disk, 207 item records referencing models, and 205 distinct referenced paths. Three files are outside those item references: two bottle-family alternatives and `placeholder_question.obj`. This is a reference census, not a deletion recommendation. |
| 173 legacy model paths without an editable source | All 32 source stems match referenced model paths; 205 minus 32 therefore yields 173 referenced paths without a matching per-item source stem. This confirms the alternate figure within this convention. |
| Approximately 20 shipped environment packages versus 19 manifests | The earlier census is precise: 19 manifests, 17 map bindings, 13 selecting layered plates and four selecting mesh presentation. Package retention and shipping presentation are different populations. |
| Twelve Passage Office candidates versus a single retained reference | Twelve describes the pre-pruning tree. PR #1352 removes r2–r12 and retains r13. Preserve both timestamps rather than treating the original inventory as current branch-tip content. |

One further distinction matters: the house grammar's expressiveness is demonstrated by its builders, tests, studies and live bridge, but the alternate audit identifies no shipped environment built from that grammar. The earlier report's capability description should not be read as proof of shipped adoption. The new exterior example imports `Exterior`, not the house grammar; it does not close that adoption gap.

## Findings that change the priority order

### The item-production failures are real and were underrepresented earlier

The local corpus gate fails trying to open repository-root `data/items.json`. The asset-set module runs four tests with three errors caused by the missing repository-root asset-set path. The model-census test fails importing the removed `mesh_recipe`. These reproduce the alternate audit's core F1 findings.

The earlier audit verified the maintained item compiler and related contracts, but did not exercise this broader asset-production test lane. Its focused green results therefore did not address these failures. #1341 belongs among the first investments, alongside #1340's capture prerequisite and failure reporting.

The PR's corpus repair correctly changes the default item data location and resolves each model against the selected item data's Project. It still introduces a fixed default game Project, rather than completing the shared Project resolver proposed in #1341. Treat it as a bounded repair. The alternate PR claims 19 corpus tests passed; this comparison read that repair but did not execute its full branch corpus gate.

For #1341, functional acceptance should be stronger than a grep returning zero hits. Test two temporary Projects with the same item identifiers but different assets, explicit Project selection, the documented environment override, missing required content, and output containment. Some tools operate on an installation, a Project, or an isolated fixture; their roots should have those explicit meanings. An alias named `ROOT` alone cannot establish whether a path is wrong.

#1344 should allow optional Blender-dependent tests to skip when Blender is absent while preserving strict required CI. An explicitly supplied invalid executable, a wrong pinned version or a failed Blender probe must remain a failure. Report executed and skipped coverage separately; a successful discovery run with skips does not verify the Blender behaviors.

### Saved-source dependencies and capture failures remain first-class work

The alternate plan does not supersede #1339's unresolved preview actor references in the adopted Praça source or #1340's missing staged capture probe. Its routing and preflight work should surface those checks. Otherwise a clearer menu merely routes a weaker agent into the same timeout or failed source inspection.

#1326 also remains a material semantic failure. Passing vendor hashes, source provenance, item corpus checks and an asset-language check does not imply that every used Blender material is semantically registered. Display these verdicts separately.

### Source grouping is an independent usability concern

The earlier inspection found 2,506 saved courtyard objects for a compact 6,137-triangle package. That is evidence of a successful source-to-runtime reduction and a large navigation surface. A part catalogue alone will not make a small edit easy in that scene. Meaningful roots, retained hinges and profiles, role isolation, and selection of the relevant composition remain high-benefit work.

The alternate read-only `describe` proposal fits this need, but should project the existing bridge inspection contract. `inspect_context`, scene summaries, object records and hierarchy data already exist. Adding a second independent scene interpreter would increase redundancy. Return a compact summary for the requested target, with deeper inspection available on demand.

## Proposals to keep, with sharper boundaries

### #1347: place specifications are valuable for scaffold creation

A relational spec over existing `Interior` and furnishing builders can replace positional inference with field-specific errors. `against: back`, `on: counter`, and a named opening are worthwhile operations. It should compile into the existing construction semantics, not define another geometry engine.

Two lifecycle transitions need explicit acceptance:

1. For a new scaffold, the spec owns the recipe and its generated structure. Remove its parallel Python recipe when equivalence is demonstrated.
2. For an adopted source, the `.blend` owns the art. The old spec becomes historical scaffold provenance unless a supported operation explicitly edits the current document. It cannot remain the live room editor while silently overwriting human changes.

Padaria is already adopted. A pilot may reconstruct its historical scaffold in scratch space and compare it to the former recipe output; it must not regenerate the adopted production file. A successful test should include a deliberate manual change in an adopted copy, then demonstrate that routine inspection/compilation preserves that change.

The alternate example also contains `exit: {at: ...}`. Define that as visual threshold placement, or make it consume an existing authored event anchor. It must not create gameplay destinations or passability from geometry. JSON makes a Studio form possible, but it does not automatically provide one: the schema, persistence boundary, Project routing and source lifecycle must be implemented deliberately through the shared form layer.

The pilot should expose several genuinely different arrangements using the same parts. Field filling that always produces the same shop silhouette does not meet the expressive objective.

### #1345: catalogue public builders, including context-dependent ones

The catalogue is one of the cheapest useful investments. The alternate acceptance needs a build-fixture contract, however. Eight public builders require keyword arguments with no default, including material inputs, an artwork image, wall coordinates and service-screen bounds. Even otherwise defaulted functions need a room, a name and sometimes a placement.

Generate signature metadata mechanically, and supply explicit preview fixtures where construction needs context. Those fixtures are catalogue examples, not new furnishing implementations. Give each entry a footprint, placement frame, materials, dependencies, editable handles, role and native-size preview. For a wall furnishing, show a wall context; for a service composition, show its public/working relationship. A contact sheet is useful for discovery but does not replace separate contextual views.

After the individual parts are discoverable, package a few higher-level arrangements: waiting alcove, service bay, hearth workspace, sleeping corner, window bay and sheltered threshold. These carry more expressive meaning per decision than an expanded list of isolated props.

### #1346: stage invalid construction without flattening artistic choices

The blanket claim that the character floor limit is only documented is too broad. `Interior.platform()` already refuses a sunken platform whose projected feet cross the limit. `Interior.foreground()` also enforces cumulative screen-coverage constraints. `finish()` does not yet provide the general staging pass proposed in the issue. Extend and share existing checks rather than introducing competing calculations.

Separate three kinds of result:

- Hard failures for malformed geometry relationships, missing required references, invalid field values, unsupported source roles, or violation of the owning map's resolved walk/camera contract.
- Scoped checks where semantic intent is known: a named walkable platform, an outward room exit, or a documented foreground member.
- Review observations for readability, focus, light motivation, visual permeability and intentional nesting.

An axis-aligned bounding-box intersection is a broad-phase overlap signal. It can report a prop near a pierced wall, books inside shelves, joinery engagement or furniture built from intersecting members. It is not by itself proof of invalid construction. Model support/containment relationships where needed and report uncertain cases; avoid requiring dozens of `allow_overlap` flags for ordinary furniture.

Likewise, a light's distance from an emissive object does not prove that its shadow is motivated. A `reason` string is an explanation, not geometric proof. Use source-owned light roles and maintain visual review for the part mechanics cannot decide. Fixed 144/240 scanlines belong to their scoped camera/UI contract, not every future map.

### #1348: templates and finish presets broaden item authorability

Lathe, plate and sweep templates are well aligned with editable Blender sources. Preserve the constructive handles and deterministic compile path; do not use the 173-path gap as authorization for mass replacement. One end-to-end item is the appropriate pilot.

The statement that missing UVs blocks all textures or projection is too broad. It blocks meaningful authored-UV texture use. The current shader explicitly supports sphere-mapped overlays from normals, which do not need authored model UVs. UV-bearing templates still improve the available range, but this distinction matters for selecting finishes and triaging legacy items.

Named finishes should expand through the existing material-pass validator and bounded two-pass runtime vocabulary. If both a preset and explicit pass JSON are supported, define one unambiguous composition rule or reject simultaneous use. Do not add two independently interpreted descriptions of a material's final passes. Unknown names, missing textures and unsupported combinations should fail with the material named.

Scaffold equivalence and silhouette checks do not establish artistic distinctness or a useful runtime finish. Include a native item view and explicit owner review when changing shipped art. Baseline changes retain their existing authority requirements.

### #1349/#1342: reduce discovery noise without inferring disposability

The alternate PR reports owner-approved removal of Passage Office r2–r12. That is a specific decision. It does not establish a general authorization to remove every unreferenced study, migration list, exporter copy or candidate alternative. Zero code references cannot establish absence of manual use or historical/provenance value.

Prefer the role manifest proposed in #1342 before reorganizing the tools. It can immediately hide one-off surgery and studies from ordinary routing while preserving reproducibility. A count such as 35 production entries is a target, not the outcome: reliable routing and fewer unsupported choices are the useful measures.

Candidate policy needs to identify serial revisions separately from distinct alternatives. A project may legitimately retain several source documents for different compositions. The two-file policy is suitable for a narrowly identified revision stream, but a blanket count over a whole town study would erase that distinction.

There is a concrete gate gap at the inspected PR head: candidate checking visits immediate folders and their immediate `.blend` files only. A temporary unregistered source under `candidates/study/variant/` returned no errors. The local `st_maria_layout` overlay has one immediate `.blend` and 23 recursively; the PR checker reports the missing immediate manifest but does not inspect the nested sources. This overlay contains concurrent untracked work, so it is not a claim that the PR's tracked tree fails CI. It shows a real scope mismatch with “every candidate `.blend` is recorded.” [#1353](https://github.com/JosephSerUSP/Second-Rite/issues/1353) records the reproduction and intended invariant.

Resolve the manifest scope and candidate identity before extending the count limit recursively. Either validate supported nesting or reject unsupported nesting explicitly. Do not silently skip it, and do not use the fix as a pruning command.

### #1350: a useful teaching example with a limited camera claim

The neutral exterior example is a valuable response to the earlier no-example policy, and the PR reports owner approval. Its use of existing vocabulary and scratch output lowers discovery effort. It is still a structure demonstration tied to the vocabulary's fixture camera.

The issue originally required #1298 first; the PR added the example while #1298 remains open. The code contains no new camera literal, which is helpful, but it still calls the fixture-based `Exterior` route. That does not demonstrate adoption of a map-owned resolved camera or guarantee that a later change will require no adapter edits.

Its two checks are scoped: no tall-and-continuous board, and a minimum menu-band coverage of 0.6 over sampled lane positions. That coverage floor is a baseline for this example, not a universal correctness threshold for exteriors. It could reward continuous near masses if generalized without the earlier report's gap, depth and readability requirements.

The rendered frames in the PR description are Blender EEVEE previews. They are not native LÖVE captures with the runtime compositor. Retain the example as teaching evidence, then add native review through an explicitly identified map contract when the camera seam is ready. Show more than one structurally valid arrangement so the example teaches alternatives rather than a new template to clone.

## A capability ladder that separates effort from authority

The alternate ladder is useful as a hypothesis. It should not place every adopted-source edit or ordinary rebake in an owner-only difficulty tier. Permission and technical difficulty are independent. An authorized bench move can be simple even in an adopted document; adopting a new source or changing canonical references remains a separate decision regardless of how easy the command is.

| Task | Small supported interface | What still decides acceptance |
| --- | --- | --- |
| Inspect or compile an existing source | Project/map identity, contextual description, one explicit compile/review command | Machine checks within their scopes |
| Edit one known feature | Named target, relational operation, fresh fingerprint, visible source diff | Ownership preservation and native evidence |
| Compose a new scaffold | Validated spec, parts catalogue, semantic arrangements, meaningful variants | Staging checks plus art review |
| Extend a builder or exporter | Shared semantics and fixtures from several actual uses | Technical review, bake correspondence and runtime proof |
| Adopt, ship or reconcile goldens | Concrete source/package/evidence record | Existing authorization and owner/reference policy |

The alternate rule that a mistake needing a reviewer two rungs higher implies a missing check is useful for mechanically decidable invariants. It cannot eliminate expert judgment for proportion, atmosphere or artistic coherence. The practical aim is to reserve that judgment for art rather than spend it diagnosing missing files and reversed axes.

## Combined sequence and issue coverage

| Sequence | Existing work | Reconciled outcome |
| --- | --- | --- |
| First: make the routes runnable | #1341, #1344, #1340; surface #1339/#1326 | Correct Project selection, complete pure-test discovery, immediate capture/dependency errors; strict required Blender CI |
| Next: make the route obvious | #1343 plus a role manifest from #1342 | One short routing table, generated capability index, current ownership/camera guidance; history reachable on demand |
| Next: make context visible | Catalogue #1345; project inventory and bridge description | Selected presentation, source status, dependencies, supported target operations and contextual previews |
| Then: reduce construction inference | #1346, camera #1298/#1338, place-spec #1347 | Shared scoped predicates, named frames and one scaffold compiler; adopted sources retain authority |
| In parallel: improve expressive units | #1348 and several semantic environment compositions | Editable item templates/finishes and genuinely distinct arrangements from known parts |
| Alongside new assemblies | #1085/#1301/#1322 and relevant source-role work | Explicit contributors/receivers and bake evidence rather than a broad green badge |
| Separately: control future revision noise | #1349/#1353 | Candidate identity and records, complete declared scope, scratch revisions, preservation-reviewed retirement |
| Teach and measure | #1350 with its camera boundary; lower-effort pilot | Examples with visible freedoms, matched native review, recorded authoring effort and success |

This sequence is an assessment, not a delivery checklist. Most of the alternate plan survives; the important change is to integrate correctness and ownership before treating field filling as safe authoring. Catalogue and test-discovery work can proceed without waiting for a universal place schema. Semantic compositions can be piloted without forcing a repository-wide recipe migration.

The controlled pilot should compare the current route and improved route on identical starting sources. Include one new waiting alcove, one adopted-window edit, one protected-path ground-cover task, one Classic/Wide review and one missing-dependency diagnosis. Measure completion, time to useful preview, custom scripts, unexplained coordinate choices, incorrect authority selections, recovery attempts and review omissions. Judge visual variety separately from mechanical validity. Record model/effort only when running that experiment; no such trial has been run by either audit.

## Verification and actions in this comparison

Freshly reproduced: the current corpus path failure, three asset-set test errors, the missing census import, the public-function split, referenced-model/source-stem counts, and the alternate candidate check's nested-source blind spot. Branch code, Issues and PR checks were read at the named snapshot. The PR's full Blender test suite, item compilation, native captures and gates were not rerun here.

This comparison added the reconciliation document, its evidence, scratch inspection/probe files and Issue #1353. It did not change sources, packages, recipes, runtime code, canonical references, the alternate branch or its Issues. It did not prune candidates, merge the PR, or post a review comment.
