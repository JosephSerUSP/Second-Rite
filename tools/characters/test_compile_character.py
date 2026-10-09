import json
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from compile_character import compile_glb, read_glb

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'projects/experiments/continuous-surface-gauntlet/assets/authoring/characters/surveyor.glb'


class CharacterCompiler(unittest.TestCase):
    def test_adopted_provenance_matches_recipe_and_glb(self):
        for name in ['surveyor','attendant','sentinel']:
            source=SOURCE.with_name(name+'.glb')
            with self.subTest(character=name):
                record=json.loads(source.with_suffix('.build.json').read_text())
                self.assertEqual(record['glbSha256'], hashlib.sha256(source.read_bytes()).hexdigest())
                self.assertEqual(record['specSha256'], hashlib.sha256(source.with_suffix('.spec.json').read_bytes()).hexdigest())
                if 'authoredClips' in record:
                    self.assertEqual(record['authoredClips']['sha256'], hashlib.sha256(source.with_suffix('.clips.json').read_bytes()).hexdigest())
                asset,images=compile_glb(source)
                runtime=source.parents[2]/'characters'/name
                expected=(json.dumps(asset,separators=(',', ':'),allow_nan=False)+'\n').encode()
                self.assertEqual(expected,(runtime/'character.json').read_bytes())
                for texture,data in images.items(): self.assertEqual(data,(runtime/texture).read_bytes())

    def test_preserves_authored_uvs_weights_clips(self):
        asset, images = compile_glb(SOURCE)
        self.assertEqual(len(asset['joints']), 22)
        self.assertEqual(set(asset['clips']), {'idle', 'walk', 'anticipation', 'strike', 'recovery', 'hit'})
        self.assertEqual(sum(len(p['indices']) // 3 for p in asset['primitives']), 696)
        self.assertEqual(len(images), 1)
        self.assertTrue(all(c['times'][0] == 0 for a in asset['clips'].values() for c in a['channels']))
        self.assertTrue(all(abs(sum(v[12:]) - 1) < .001 for p in asset['primitives'] for v in p['vertices']))

    def reject(self, mutate):
        g, binary = read_glb(SOURCE)
        mutate(g)
        text = json.dumps(g).encode()
        text += b' ' * (-len(text) % 4)
        data = struct.pack('<4sII', b'glTF', 2, 12+8+len(text)+8+len(binary))
        data += struct.pack('<I4s',len(text),b'JSON')+text+struct.pack('<I4s',len(binary),b'BIN\0')+binary
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'bad.glb'; p.write_bytes(data)
            with self.assertRaises(ValueError): compile_glb(p)

    def test_required_extension_is_not_silently_ignored(self):
        self.reject(lambda g: g.update(extensionsRequired=['KHR_draco_mesh_compression']))

    def test_missing_walk_rejected(self):
        self.reject(lambda g: g.update(animations=[a for a in g['animations'] if a['name'] != 'Walk']))

    def test_unsupported_interpolation_rejected(self):
        self.reject(lambda g: g['animations'][0]['samplers'][0].update(interpolation='CUBICSPLINE'))

    def test_nonuniform_scale_rejected(self):
        self.reject(lambda g: g['nodes'][0].update(scale=[1,2,1]))

    def test_unskinned_mesh_rejected(self):
        def mutate(g):
            next(n for n in g['nodes'] if 'mesh' in n).pop('skin')
        self.reject(mutate)


if __name__ == '__main__':
    unittest.main()
