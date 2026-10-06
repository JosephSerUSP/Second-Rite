# Read-only native UV-index drift fixture

This is the new tome source **before** its cover finish was materialized. It
is a reproduction fixture, not a shipping source. Never promote or regenerate
it. Its original surface atlas is colocated so the saved document resolves it.

Source SHA256: `5ca40f5e590645f3289d07fa76358c193a8b99f19ad2d9d09c2ad94e256dc1f8`.
Pinned Windows Blender 5.2.2 LTS, build `d13f752e3b9c`. With
`BLENDER_EXECUTABLE` set to that installation and `PYTHONUTF8=1`, from the
designated worktree:

```powershell
python tools/blender/compile_item_blends.py --source docs/reports/item-model-continuous-review/repro/tome_wind_blade.blend --output-dir out/repro-a
python tools/blender/compile_item_blends.py --source docs/reports/item-model-continuous-review/repro/tome_wind_blade.blend --output-dir out/repro-b
```

Compare OBJ bytes, then resolve face indices into ordered vertex/UV/normal
attributes and material assignments. The observed pair had different UV aliases
and face indices, while decoded attributes and material order were exactly
equal. There were no changed `v` or `vn` records. Two future executions may
happen to match: the retained fixture supports investigation, not a guarantee
of drift on every pair. Hash the source before/after; compilation is read-only.

[The retained observation](../repeat-uv-evidence.json) names both hashes and
record counts. The production tome was fixed by directly applying only its
saved cover SOLIDIFY/BEVEL, verifying evaluated positions at seven-decimal precision,
then quantizing source UVs to six decimals. The shared compiler and older
sources were unchanged. The final production source passes an independent
repeat byte check and shipping `compile --check`; Linux remains unverified.

Related existing investigations: #1355 (Chrysalis normal rounding) and #1369
(cross-host Windows/Linux byte differences). This observation is same-host,
with matching decoded geometry, and should not be conflated with either.
The deferred investigation is [#1447](https://github.com/JosephSerUSP/Second-Rite/issues/1447).
