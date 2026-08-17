from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import classes


PROJECT = Path(__file__).resolve().parents[3] / "projects" / "labs" / "sol-game-01"


class ProjectConfigTests(unittest.TestCase):
    def tearDown(self):
        classes.configure()

    def test_project_style_and_prompt_do_not_use_root_second_gate_guidance(self):
        classes.configure(PROJECT)
        registry = classes.registry()
        self.assertNotIn("RPG Maker 2003", registry["styleBible"])
        self.assertIn("municipal telephone exchange", registry["styleBible"])
        ctx = classes.resolve("sprite", {})
        prompt = classes.prompt(ctx, "Probe", "a call button")
        self.assertIn("municipal telephone exchange", prompt)
        self.assertNotIn("first-person dungeon corridor", prompt)

    def test_root_registry_keeps_historical_class_style(self):
        classes.configure()
        self.assertIn("RPG Maker 2003", classes.registry()["styleBible"])

    def test_project_rejects_output_dirs_outside_project_assets(self):
        classes.configure(PROJECT)
        original = classes.project_config
        classes.project_config = lambda: {"classes": {"sprite": {"dir": "../assets"}}}
        try:
            with self.assertRaisesRegex(ValueError, "under assets/"):
                classes.registry()
        finally:
            classes.project_config = original


if __name__ == "__main__":
    unittest.main()
