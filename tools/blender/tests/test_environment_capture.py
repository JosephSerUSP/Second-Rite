"""Capture failures must restore stage hooks and never touch shipping sources."""
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from unittest.mock import patch
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT/'tools/blender/capture_environment.py'
sys.path.insert(0, str(ROOT/'tools/blender'))
import capture_environment as capture


class CaptureSafetyTests(unittest.TestCase):
    def arguments(self, root):
        return Namespace(game_root=root, output=root/'review', map_id=28,
            positions=[1], unobstructed=False, device=[2100, 900], lovec='lovec')

    @staticmethod
    def frame(visible=6000):
        return {'y': 1, 'width': 256, 'height': 240,
            'viewportVisiblePixels': visible, 'image': 'eA=='}

    def test_fresh_stage_installs_probe_and_restores_after_success(self):
        (ROOT/'out').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'out') as directory:
            root=Path(directory)
            main=root/'main.lua'; original=b'cli_tools.runTownProofFrames(loader)\r\n'
            main.write_bytes(original)
            def run(*args, **kwargs):
                self.assertTrue((root/'tests/environment_frames.lua').is_file())
                self.assertIn(b'love.errorhandler', main.read_bytes())
                payload=json.dumps([self.frame()])
                return subprocess.CompletedProcess(args, 0, 'ENVIRONMENT FRAMES BEGIN'+payload+'ENVIRONMENT FRAMES END', '')
            with patch.object(capture.subprocess, 'run', side_effect=run):
                capture.capture(self.arguments(root))
            self.assertEqual(main.read_bytes(), original)
            self.assertFalse((root/'tests').exists())
            self.assertFalse((root/'environment-review.json').exists())
            self.assertEqual(len(list((root/'review').glob('*/1.png'))), 4)

    def test_empty_viewport_fails_before_writing_evidence_and_restores_stage(self):
        (ROOT/'out').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'out') as directory:
            root=Path(directory)
            main=root/'main.lua'; original=b'cli_tools.runTownProofFrames(loader)\r\n'
            main.write_bytes(original)
            payload=json.dumps([self.frame(visible=648)])
            result=subprocess.CompletedProcess([], 0,
                'ENVIRONMENT FRAMES BEGIN'+payload+'ENVIRONMENT FRAMES END', '')
            with patch.object(capture.subprocess, 'run', return_value=result), self.assertRaisesRegex(
                    RuntimeError, 'environment viewport is effectively empty'):
                capture.capture(self.arguments(root))
            self.assertEqual(main.read_bytes(), original)
            self.assertFalse((root/'review').exists())
            self.assertFalse((root/'environment-review.json').exists())

    def test_visibility_evidence_is_required(self):
        with self.assertRaisesRegex(RuntimeError, 'omitted viewport visibility evidence'):
            capture.validate_visible_environment('wide', [
                {'y': 1, 'width': 426, 'height': 240}
            ])

    def test_timeout_and_bad_payload_restore_borrowed_stage_files(self):
        (ROOT/'out').mkdir(exist_ok=True)
        failures=[subprocess.TimeoutExpired('lovec',120), subprocess.CompletedProcess([],0,'missing payload','')]
        for failure in failures:
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory(dir=ROOT/'out') as directory:
                root=Path(directory)
                (root/'main.lua').write_bytes(b'cli_tools.runTownProofFrames(loader)\r\n')
                (root/'tests').mkdir()
                probe=root/'tests/environment_frames.lua'; probe.write_bytes(b'-- caller probe\r\n')
                config=root/'environment-review.json'; config.write_bytes(b'\xef\xbb\xbf{}\r\n')
                before={path:path.read_bytes() for path in (root/'main.lua',probe,config)}
                options={'side_effect':failure} if isinstance(failure,Exception) else {'return_value':failure}
                with patch.object(capture.subprocess, 'run', **options), self.assertRaises(RuntimeError):
                    capture.capture(self.arguments(root))
                self.assertEqual({path:path.read_bytes() for path in before},before)
                self.assertFalse((root/'review').exists())

    def test_shipping_root_is_refused_without_modification(self):
        main = ROOT/'runtime/main.lua'
        before = main.read_bytes()
        result = subprocess.run([sys.executable,str(SCRIPT),'--game-root',str(ROOT/'runtime'),
            '--output',str(ROOT/'out/capture-should-not-exist'),'--map-id','28','--positions','1'],
            capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertIn('disposable stage',result.stderr)
        self.assertEqual(main.read_bytes(),before)

    def test_process_failure_restores_original_hook_and_configuration(self):
        (ROOT/'out').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'out',prefix='capture-safety-') as directory:
            root=Path(directory)
            main=root/'main.lua';before=b'-- retained\r\ncli_tools.runTownProofFrames(loader)\r\n'
            main.write_bytes(before)
            config=root/'environment-review.json';config.write_bytes(b'{"retained":true}\r\n')
            result=subprocess.run([sys.executable,str(SCRIPT),'--game-root',str(root),
                '--output',str(root/'review'),'--map-id','28','--positions','1',
                '--lovec',sys.executable],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(main.read_bytes(),before)
            self.assertEqual(config.read_bytes(),b'{"retained":true}\r\n')


if __name__=='__main__':unittest.main()
