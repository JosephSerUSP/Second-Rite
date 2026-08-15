"""Corpus checks for the item model library, with their negative controls.

Every check here exists because the per-asset validity rubric passed the whole
2026-08 batch. So each one is tested twice: once that a clean corpus stays
clean, and once that the specific defect it exists to catch actually fails it.
A check that has only ever been run against known-bad data has not been shown
to detect anything.
"""
from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools" / "asset-production"))

import check_item_models  # noqa: E402
import item_model_corpus  # noqa: E402


def write_obj(
    directory: Path,
    name: str,
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, int, int]],
    with_uvs: bool = False,
) -> Path:
    lines = [f"v {x} {y} {z}" for x, y, z in vertices]
    if with_uvs:
        lines += [f"vt {(i % 3) / 2.0} {(i % 2) / 1.0}" for i in range(len(vertices))]
        lines += [f"f {a}/{a} {b}/{b} {c}/{c}" for a, b, c in faces]
    else:
        lines += [f"f {a} {b} {c}" for a, b, c in faces]
    path = directory / f"{name}.obj"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def tetra(scale: float = 1.0, offset: float = 0.0) -> list[tuple[float, float, float]]:
    return [
        (offset, offset, offset),
        (scale + offset, offset, offset),
        (offset, scale + offset, offset),
        (offset, offset, scale + offset),
    ]


TETRA_FACES = [(1, 2, 3), (1, 2, 4), (1, 3, 4), (2, 3, 4)]


def wedge() -> list[tuple[float, float, float]]:
    """A shape with a genuinely different silhouette from the tetrahedron."""
    return [
        (0.0, 0.0, 0.0),
        (4.0, 0.0, 0.0),
        (4.0, 0.2, 0.0),
        (0.0, 0.2, 0.0),
        (2.0, 0.1, 1.6),
    ]


WEDGE_FACES = [(1, 2, 3), (1, 3, 4), (1, 2, 5), (2, 3, 5), (3, 4, 5), (4, 1, 5)]


class GeometryHashTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_same_shape_at_a_different_scale_and_position_hashes_alike(self):
        """The defect that produced 27 identical armours was a renamed copy."""
        a = item_model_corpus.parse_obj(write_obj(self.dir, "a", tetra(1.0, 0.0), TETRA_FACES))
        b = item_model_corpus.parse_obj(write_obj(self.dir, "b", tetra(7.5, 12.0), TETRA_FACES))
        self.assertEqual(item_model_corpus.geometry_hash(a), item_model_corpus.geometry_hash(b))

    def test_different_shapes_hash_differently(self):
        a = item_model_corpus.parse_obj(write_obj(self.dir, "a", tetra(), TETRA_FACES))
        b = item_model_corpus.parse_obj(write_obj(self.dir, "b", wedge(), WEDGE_FACES))
        self.assertNotEqual(item_model_corpus.geometry_hash(a), item_model_corpus.geometry_hash(b))

    def test_reordered_vertices_do_not_launder_a_duplicate(self):
        verts = tetra()
        a = item_model_corpus.parse_obj(write_obj(self.dir, "a", verts, TETRA_FACES))
        b = item_model_corpus.parse_obj(
            write_obj(self.dir, "b", list(reversed(verts)), TETRA_FACES)
        )
        self.assertEqual(item_model_corpus.geometry_hash(a), item_model_corpus.geometry_hash(b))

    def test_degenerate_mesh_fails_loudly(self):
        flat = [(2.0, 2.0, 2.0)] * 4
        mesh = item_model_corpus.parse_obj(write_obj(self.dir, "flat", flat, TETRA_FACES))
        with self.assertRaises(item_model_corpus.ItemModelError):
            item_model_corpus.geometry_hash(mesh)


class SilhouetteTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_identical_shapes_score_one(self):
        a = item_model_corpus.parse_obj(write_obj(self.dir, "a", tetra(1.0), TETRA_FACES))
        b = item_model_corpus.parse_obj(write_obj(self.dir, "b", tetra(3.0), TETRA_FACES))
        score = item_model_corpus.silhouette_iou(
            item_model_corpus.silhouettes(a), item_model_corpus.silhouettes(b)
        )
        self.assertEqual(score, 1.0)

    def test_distinct_shapes_score_below_the_limit(self):
        a = item_model_corpus.parse_obj(write_obj(self.dir, "a", tetra(), TETRA_FACES))
        b = item_model_corpus.parse_obj(write_obj(self.dir, "b", wedge(), WEDGE_FACES))
        score = item_model_corpus.silhouette_iou(
            item_model_corpus.silhouettes(a), item_model_corpus.silhouettes(b)
        )
        self.assertLess(score, item_model_corpus.SILHOUETTE_IOU_LIMIT)

    def test_proportion_is_visible_to_the_silhouette_check(self):
        """Regression: the rasterizer used to fit each view to its own
        bounding box, which stretched every silhouette to fill the frame. A
        tall narrow shape and a short wide one scored a perfect 1.0, so
        proportion -- most of what distinguishes these objects -- was invisible.
        """
        squat = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 1.4, 0.0), (0.0, 1.4, 0.0), (1.0, 0.7, 1.0)]
        tall = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 2.2, 0.0), (0.0, 2.2, 0.0), (1.0, 1.1, 1.4)]
        faces = [(1, 2, 3), (1, 3, 4), (1, 2, 5), (2, 3, 5), (3, 4, 5), (4, 1, 5)]
        a = item_model_corpus.parse_obj(write_obj(self.dir, "squat", squat, faces))
        b = item_model_corpus.parse_obj(write_obj(self.dir, "tall", tall, faces))
        score = item_model_corpus.silhouette_iou(
            item_model_corpus.silhouettes(a), item_model_corpus.silhouettes(b)
        )
        self.assertLess(score, 0.8, "differing proportion must not score as identical")

    def test_a_difference_finer_than_display_size_is_not_a_difference(self):
        """Two shapes that differ only sub-pixel are one shape to the player.

        The base shape is deliberately off-grid. A regular tetrahedron
        normalizes to coordinates that land exactly on pixel centres, so its
        whole boundary rasterizes in while a hair-width copy's falls out --
        a knife-edge of the test data, not of the metric.
        """
        base = [(0.03, 0.07, 0.11), (1.13, 0.05, 0.09), (0.07, 1.09, 0.13), (0.11, 0.03, 1.07)]
        nudged = list(base)
        nudged[3] = (0.11, 0.03, 1.07 + 1e-4)
        a = item_model_corpus.parse_obj(write_obj(self.dir, "a", base, TETRA_FACES))
        b = item_model_corpus.parse_obj(write_obj(self.dir, "b", nudged, TETRA_FACES))
        score = item_model_corpus.silhouette_iou(
            item_model_corpus.silhouettes(a), item_model_corpus.silhouettes(b)
        )
        self.assertGreaterEqual(score, item_model_corpus.SILHOUETTE_IOU_LIMIT)


