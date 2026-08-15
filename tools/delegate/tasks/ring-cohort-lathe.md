# Task — author the first gauntlet cohort: 8 rings on the profile lathe

## Goal

The item model library shipped in August 2026 contains 207 items over only 112
distinct shapes. Eight of those items — Ruby Ring, Sapphire Ring, Emerald Ring,
Pearl Ring, Onyx Ring, Peace Ring, Protect Ring, Medicine Ring — currently
share **one identical mesh**.

Replace those eight meshes with eight genuinely distinct ones, authored on the
new profile lathe, and make them pass the corpus gate on their own merits.

This is the first cohort of a "gauntlet" production model: a small cohort that
must survive every mechanical check individually, rather than a large batch
scored in aggregate. Do not extend the cohort beyond these eight items.

## Read first

- `tools/asset-production/lathe.py` — the primitive you will author against.
  Read its module docstring and `lathe()` signature carefully.
- `tools/asset-production/tests/test_lathe.py` — shows the API in use,
  including `closed_profile`.
- `tools/asset-production/check_item_models.py` — the gate you must satisfy.
- `tools/asset-production/README.md`, section "Item model corpus gate".
- `tools/asset-language/materials.json` — the **only** legal material ids.

## Current truth to establish before changing anything

Verify these yourself rather than trusting this packet:

1. `python tools/asset-production/check_item_models.py --report` currently
   prints `ITEM MODELS OK`, with the eight rings appearing as a `baselined`
   `duplicate_geometry` group.
2. The eight items in `data/items.json` and the `.obj` paths they reference.
3. `python -m unittest discover -s tools/asset-production/tests -p "test_lathe.py"`
   passes (23 tests).

Note: `tests/test_model_census.py` fails to import `mesh_recipe` in a fresh
checkout. That is pre-existing and out of scope — do not fix it, do not report
it as a finding.

## Owner decisions (do not revisit)

- The existing 208 models stay in place as placeholders. You are replacing
  eight of them, not deleting the library.
- Rings are differentiated **by form**, not by colour. The canonical material
  registry has no gem colours, and adding them is explicitly out of scope;
  colour is deferred to a later texture-projection pass. Distinguish the rings
  by band section, setting shape, shoulder profile and proportion.
- Geometry is authored as a data table of profiles, not as eight hand-written
  scripts. One builder, eight declarative entries.

## Required semantics / acceptance criteria

1. A new builder writes all eight OBJs plus their shared MTL, deterministically:
   running it twice produces byte-identical files.
2. Every ring is built through `lathe.lathe()`. Do not write a second mesh
   generator, do not emit OBJ by hand — use `lathe.write_obj` / `lathe.write_mtl`.
3. All eight pass the corpus gate **without being baselined**:
   - no `duplicate_geometry` among them or against the other 199 items;
   - no `indistinct_silhouette` pair, including against the other 199 items;
   - no `no_uvs` — the lathe gives UVs for free, so a ring lacking them means
     something went wrong;
   - no `shared_file`.
4. The eight baselined `duplicate_geometry` / `no_uvs` entries these rings
   currently occupy must be **removed** from `item-model-baseline.json`, and
   the gate must be green afterwards. The baseline may only shrink. Do not run
   `--write-baseline` — edit out only the entries that no longer reproduce, and
   show the diff.
5. `data/items.json` keeps pointing at the same eight paths (overwrite the
   OBJs in place). If you must change a path, say so explicitly.
6. New tests covering the builder, in `tools/asset-production/tests/`.

## Must preserve

- `data/items.json` formatting: 2-space indent, existing key order, and its
  existing line endings. Several item names are non-ASCII; do not mangle them.
- Every material id must exist in `materials.json`. `lathe.write_obj` already
  enforces this — do not weaken that check to make a build pass.
- Do not modify `lathe.py`'s validation to accept a profile it currently
  rejects. If you believe a rejection is wrong, stop and report it instead.

## Explicit non-goals

- Do not touch any of the other 199 item models.
- Do not add gem colours or new materials.
- Do not restructure `tools/asset-gen/`.
- Do not attempt texture generation, Stable Diffusion, or anything GPU-bound.
- Do not add a Blender dependency.

## Verification

Everything here runs in a bare worktree with Python and numpy — **no GPU, no
LOVE, no Effekseer DLL**:

```text
python tools/asset-production/check_item_models.py --report
python -m unittest discover -s tools/asset-production/tests -p "test_lathe.py"
python -m unittest discover -s tools/asset-production/tests -p "test_item_model_corpus.py"
```

**Do not run or claim the golden gates (G1-G6).** They need a GPU and a native
DLL this worktree does not have. Reporting a gate result you did not observe is
the failure that matters most here.

### Required evidence

For each of the eight rings, include in your report an ASCII silhouette dump
from all three axes, produced with the existing helper:

```python
import sys; sys.path.insert(0, "tools/asset-production")
import item_model_corpus as C
mesh = C.parse_obj(path)
for view in C.silhouettes(mesh, res=28):
    for row in view[::-1]:
        print("".join("#" if v else "." for v in row))
```

A ring that passes the numeric checks but whose silhouette does not look like
a ring is a failure, and the dump is how a reviewer sees that in one read.
Also report the closest silhouette IoU each ring scored against any other item,
so the reviewer can see how much margin the cohort actually has rather than
just that it cleared the threshold.

## Delivery

- Work in your assigned worktree and branch; do not touch the primary checkout.
- Do not merge. Leave the branch for review.
- Report separately: what you proved by running it, versus what you believe but
  did not verify.
- Sign per `tools/delegate/AGENT-PROVENANCE.md`.
