"""Missing optional integrations skip; required/configured integrations fail."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_locator
import blender_test_support as support


class IntegrationPreconditionTests(unittest.TestCase):
    def test_unconfigured_optional_integration_skips(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(unittest.SkipTest):
            support.blender_executable()

    def test_required_integration_cannot_skip(self):
        with patch.dict(os.environ, {'BLENDER_TESTS_REQUIRED': '1'}, clear=True):
            with self.assertRaisesRegex(AssertionError, 'unset'):
                support.blender_executable()

    def test_configured_invalid_blender_fails_without_aborting_discovery(self):
        with patch.dict(os.environ, {'BLENDER_EXECUTABLE': '/missing'}, clear=True):
            with self.assertRaisesRegex(AssertionError, 'does not exist'):
                support.blender_executable()

    def test_wrong_version_cannot_become_a_skip(self):
        with patch.dict(os.environ, {'BLENDER_EXECUTABLE': 'configured'}, clear=True):
            with patch.object(blender_locator, 'blender_executable', side_effect=blender_locator.BlenderError('wrong version')):
                with self.assertRaisesRegex(AssertionError, 'wrong version'):
                    support.blender_executable()