class CollectViolationsTests(unittest.TestCase):
    """The gate driver, against synthetic corpora it should pass and fail."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def kinds(self, models):
        return sorted(r["kind"] for r in check_item_models.collect_violations(models))

    def test_clean_corpus_has_no_violations(self):
        models = {
            "Tetra": write_obj(self.dir, "tetra", tetra(), TETRA_FACES, with_uvs=True),
            "Wedge": write_obj(self.dir, "wedge", wedge(), WEDGE_FACES, with_uvs=True),
        }
        self.assertEqual(check_item_models.collect_violations(models), [])

    def test_renamed_duplicate_is_caught(self):
        models = {
            "Tetra": write_obj(self.dir, "tetra", tetra(), TETRA_FACES, with_uvs=True),
            "Lantern": write_obj(self.dir, "lantern", tetra(4.0, 9.0), TETRA_FACES, with_uvs=True),
        }
        self.assertIn("duplicate_geometry", self.kinds(models))

    def test_two_items_sharing_one_file_is_caught(self):
        shared = write_obj(self.dir, "charm", wedge(), WEDGE_FACES, with_uvs=True)
        models = {"Alert Charm": shared, "Wind Charm": shared}
        self.assertIn("shared_file", self.kinds(models))

    def test_missing_uvs_is_caught(self):
        models = {
            "Tetra": write_obj(self.dir, "tetra", tetra(), TETRA_FACES, with_uvs=False),
            "Wedge": write_obj(self.dir, "wedge", wedge(), WEDGE_FACES, with_uvs=True),
        }
        self.assertIn("no_uvs", self.kinds(models))

    def test_a_duplicate_is_reported_once_not_twice(self):
        """Duplicate geometry is also an identical silhouette; report one."""
        models = {
            "Tetra": write_obj(self.dir, "tetra", tetra(), TETRA_FACES, with_uvs=True),
            "Lantern": write_obj(self.dir, "lantern", tetra(4.0), TETRA_FACES, with_uvs=True),
        }
        self.assertEqual(self.kinds(models), ["duplicate_geometry"])

    def _near_pair(self):
        """Two shapes that clear the loose bar but not the strict one.

        Measured at IoU 0.9157: comfortably under 0.97, comfortably over 0.85.
        Differing only in height, which is exactly the kind of difference the
        rasterizer's fixed domain exists to keep visible.
        """
        squat = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 1.4, 0.0), (0.0, 1.4, 0.0), (1.0, 0.7, 1.0)]
        tall = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 1.6, 0.0), (0.0, 1.6, 0.0), (1.0, 0.8, 1.0)]
        faces = [(1, 2, 3), (1, 3, 4), (1, 2, 5), (2, 3, 5), (3, 4, 5), (4, 1, 5)]
        return {
            "Alpha": write_obj(self.dir, "alpha", squat, faces, with_uvs=True),
            "Beta": write_obj(self.dir, "beta", tall, faces, with_uvs=True),
        }

    def test_legacy_pairs_are_measured_against_the_loose_bar(self):
        models = self._near_pair()
        violations = check_item_models.collect_violations(models, legacy=set(models))
        self.assertEqual([r["kind"] for r in violations], [])

    def test_a_pair_of_re_authored_items_faces_the_strict_bar(self):
        """The first lathe cohort cleared 0.97 by 0.008 and was still eight
        variations of one ring. New work has to show real margin."""
        models = self._near_pair()
        loose = check_item_models.collect_violations(models, legacy=set(models))
        strict = check_item_models.collect_violations(models, legacy=set())
        self.assertEqual(loose, [])
        self.assertEqual([r["kind"] for r in strict], ["indistinct_silhouette"])

    def test_one_legacy_member_keeps_the_pair_on_the_loose_bar(self):
        models = self._near_pair()
        violations = check_item_models.collect_violations(models, legacy={"Alpha"})
        self.assertEqual([r["kind"] for r in violations], [])

    def test_violation_keys_are_order_independent(self):
        left = check_item_models.violation_key("duplicate_geometry", ["B", "A"])
        right = check_item_models.violation_key("duplicate_geometry", ["A", "B"])
        self.assertEqual(left, right)


class LiveCorpusTests(unittest.TestCase):
    def test_every_referenced_item_model_parses(self):
        models = item_model_corpus.load_item_models()
        self.assertGreater(len(models), 100)
        for name, path in models.items():
            mesh = item_model_corpus.parse_obj(path)
            self.assertTrue(mesh.faces, f"{name}: no faces")
            self.assertTrue(
                all(math.isfinite(v) for v in mesh.vertices.ravel()),
                f"{name}: non-finite vertex",
            )

    def test_baseline_only_covers_violations_that_still_exist(self):
        """A baselined violation that no longer reproduces means it was fixed.

        The baseline may only shrink; leaving a stale entry would let a future
        duplicate re-enter the corpus under an already-accepted key.
        """
        baseline = check_item_models.load_baseline()
        if not baseline:
            self.skipTest("no baseline recorded yet")
        models = item_model_corpus.load_item_models()
        keys = {r["key"] for r in check_item_models.collect_violations(models)}
        self.assertEqual(sorted(baseline - keys), [])


if __name__ == "__main__":
    unittest.main()
