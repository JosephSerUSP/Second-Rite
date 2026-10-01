# Repo-local curated Essentials materials

The original downloads under `upstream/` are immutable, SHA256-addressed files.
`provenance.json` records authors, CC0 declarations, listing index hash, URLs,
retrieval time and Blender requirements. Shared source files are deduplicated by hash.
Project adaptations live in the courtyard source, separately from these assets.

`library/` contains only the three selected material assets: Bricks - Cobblestone,
Clay, and Fabric - Linen. All dependencies are packed or procedural. The saved library
and source open with Blender 5.2.2; automatic Python execution is disabled in tools.
No global preferences have been changed and nothing has been published.

Open `library/selected_materials.blend` directly or append its named materials.
If you choose to register an Asset Browser library manually, select **this `library/`
subfolder**, not the parent containing upstream archives. The repository's own library
remains separate at `tools/blender/asset-library/`. Registration is optional and is
not performed by these commands.

Offline integrity/dependency check from the repository root:

```powershell
python tools/blender/vendor_assets.py check
```

Use `--hash-only` without Blender. The full check opens the curated library with
Python socket connections denied and rejects unpacked external images, linked
external datablocks, unexpected assets and metadata mismatches. It does not change
machine networking. Builds and staging never fetch materials.

Acquisition is a separate, deliberate network operation:

```powershell
python tools/blender/vendor_assets.py acquire --library out/new-curated-library --asset "Bricks - Cobblestone" --asset Clay --asset "Fabric - Linen"
```

Each download must match the listing's declared size and SHA256 before it is written.
The material selection uses the existing read-only catalog browser (`asset_library.py`);
only acquisition downloads source files. Review new provenance before adoption.
