"""Optional host discovery; configured Blender integration remains strict."""
import os
import unittest

import blender_locator


def blender_executable():
    if not os.environ.get(blender_locator.ENV_VAR):
        message = f'{blender_locator.ENV_VAR} is unset; Blender integration was not run'
        if os.environ.get('BLENDER_TESTS_REQUIRED') == '1':
            raise AssertionError(message)
        raise unittest.SkipTest(message)
    try:
        return blender_locator.blender_executable()
    except blender_locator.BlenderError as error:
        # SystemExit aborts discovery; a normal failure preserves the full report.
        raise AssertionError(str(error)) from error
