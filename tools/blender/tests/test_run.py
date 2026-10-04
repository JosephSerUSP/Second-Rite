"""run.py, and the rule it exists for: a headless Blender run must fail loudly.

Blender exits 0 when a ``--python`` script raises unless ``--python-exit-code``
is passed. A caller that checks the exit code then reports a crashed bake, a
failed structural verification or a broken probe as success. The guard below
keeps every tool that launches Blender itself on the fail-loud side.
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools" / "blender"
sys.path.insert(0, str(TOOLS))
import run  # noqa: E402
from blender_test_support import blender_executable  # noqa: E402

RUN = TOOLS / "run.py"

# A quoted ``--python``/``-P`` argument (Python/JS), or a bare ``--python`` flag
# (YAML/PowerShell/shell), next to a locator token, means the file launches
# Blender itself rather than through a helper that already carries the flag.
LAUNCH = re.compile(r"""["'](--python|-P)["']|\s--python\s""")
LOCATOR = ("blender_executable", "blender_locator", "BLENDER_EXECUTABLE", "blenderExecutable")
# Studies are retained evidence (SCRIPTS.md); the item toolkit is a standalone
# bundle that cannot use this repository's locator.
EXEMPT_PREFIXES = ("tools/blender/second-rite-item-model-toolkit/",)


def dry_run(*argv):
    result = subprocess.run([sys.executable, str(RUN), "--dry-run", *argv],
                            capture_output=True, text=True, cwd=ROOT, timeout=60)
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


class LauncherTests(unittest.TestCase):
    def test_every_run_fails_loudly_and_is_headless(self):
        command = dry_run("tools/blender/recipes/alicias_padaria.py")
        for flag in ("--background", "--factory-startup"):
            self.assertIn(flag, command)
        self.assertEqual(command[command.index("--python-exit-code") + 1], "1")

    def test_blend_opens_before_the_script_and_arguments_pass_through(self):
        blend = "projects/hichaukitoden-game/assets/authoring/environments/alicias_padaria.blend"
        command = dry_run("recipes/alicias_padaria.py", "--blend", blend,
                          "--", "--variant", "alcove", "--", "inner")
        self.assertLess(command.index(str((ROOT / blend).resolve())), command.index("--python"))
        self.assertEqual(command[command.index("--") + 1:], ["--variant", "alcove", "--", "inner"])

    def test_script_paths_resolve_from_root_or_tool_folder(self):
        expected = str((TOOLS / "stage_room_model.py").resolve())
        for given in ("tools/blender/stage_room_model.py", "stage_room_model.py"):
            command = dry_run(given)
            self.assertEqual(command[command.index("--python") + 1], expected)

    def test_a_missing_script_names_what_was_tried(self):
        with self.assertRaises(SystemExit) as raised:
            run.resolve("recipes/no_such_recipe.py", "script")
        self.assertIn("no_such_recipe.py", str(raised.exception))


class FailLoudGuardTests(unittest.TestCase):
    def test_every_blender_launch_passes_python_exit_code(self):
        offenders = []
        for base in ("tools", ".github"):
            for path in (ROOT / base).rglob("*"):
                relative = path.relative_to(ROOT).as_posix()
                if (path.suffix not in (".py", ".js", ".yml", ".ps1", ".sh")
                        or not path.is_file()
                        or path.name.startswith("study_") or path == Path(__file__).resolve()
                        or any(part in (".venv", "node_modules") for part in path.parts)
                        or relative.startswith(EXEMPT_PREFIXES)):
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                if (LAUNCH.search(text) and any(token in text for token in LOCATOR)
                        and "--python-exit-code" not in text):
                    offenders.append(relative)
        self.assertEqual(offenders, [], "these launch Blender without --python-exit-code 1, so a "
                         "raised script exits 0; add the flag or launch through tools/blender/run.py")


class RealBlenderTests(unittest.TestCase):
    """The negative control: a raising script must turn into a failed run."""

    def launch(self, body):
        blender_executable()  # skip without Blender; fail if configured but wrong
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "probe.py"
            script.write_text(body, encoding="utf-8")
            return subprocess.run([sys.executable, str(RUN), str(script), "--", "token"],
                                  capture_output=True, text=True, cwd=ROOT, timeout=600)

    def test_a_raising_script_fails(self):
        result = self.launch("import bpy\nraise RuntimeError('deliberate probe failure')\n")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("deliberate probe failure", result.stdout + result.stderr)
        self.assertIn("run.py: FAILED", result.stderr)

    def test_a_clean_script_passes_and_receives_its_arguments(self):
        result = self.launch("import sys, bpy\nprint('PROBE', sys.argv[sys.argv.index('--') + 1:])\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PROBE ['token']", result.stdout)


if __name__ == "__main__":
    unittest.main()
