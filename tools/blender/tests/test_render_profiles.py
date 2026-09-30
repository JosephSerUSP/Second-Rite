import unittest
from types import SimpleNamespace as NS
from tools.blender import render_profiles as profiles


class RenderProfilesTests(unittest.TestCase):
    def test_real_blender_preserves_projection(self):
        from tools.blender.tests.test_eevee_backend import blender, TOOLS
        result = blender("-P", str(TOOLS / "tests" / "render_profiles_blender.py"))
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-1000:])
        self.assertIn("RENDER_PROFILE_SMOKE_OK", result.stdout)

    def test_expensive_settings_require_selection(self):
        for name in ("draft", "lookdev", "review", "export"):
            profile = profiles.resolve(name)
            self.assertEqual(profile.engine, "BLENDER_EEVEE")
            self.assertEqual(profile.supersample, 1)
        self.assertEqual(profiles.resolve("cycles-comparison").engine, "CYCLES")
        self.assertEqual(profiles.resolve(supersample=3).supersample, 3)

    def test_invalid_requests_fail_loudly(self):
        for kwargs in ({"samples": 0}, {"supersample": -1}, {"samples": True},
                       {"supersample": 1.5}, {"engine": "unknown"}):
            with self.assertRaises(ValueError):
                profiles.resolve(**kwargs)
        with self.assertRaises(ValueError):
            profiles.resolve("unknown")

    def test_quality_preserves_authored_camera_and_lighting(self):
        scene = NS(render=NS(resolution_x=906, resolution_y=240),
                   view_settings=NS(exposure=0.6, view_transform="AgX"),
                   eevee=NS(), cycles=NS(), camera=object(), world=object())
        camera, world = scene.camera, scene.world
        profiles.apply(scene, profiles.resolve())
        self.assertIs(scene.camera, camera)
        self.assertIs(scene.world, world)
        self.assertEqual(scene.render.resolution_x, 906)
        self.assertEqual(scene.view_settings.view_transform, "AgX")
        self.assertEqual(scene.view_settings.exposure, 0)


if __name__ == "__main__":
    unittest.main()
