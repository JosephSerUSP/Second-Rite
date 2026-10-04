"""Build/check a portable named-datablock library; no network or preferences changes."""
import hashlib
import json
import sys
import uuid
from pathlib import Path
import bpy


def inspect_dependencies():
    unpacked = [image.name for image in bpy.data.images if image.source == "FILE"
                and not image.packed_file and not image.packed_files]
    if unpacked:
        raise ValueError(f"Unpacked external images: {unpacked}")
    linked = [block.name for block in bpy.data.user_map() if block.library is not None
              and not isinstance(block, bpy.types.Library)]
    if linked:
        raise ValueError(f"Library contains external linked datablocks: {linked}")


def main():
    mode, directory = sys.argv[sys.argv.index("--") + 1:]
    root = Path(directory)
    manifest_path = root / "provenance.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    names = {record["asset"] for record in manifest["assets"]}
    output = root / "library/selected_materials.blend"
    if mode == "build":
        bpy.ops.wm.read_factory_settings(use_empty=True)
        catalog = str(uuid.uuid5(uuid.NAMESPACE_URL, "hichaukitoden/vendor-materials"))
        for record in manifest["assets"]:
            with bpy.data.libraries.load(str(root / record["localPath"]), link=False) as (source, target):
                if record["asset"] not in source.materials:
                    raise ValueError(f"Missing named material: {record['asset']}")
                target.materials = [record["asset"]]
            material = target.materials[0]
            material.use_fake_user = True
            material.asset_mark()
            material.asset_data.catalog_id = catalog
            material.asset_data.author = record["author"]
            material.asset_data.license = record["license"]
        for block in bpy.data.user_map():
            if block.asset_data and not (isinstance(block,bpy.types.Material) and block.name in names):
                block.asset_clear()
        bpy.ops.file.pack_all()
        inspect_dependencies()
        output.parent.mkdir(parents=True,exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output))
        (output.parent / "blender_assets.cats.txt").write_text(
            f"VERSION 1\n{catalog}:Materials/Curated Essentials:Curated Essentials\n", encoding="utf-8")
        manifest["files"] = [file for file in manifest["files"] if file["localPath"] != "library/selected_materials.blend"]
        manifest["files"].append({"localPath": "library/selected_materials.blend",
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()})
        catalog_file = output.parent / "blender_assets.cats.txt"
        relative = "library/blender_assets.cats.txt"
        manifest["files"] = [file for file in manifest["files"] if file["localPath"] != relative]
        manifest["files"].append({"localPath": relative,
            "sha256": hashlib.sha256(catalog_file.read_bytes()).hexdigest()})
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    elif mode == "check":
        bpy.ops.wm.open_mainfile(filepath=str(output))
        inspect_dependencies()
        assets = {material.name for material in bpy.data.materials if material.asset_data}
        marked = [block for block in bpy.data.user_map() if block.asset_data]
        if any(not isinstance(block, bpy.types.Material) or block.name not in names for block in marked):
            raise ValueError("Unselected asset datablocks in curated library")
        for record in manifest["assets"]:
            metadata = bpy.data.materials[record["asset"]].asset_data
            if metadata.author != record["author"] or metadata.license != record["license"]:
                raise ValueError(f"Asset metadata differs: {record['asset']}")
        if assets != names:
            raise ValueError(f"Selected assets differ: {assets} != {names}")
    else:
        raise ValueError(mode)
    print("VENDOR BLENDER CHECK OK")


if __name__ == "__main__":
    main()
