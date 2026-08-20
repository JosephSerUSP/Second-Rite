"""Phase 10: assemble town-gauntlet-next-report.md from the recorded evidence."""
from __future__ import annotations

import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOWN = ROOT / "projects/hichaukitoden-game/assets/authoring/town"
ATT = TOWN / "attempts_next"
EXPORT = ROOT / "exports/environments/town_next"
OUT = TOWN / "town-gauntlet-next-report.md"


def jload(p, default=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else default


def size(p):
    return p.stat().st_size if p.is_file() else 0


def human(n):
    for u in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or u == "GiB":
            return "%.1f %s" % (n, u) if u != "B" else "%d B" % n
        n /= 1024.0


def main():
    census = jload(ATT / "census.json", {})
    ev = jload(ATT / "evaluation.json", {})
    winner_census = jload(TOWN / "winner_census.json", {})
    envjson = jload(EXPORT / "environment.json", {})
    prov = jload(TOWN / "material-provenance.json", {})
    by = ev.get("byAttempt", {})

    L = []
    A = L.append
    A("# Second Gate - next town visual gauntlet (report)")
    A("")
    A("Branch `exp/town-material-gauntlet`, stacked on PR #859 "
      "(`prep/town-gauntlet-camera-authority`). No PR was merged. "
      "PR #856's first-gauntlet evidence was not modified.")
    A("")

    A("## 1. Camera validation")
    A("")
    A("`python tools/blender/check_next_town_camera.py` **passes**.")
    A("")
    A("```")
    A("THESTRA_TOWN_CAMERA_CALIBRATION OK eye=(0.900000,5.500000,0.000000) "
      "pitch=0.000000 fovHalfX=0.250000000")
    A("THESTRA_TOWN_CAMERA_BLENDER OK lens=43.2676mm pitch=0 offsets=-96,0,+96 "
      "transformInvariant=true")
    A("```")
    A("")
    A("It did **not** pass as found. `tools/blender/tests/town_camera_blender.py` "
      "compared Blender's single-precision `camera.data.lens` against a "
      "double-precision derivation with a 1e-8 absolute tolerance. At ~43 mm the "
      "float32 resolution is ~3.8e-6, so the check was mathematically unreachable; "
      "`float32(expected) == float32(lens)` exactly and the 8.06e-07 delta was pure "
      "storage rounding. The tolerance now scales with float32 resolution.")
    A("")
    A("That assertion is a near-tautology by construction - `thestra_camera` sets "
      "`camera.lens = SENSOR_WIDTH_MM * ax * 0.5` from the same record fields the "
      "expectation re-derives - so it can only ever detect rounding. The guards that "
      "actually protect art direction were negative-controlled and both correctly "
      "reject bad input:")
    A("")
    A("| negative control | result |")
    A("|---|---|")
    A("| pitch = -30 deg (the exact #856 mistake) | rejected: \"town camera must be level\" |")
    A("| fovHalfX = 0.55 (wide parity-style) | rejected: lens 19.667 mm outside the 40-45 mm family |")
    A("| real calibration | accepted: 43.2676 mm |")
    A("")

    A("### Calibrated values used throughout")
    A("")
    A("| quantity | value |")
    A("|---|---|")
    A("| pitch | 0 deg (level side view) |")
    A("| horizontal FOV | 28.0724869 deg (`fovHalfX` = 0.25) |")
    A("| Blender lens | **43.2676 mm** |")
    A("| eye | (0.9, 5.5, 0.0), fixed |")
    A("| forward / screen-right / up | +X / +Y / +Z |")
    A("| target | 426x240 (base viewport 256x144) |")
    A("| horizon | y = 70 px (29% from top) |")
    A("")
    A("**A framing consequence worth recording.** `fovHalfX`/`fovHalfY` are tangents, "
      "so the visible frame at distance *d* is `(2*0.25*d) x (2*0.140625*d)`. At the "
      "study's 6.9-unit framing distance a 1.7 m person fills **88% of the frame "
      "height** - that distance was chosen to compare lenses, not to stage a town. "
      "The action plane therefore sits at x = 19.0 (d = 18.1), where the frame is "
      "~15.1 x 8.5 units and the protagonist renders at exactly **24x48 px**, one "
      "native walker cell at 1:1. The eye, lens and pitch were never touched.")
    A("")

    A("## 2. Material micro-gauntlet (Phase 1)")
    A("")
    A("`town-material-gauntlet-contact-sheet.png` - 16 samples across 6 surface "
      "families on identical geometry, camera, lighting and exposure, each rendered "
      "at both 512 px study scale and the real 426x240 town scale.")
    A("")
    A("Procedural was initially handicapped by a bug rather than by the strategy: the "
      "palette was authored in sRGB numbers and assigned straight to Blender colour "
      "sockets, which are **linear**, so every procedural sample rendered roughly "
      "twice as bright and desaturated. After fixing that and four specific defects "
      "(an inverted joint mask washing every cobble pale green, a rust ramp turning "
      "iron into tan cloud, roof rows carrying all the relief so tiles read flat, and "
      "a dense distance-to-edge voronoi crazing plaster into a regular ceramic net), "
      "procedural improved substantially but still does not match a curated CC0 scan "
      "or a generated albedo on hero field surfaces: it lacks high-frequency "
      "micro-detail and keeps a soft, low-contrast read.")
    A("")

    A("### Strategy C: the brief's 2x2 sheet format does not work, and why")
    A("")
    A("The brief's default was one 1024x1024 sheet carrying albedo / height / "
      "roughness / AO in four quadrants. Measured on real output from two models, "
      "the quadrants are **not pixel-registered**:")
    A("")
    A("| model | structural alignment vs albedo | tonal correlation | albedo vertical ramp |")
    A("|---|---|---|---|")
    A("| gpt-image-1-mini | r = 0.06 - 0.38 | up to +0.83 | +32.0 |")
    A("| gpt-image-2 | r = 0.16 - 0.42 | up to +0.74 | +4.9 |")
    A("")
    A("A usable set needs ~0.9+. Both models returned four tonal variants of one lit "
      "render; the \"height\" quadrant shaded flat dentil faces with a 66-level "
      "top-to-bottom gradient, which is shading, not elevation.")
    A("")
    A("Strategy C was therefore restructured to generate **one flat albedo** - the one "
      "thing the models do well - and derive the rest numerically, so registration is "
      "exact by construction and the brief's preferred chain "
      "(`generated height -> Blender bump/normal -> optional displacement`) is "
      "preserved. Normals are never generated.")
    A("")
    A("| height map | low-frequency shading energy | detail std |")
    A("|---|---|---|")
    A("| generated quadrant (same subject) | 21.02 | 39.10 |")
    A("| derived from the same lit albedo | 6.25 | 54.38 |")
    A("| derived from a flat gpt-image-2 albedo | **1.50 - 3.17** | 41.0 - 53.1 |")
    A("")
    A("Derivation quality is bounded by albedo flatness, which is why gpt-image-2 "
      "(ramp +4.9) is used rather than gpt-image-1-mini (ramp +32.0).")
    A("")

    A("## 3. Material palette and provenance")
    A("")
    if prov:
        sc = prov.get("strategyCounts", {})
        A("%d materials: **%d procedural**, **%d CC0 public-library**, "
          "**%d OpenAI-generated**." % (len(prov.get("materials", [])),
                                        sc.get("procedural", 0),
                                        sc.get("public-library", 0),
                                        sc.get("openai-generated", 0)))
        A("")
        A("Machine-readable manifest: `material-provenance.json`.")
        A("")
        A("Poly Haven assets are **CC0-1.0**, verified at <https://polyhaven.com/license> "
          "on 2026-08-20: commercial use and redistribution permitted, attribution not "
          "required. Every downloaded file is recorded with its source URL and sha256. "
          "No API key is stored anywhere in the repository.")
        A("")
        A("| role | id | strategy | licence |")
        A("|---|---|---|---|")
        for m in prov.get("materials", []):
            if m["strategy"] == "public-library":
                A("| %s | `%s` | CC0 library | %s |" % (m.get("paletteRole", ""), m["id"], m["license"]))
        for m in prov.get("materials", []):
            if m["strategy"] == "openai-generated":
                A("| %s | `%s` | generated albedo + derived maps | owner-generated |"
                  % (m["id"].split(":")[1], m["id"]))
        A("")

    A("## 4. Attempts 01-09")
    A("")
    A("`town-gauntlet-contact-sheet.png` (3x3, native 426x240 renders, aspect preserved).")
    A("")
    A("| # | title | material bias | TH_SOURCE tris | TH_RENDER tris | reduction | blind score |")
    A("|---|---|---|---|---|---|---|")
    for aid in sorted(census):
        c = census[aid]
        s = by.get(aid, {}).get("mean")
        A("| %s | %s | %s | %s | %s | %s:1 | %s |" % (
            aid, c["title"], c["bias"], f"{c['sourceTris']:,}", f"{c['renderTris']:,}",
            f"{c['reductionRatio']:.0f}", ("**%.2f**" % s) if s else "-"))
    A("")
    A("Attempts 01-06 diverge; 07-09 converge on the evaluation of 01-06.")
    A("")

    A("## 5. Blind evaluation (Phase 4)")
    A("")
    A("Two evaluators scored every attempt on 15 criteria, 1-10, from the image alone, "
      "in a shuffled presentation order with no material-strategy hint.")
    A("")
    A("**Evaluator independence is weaker than intended.** `OPENROUTER_API_KEY` is "
      "present but the account returns `HTTP 402 Payment Required`, so the second "
      "evaluator is a different OpenAI model generation (`gpt-4.1`) rather than a "
      "second vendor. The two disagree substantially - they rank the top attempt "
      "differently - so they are not merely echoing each other, but this is not "
      "cross-vendor independence.")
    A("")
    if by:
        agg = collections.defaultdict(list)
        for a, v in by.items():
            for c, s in v.get("perCriterion", {}).items():
                agg[c].append(s)
        A("| criterion | mean across 9 attempts |")
        A("|---|---|")
        for c, v in sorted(agg.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
            A("| %s | %.2f |" % (c.replace("_", " "), sum(v) / len(v)))
        A("")
    A("The shape of this is the finding: **the collapse to cheap runtime geometry is "
      "the strongest thing here (8.94) and traversal clarity is solid (7.78), while "
      "distinctiveness (2.78), procedural repetition (2.83) and believable surface age "
      "(3.17) are the weakest.** The pipeline works; the art direction is not yet "
      "characterful.")
    A("")
    A("Convergence measurably moved the criteria it targeted: foreground framing rose "
      "from **1.75** across 01-06 to **3.50** across all nine (5.5 on the winner), and "
      "architectural depth from 3.25 to 3.61. Distinctiveness barely moved "
      "(2.58 -> 2.78) and remains the clearest unsolved problem.")
    A("")
    A("Representative criticisms, quoted from the raw evaluations "
      "(`attempts_next/evaluation.json`):")
    A("")
    A("- *\"The huge, visibly tiled cobblestone ground dominates the image with "
      "repetitive noise, flattening depth and hurting character legibility.\"*")
    A("- *\"Severe tiling/repetition of identical door bays and wall panels, making "
      "the scene read as a copied module with shallow depth and no focal variation.\"*")
    A("- *\"All building facades and ground plane are very flat.\"*")
    A("")

    A("## 6. Winner")
    A("")
    if winner_census:
        A("**Attempt %s - %s.**" % (winner_census.get("attempt"),
                                    census.get(winner_census.get("attempt"), {}).get("title", "")))
        A("")
        A("Selected as the highest blind mean (**%.2f**), and it is also a genuine "
          "three-strategy hybrid: CC0 stone and timber field textures, an "
          "OpenAI-generated shopfront timber, and a procedural metal, with procedural "
          "grime over the library scans." % (by.get(winner_census.get("attempt"), {}).get("mean") or 0))
        A("")
    A("## 7. Source vs runtime census (Phase 9)")
    A("")
    if winner_census and envjson:
        rows = [
            ("TH_SOURCE triangles", f"{winner_census['sourceTris']:,}"),
            ("TH_RENDER triangles", f"{winner_census['renderTris']:,}"),
            ("reduction ratio", "%.0f:1" % winner_census["reductionRatio"]),
            ("source materials", str(len(winner_census.get("sourceMaterials", [])))),
            ("runtime materials", "1 (one baked atlas)"),
            ("atlas dimensions", "%dx%d" % (envjson["atlas"]["width"], envjson["atlas"]["height"])),
            ("atlas PNG bytes", human(size(EXPORT / "environment.png"))),
            ("runtime package bytes", human(sum(size(p) for p in EXPORT.glob("*") if p.is_file()))),
            (".blend bytes", human(size(TOWN / "town-next.blend"))),
        ]
        A("| quantity | value |")
        A("|---|---|")
        for k, v in rows:
            A("| %s | %s |" % (k, v))
        A("")
        A("Material-source breakdown of the winner: `%s`."
          % json.dumps(winner_census.get("materialStrategies", {})))
        A("")
    A("`winner_source_vs_baked.png` puts the rich TH_SOURCE render beside the "
      "atlas-on-TH_RENDER result at matched framing.")
    A("")

    A("## 8. Projection-window proof (Phase 7)")
    A("")
    A("`town-final-projection-window-strip.png` renders the winner at "
      "`projectionWindowOffsetX` = -96 / 0 / +96. The strip builder **asserts** that "
      "the lens and the eye transform are identical across all three and fails if "
      "they are not; only the window moves.")
    A("")

    A("## 9. Known weaknesses")
    A("")
    A("- **Distinctiveness is the weakest criterion (2.78).** Nothing here yet says "
      "\"Thestra\" rather than \"a generic old European street\". No signage, no "
      "civic landmark, no repeated motif, no colour identity.")
    A("- **Facade bays still read as repeated modules** even with per-bay variation.")
    A("- **The ground competes with the characters.** Both evaluators independently "
      "flagged the cobblestone as too busy at 426x240.")
    A("- **Procedural materials get no displaced source geometry.** `height_for()` "
      "resolves a height *file*, and node-based materials have none, so attempt 02 "
      "reports 1:1 rather than a real reduction. Baking procedural height to an image "
      "would fix this and was not done.")
    A("- **Rooflines are out of frame by construction.** With a level eye 1.7 m above "
      "the street and the horizon at 29% from top, any 5-6 m building exceeds the "
      "frame. Height variation in the rhythm is therefore invisible; variation has to "
      "come from facade detail, depth stagger and openings.")
    A("- **Evaluator independence** is single-vendor (see section 5).")
    A("- **One generated sheet in the manifest is an experiment record** "
      "(`gen_facade_ornament_img2`), retained as evidence of the 2x2 failure rather "
      "than used as a production material.")
    A("")

    A("## 10. Which techniques to retain")
    A("")
    A("| technique | verdict |")
    A("|---|---|")
    A("| CC0 Poly Haven scans for hero field surfaces | **retain** - strongest richness per effort |")
    A("| Generated flat albedo + numerically derived maps | **retain** - best for bespoke carved ornament that no library has |")
    A("| Generated 2x2 PBR sheets | **drop** - quadrants are not registered |")
    A("| Procedural as a hero field material | **de-prioritise** - lacks micro-detail |")
    A("| Procedural as a grime/moss/tonal overlay | **retain** - this is where it genuinely wins, and it breaks library tiling |")
    A("| Displaced flat facade panels on TH_SOURCE | **retain** - watertight relief; never displace a box |")
    A("| Bake COMBINED to one atlas on coarse geometry | **retain** - the headline result, 8.94/10 collapsibility |")
    A("")

    A("## 11. Recommended next step")
    A("")
    A("**Solve distinctiveness before adding any more material technology.** The "
      "pipeline is proven and the collapse is excellent; what is missing is authored "
      "identity. Concretely: give Thestra one repeated architectural motif (a specific "
      "arch profile or window shape), a restricted colour identity, one civic landmark "
      "silhouette visible from several compositions, and hand-placed props with real "
      "silhouettes. Quiet the ground material so the protagonist reads. Do that as an "
      "art-direction pass on the winning composition rather than as another "
      "nine-attempt gauntlet.")
    A("")

    OUT.write_text("\n".join(L), encoding="utf-8")
    print("wrote %s (%d lines)" % (OUT, len(L)))


if __name__ == "__main__":
    main()
