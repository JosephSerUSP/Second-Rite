"""#827: the checker must resolve a Project, and say so when it cannot."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.roots import DEFAULT_PROJECT_ROOT, PROJECT_ENV, project_root  # noqa: E402


class ProjectRootTests(unittest.TestCase):
    def test_default_is_the_in_repo_project(self):
        self.assertEqual(project_root(env={}), DEFAULT_PROJECT_ROOT.resolve())

    def test_configured_project_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "data").mkdir()
            self.assertEqual(project_root(env={PROJECT_ENV: tmp}), Path(tmp).resolve())

    def test_a_directory_without_data_is_not_a_project(self):
        # The installation root is the specific wrong answer this gate used to
        # assume, so it is the one worth pinning: it must fail here, naming
        # itself, rather than surfacing later as a missing data/items.json.
        install_root = DEFAULT_PROJECT_ROOT.parents[1]
        with self.assertRaises(RuntimeError) as caught:
            project_root(env={PROJECT_ENV: str(install_root)})
        self.assertIn("contains no data/", str(caught.exception))

    def test_a_missing_path_is_reported_as_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            gone = str(Path(tmp) / "absent")
            with self.assertRaises(RuntimeError) as caught:
                project_root(env={PROJECT_ENV: gone})
            self.assertIn("does not exist", str(caught.exception))

    def test_blank_configuration_falls_back_to_the_default(self):
        self.assertEqual(project_root(env={PROJECT_ENV: "   "}), DEFAULT_PROJECT_ROOT.resolve())


if __name__ == "__main__":
    unittest.main()
