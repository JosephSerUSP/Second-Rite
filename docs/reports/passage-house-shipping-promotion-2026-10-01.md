# Passage House shipping promotion

The owner visually approved revision 18 and explicitly requested shipping after
the consolidation handoff. That supersedes the earlier unaccepted-room status;
foreground refinement remains #1308 and bake correspondence remains #1301.
Owner PLAYED acceptance is not claimed.

Map 32 is now authored shipping data at
`projects/hichaukitoden-game/data/maps/32.json`. The town generator owns the
Cortico/lodging connections: Cortico's unchanged Passage House event now enters
32 at `cortico_entry`; lodging returns to 32 at `lodging_entry`. Courtyard returns
resolve reciprocally to Cortico and lodging. Generator registration marks the
3D court authored and preserves it on town rebuild. Only maps 25/26 were regenerated;
their other placements/profiles/dialogue are unchanged. The opening retains direct
arrival into lodging. The duplicate candidate map was moved rather than retained
as another semantic authority.

The approved package is copied byte-for-byte to
`assets/environments/st_maria_town/passage_house_courtyard` inside the game Project.
The source remains a registered scaffold; only its map-authority metadata changed
to name `data/maps/32.json`, with a guard against intervening owner edits. New SHA-256:
`2e535bbf2007a3393131bfbe64f33c2e54d4cb695f86ab76b50082bc679e8d95`.
Approved study source hash remains recorded in review metadata. No geometry,
lighting, camera, atlas or collision was regenerated for promotion.

The courtyard's traversal suite is now a normal shipping runtime unit suite.
The review staging helper consumes the canonical shipping Project and optionally
overrides only its staged package for historical comparisons; it no longer rewrites
topology or patches shipping tests. Native capture hooks remain staged-only.

Local G1, G4, save/load, full shipping units, source registry, town checks,
editor/profile/geography checks and source recipe parity pass. G4 now reports
30 maps. All 14 native Classic/Wide frames match the approved study below row 4;
nine full frames differ by one pixel at row 4. Full-frame byte parity is not claimed.
Package files are byte-identical; collision remains unchanged. Seven native
Effekseer assertions were unavailable. Golden references were not recaptured.

PR #1296 is retargeted to main to include its renderer dependency in one shipping
review. PR #1294 should be closed as superseded only after that code lands.
The earlier optional G6 relative run failed during generated-inspection readiness
capture, not a completed candidate/base pixel comparison; it provides no green
G6 verdict. Required hosted Windows gates still govern the merge.
