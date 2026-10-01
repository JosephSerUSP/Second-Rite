import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from tools.blender.vendor_assets import verify


class VendorAssetsTests(unittest.TestCase):
    def test_committed_selection_is_available_offline(self):
        root=Path(__file__).resolve().parents[1]/"vendor-library"
        record=verify(root)
        self.assertEqual({asset["asset"] for asset in record["assets"]},
            {"Bricks - Cobblestone","Clay","Fabric - Linen"})

    def test_missing_changed_or_escaping_files_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            original=b"original"
            (root/"asset.blend").write_bytes(original)
            def manifest(relative="asset.blend"):
                (root/"provenance.json").write_text(json.dumps({"files":[{"localPath":relative,
                    "sha256":hashlib.sha256(original).hexdigest()}]}),encoding="utf-8")
            manifest();verify(root)
            (root/"asset.blend").write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError,"changed"):verify(root)
            manifest("missing.blend")
            with self.assertRaisesRegex(ValueError,"Missing"):verify(root)
            manifest("../outside.blend")
            with self.assertRaisesRegex(ValueError,"leaves library"):verify(root)


if __name__=="__main__":unittest.main()
