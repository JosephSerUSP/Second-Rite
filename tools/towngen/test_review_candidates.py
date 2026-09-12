import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import review_candidates


class ReviewCandidateWorkflowTests(unittest.TestCase):
    def source_image(self, root):
        path = root / "source.png"
        Image.new("RGB", (1869, 842), (90, 110, 130)).save(path)
        return path

    def geometry_guide(self, root):
        path = root / "geometry.png"
        image = Image.new("RGB", (1065, 240), (128, 128, 128))
        draw = ImageDraw.Draw(image)
        draw.line((0, 239, 532, 66), fill=(110, 210, 140), width=2)
        draw.line((532, 66, 1064, 239), fill=(110, 210, 140), width=2)
        draw.line((180, 0, 128, 239), fill=(225, 190, 90), width=2)
        image.save(path)
        return path

    def test_precedent_packet_records_vertical_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / "packet"
            review_candidates.prepare_precedent(
                "port", self.source_image(root), self.geometry_guide(root), out)
            packet = json.loads((out / "precedent.json").read_text(
                encoding="utf-8"))
            self.assertEqual(packet["target"]["size"], [1065, 240])
            self.assertEqual(packet["framingRows"]["target"], {
                "horizon": 66,
                "actorGround": 136,
                "persistentUiBegins": 144,
            })
            self.assertTrue(packet["workingTransform"]["anisotropic"])
            self.assertEqual(len(packet["affordances"]), 5)
            self.assertIn("projected-geometry-guide.png",
                          packet["projectionAuthority"])
            self.assertIn("authoritative camera projection",
                          packet["promptPolicy"]["image2"])
            with Image.open(out / "normalized-proof.png") as image:
                self.assertEqual(image.size, (1065, 240))
            with Image.open(out / "semantic-edit-guide.png") as image:
                self.assertEqual(image.size, (1869, 842))

    def test_semantic_guide_rejects_non_contract_geometry_aspect(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad = root / "bad-geometry.png"
            Image.new("RGB", (100, 100), (128, 128, 128)).save(bad)
            with self.assertRaises(SystemExit):
                review_candidates.semantic_edit_guide(
                    "port", self.source_image(root), bad, root / "out.png")

    def test_blender_spatial_overlay_preserves_plate_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "spatial.png"
            out = root / "annotated.png"
            Image.new("RGB", (1065, 240), (80, 90, 100)).save(source)
            review_candidates.blender_spatial_overlay("port", source, out)
            with Image.open(out) as image:
                self.assertEqual(image.size, (1065, 240))
                self.assertNotEqual(image.getpixel((4, 2)), (80, 90, 100))

    def test_blender_spatial_overlay_rejects_wrong_size(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "bad.png"
            Image.new("RGB", (100, 100), (80, 90, 100)).save(source)
            with self.assertRaises(SystemExit):
                review_candidates.blender_spatial_overlay(
                    "port", source, root / "annotated.png")

    def test_working_guide_is_derived_from_full_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "full.png"
            out = root / "working.png"
            image = Image.new("RGB", (1065, 240), (10, 20, 30))
            image.putpixel((532, 136), (255, 0, 0))
            image.save(source)
            review_candidates.derive_working_guide(source, out)
            with Image.open(out) as working:
                self.assertEqual(working.size, (2160, 720))

    def test_working_guide_rejects_portrait_canvas(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "full.png"
            Image.new("RGB", (1065, 240), (10, 20, 30)).save(source)
            with self.assertRaises(SystemExit):
                review_candidates.derive_working_guide(
                    source, root / "working.png", width=1024, height=1536)

    def test_authored_centres_make_valid_non_mutating_remap_proposal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet_dir = root / "packet"
            review_candidates.prepare_precedent(
                "port", self.source_image(root), self.geometry_guide(root),
                packet_dir)
            review_path = packet_dir / "precedent.json"
            packet = json.loads(review_path.read_text(encoding="utf-8"))
            for row in packet["affordances"]:
                row["review"]["observedPlateX"] = row["authoredPlateX"]
            review_path.write_text(json.dumps(packet), encoding="utf-8")
            proposal_path = root / "proposal.json"
            review_candidates.remap_proposal(
                "port", review_path, proposal_path)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            self.assertEqual(proposal["status"], "valid-proposal")
            self.assertFalse(proposal["mutatedAuthoredData"])
            self.assertTrue(proposal["ownerApprovalRequired"])
            self.assertTrue(all(row["deltaPlateX"] == 0
                                for row in proposal["proposals"]))

    def test_precedent_packet_can_be_regenerated_from_local_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / "packet"
            review_candidates.prepare_precedent(
                "port", self.source_image(root), self.geometry_guide(root), out)
            review_candidates.prepare_precedent(
                "port", out / "aesthetic-precedent.png",
                out / "projected-geometry-guide.png", out)
            self.assertTrue((out / "precedent.json").exists())

    def test_remap_proposal_rejects_overlapping_transitions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet_dir = root / "packet"
            review_candidates.prepare_precedent(
                "port", self.source_image(root), self.geometry_guide(root),
                packet_dir)
            review_path = packet_dir / "precedent.json"
            packet = json.loads(review_path.read_text(encoding="utf-8"))
            for row in packet["affordances"]:
                row["review"]["observedPlateX"] = row["authoredPlateX"]
            # Keep the test tied to the live lane calibration. The port's
            # pixels-per-unit value is intentionally not a global constant.
            minimum = 1.8 * review_candidates.spec("port")["pixelsPerLaneUnit"]
            packet["affordances"][2]["review"]["observedPlateX"] = (
                packet["affordances"][1]["authoredPlateX"] + minimum * 0.5)
            review_path.write_text(json.dumps(packet), encoding="utf-8")
            proposal_path = root / "proposal.json"
            with self.assertRaises(SystemExit):
                review_candidates.remap_proposal(
                    "port", review_path, proposal_path)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            self.assertEqual(proposal["status"], "invalid-proposal")
            self.assertTrue(any("trigger overlap" in error
                                for error in proposal["errors"]))


if __name__ == "__main__":
    unittest.main()
