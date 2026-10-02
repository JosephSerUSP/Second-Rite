"""Capture failures must restore stage hooks and never touch shipping sources."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT/'tools/blender/capture_environment.py'


class CaptureSafetyTests(unittest.TestCase):
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
