import io
import os
import random
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import image_storage  # noqa: E402


class ImageStorageTests(unittest.TestCase):
    def test_indexed_png_preserves_rgba_exactly(self):
        source = Image.new("RGBA", (128, 128))
        colours = [((index * 37) % 256, (index * 71) % 256,
                    (index * 109) % 256, 255) for index in range(64)]
        rng = random.Random(12345)
        source.putdata([colours[rng.randrange(len(colours))]
                        for _index in range(128 * 128)])
        encoded = image_storage.png_bytes(source)
        with Image.open(io.BytesIO(encoded)) as decoded:
            self.assertEqual(source.tobytes(), decoded.convert("RGBA").tobytes())
            self.assertEqual("P", decoded.mode)

    def test_lossless_webp_preserves_room_pixels(self):
        source = Image.new("RGB", (32, 32))
        source.putdata([((x * 17) % 256, (x * 31) % 256, (x * 47) % 256)
                        for x in range(1024)])
        encoded = image_storage.webp_bytes(source)
        with Image.open(io.BytesIO(encoded)) as decoded:
            self.assertEqual(source.convert("RGBA").tobytes(),
                             decoded.convert("RGBA").tobytes())

    def test_audit_never_rewrites_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "sample.png")
            Image.new("RGBA", (32, 32), (1, 2, 3, 255)).save(path)
            with open(path, "rb") as handle:
                before = handle.read()
            result = image_storage.audit(path)
            with open(path, "rb") as handle:
                after = handle.read()
            self.assertEqual(before, after)
            self.assertGreater(result["saving"], 0)


if __name__ == "__main__":
    unittest.main()
