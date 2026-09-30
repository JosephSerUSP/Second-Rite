# Rebaking the shop 3D packages on the packed atlas layout (2026-09-30)

Owner decision (2026-09-30): rebake both shop packages on the packed layout at 1024. The reasons
and the measurements are in `eevee-atlas-and-grass-placement-2026-09-30.md`; this records what
was rebaked and how it was checked.

## What was done

`export_room_environment.py --atlas-layout packed` for each room (Blender 5.2.2, Cycles, the
exporter's default lighting and 24 samples, the anchors the packages already carry), installed with
`install_room_3d.py`. The bake took 303 s (Padaria) and 211 s (smith).

| package | atlas PNG | atlas non-black | geometry |
|---|---|---|---|
| `alicias_padaria_3d` | 684,668 -> 1,670,386 bytes | 24.7% -> 86.5% | 1934 vertices, 4986 UVs, 3208 faces, max vertex difference 0.0 |
| `lauras_smith_3d` | 652,755 -> 1,503,984 bytes | 27.6% -> 86.7% | 1186 vertices, 3450 UVs, 1816 faces, max vertex difference 0.0 |

Vertices, faces and the UV count are identical; only the UV coordinates and the atlas image change,
so `environment.obj` differs on its `vt` lines and the PNG grows about 2.4x (it now carries texels
where it was mostly empty). `environment.json` is byte-identical apart from line endings (the
`provenance.sourceBlend` record the installer writes matches the one already there), and
`collision.obj` and `environment.mtl` are unchanged: the exporter's default collision ceiling (3.9)
differs from the one the shipped Padaria used (3.7), so the shipped collision files were kept rather
than regenerated. That is a note for the next rebake: pass `--ceiling 3.7` for the Padaria.

## How it was checked

- `st-maria-shop-atlas-rebake-2026-09-30/package_before_after.png`: both packages, old and new, photographed from their actual
  files (OBJ + atlas PNG) unlit, nearest-sampled, at native size with no film filter, from two lane
  positions each (`tools/blender/photograph_room_package.py`). The Padaria's azulejo dado returns
  and the wall texture holds detail.
- Staged unit suites: `ALL UNIT TESTS OK`. G1: `VALIDATE OK`.
- G5: no committed golden frame shows either shop's 3D room (the frames under
  `tools/golden/screens/` are map, battle, menu and special), so no golden moves and none is
  recaptured. The hosted relative G5 A/B is advisory.
- Not run: the shops in the live game window (this sandbox has no way to drive it); the picture
  above is Blender's rendering of the package files, not LÖVE's.

Agent-Signature:
  platform: Claude Code (desktop)
  model: Sonnet 5.5
  role: implementation
  task: "owner decision: rebake shop packages, packed 1024"
  base: 10187b92
