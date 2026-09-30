"""The Blender locator: one env var, one pin, a loud version assertion (#1254).

No real Blender is needed: a tiny script that prints a chosen ``--version``
stands in for it, which is all the locator ever asks of the executable.
"""
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import blender_locator as locator

# Every name a Blender was once located by, and every hardcoded search list.
RETIRED = ("BLENDER_PATH", "BLENDER_BIN", "os.environ.get(\"BLENDER\")",
           "env.BLENDER_PATH", "Blender 4.2", "Blender 4.1")


def _fake_blender(directory, version):
    path = Path(directory) / ("fake-blender.bat" if os.name == "nt" else "fake-blender")
    if os.name == "nt":
        path.write_text("@echo Blender %s\n" % version)
    else:
        path.write_text("#!/bin/sh\necho 'Blender %s'\necho ' build date: today'\n" % version)
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


class LocatorTests(unittest.TestCase):
    def test_pin_is_an_exact_five_two_release_with_both_archives(self):
        pin = json.loads(locator.PIN_PATH.read_text(encoding="utf-8"))
        self.assertRegex(pin["version"], r"^5\.2\.\d+$")
        for platform in ("windows-x64", "linux-x64"):
            self.assertIn(pin["version"], pin["archives"][platform]["url"])

    def test_pinned_version_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            exe = _fake_blender(temp, locator.pinned_version())
            self.assertEqual(locator.blender_executable({locator.ENV_VAR: exe}), exe)

    def test_any_other_version_names_both_versions(self):
        with tempfile.TemporaryDirectory() as temp:
            exe = _fake_blender(temp, "5.1.2")
            with self.assertRaises(SystemExit) as raised:
                locator.blender_executable({locator.ENV_VAR: exe})
            message = str(raised.exception)
            self.assertIn("5.1.2", message)
            self.assertIn(locator.pinned_version(), message)

    def test_a_patch_release_of_the_same_series_is_still_a_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            exe = _fake_blender(temp, "5.2.99")
            with self.assertRaises(SystemExit):
                locator.assert_version(exe, "5.2.0")

    def test_unset_variable_fails_instead_of_searching(self):
        with self.assertRaises(SystemExit) as raised:
            locator.blender_executable({})
        self.assertIn(locator.ENV_VAR, str(raised.exception))

    def test_missing_file_fails(self):
        with self.assertRaises(SystemExit):
            locator.blender_executable({locator.ENV_VAR: "/nonexistent/blender"})

    def test_output_without_a_version_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "not-blender"
            path.write_text("#!/bin/sh\necho hello\n")
            path.chmod(path.stat().st_mode | stat.S_IEXEC)
            if os.name != "nt":
                with self.assertRaises(SystemExit):
                    locator.blender_executable({locator.ENV_VAR: str(path)})


class OneLocatorTests(unittest.TestCase):
    def test_retired_locators_no_longer_appear_in_code(self):
        offenders = []
        for base in ("tools", ".github"):
            for path in (ROOT / base).rglob("*"):
                if (path.suffix not in (".py", ".js", ".yml", ".ps1", ".sh")
                        or path.name in ("test_blender_locator.py", "blender_locator.py")
                        or "node_modules" in path.parts):
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                offenders += ["%s: %s" % (path.relative_to(ROOT), token)
                              for token in RETIRED if token in text]
        self.assertEqual(offenders, [])

    def test_install_directory_search_is_confined_to_the_standalone_toolkit(self):
        """No repo tool may hunt for a Blender in install directories.

        The retired-token scan above cannot see this: a script that walks
        ``Program Files\\Blender Foundation`` picks whichever Blender it finds,
        which is exactly what a version pin exists to stop. The one deliberate
        exception is the item toolkit, a self-contained bundle meant to be
        extracted and run outside this repository (it vendors its own core and
        carries an integrity manifest), so it cannot call the repo's locator or
        read the repo's pin. It is listed here, by name, so the exemption is
        visible and cannot widen by accident.
        """
        standalone = ("tools/blender/second-rite-item-model-toolkit",)
        for directory in standalone:
            self.assertTrue((ROOT / directory).is_dir(),
                            "%s is exempt but no longer exists; drop it from the list" % directory)
        offenders = []
        for base in ("tools", ".github"):
            for path in (ROOT / base).rglob("*"):
                relative = path.relative_to(ROOT).as_posix()
                if (path.suffix not in (".py", ".js", ".yml", ".ps1", ".sh", ".bat")
                        or path.name == "test_blender_locator.py"
                        or "node_modules" in path.parts
                        or any(relative.startswith(d + "/") for d in standalone)):
                    continue
                if "Blender Foundation" in path.read_text(encoding="utf-8", errors="replace"):
                    offenders.append(relative)
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
