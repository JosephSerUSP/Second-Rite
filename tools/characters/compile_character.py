"""Compile chara-compiler's deform-only GLB into the runtime character contract.

No Blender or game semantics here: retain glTF skeleton/TRS tracks and authored
UVs/weights. The Lua consumer alone poses the character, including for Studio.
Usage: python tools/characters/compile_character.py SOURCE.glb --out DIR [--check]
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


def read_glb(path):
    data = Path(path).read_bytes()
    magic, version, length = struct.unpack_from('<4sII', data)
    if magic != b'glTF' or version != 2 or length != len(data):
        raise ValueError('requires complete glTF 2 binary')
    offset, chunks = 12, {}
    while offset < len(data):
        size, kind = struct.unpack_from('<I4s', data, offset)
        chunks[kind] = data[offset + 8:offset + 8 + size]
        offset += 8 + size
    return json.loads(chunks[b'JSON']), chunks[b'BIN\0']


def compile_glb(path):
    g, binary = read_glb(path)
    if g.get('extensionsRequired'):
        raise ValueError('required glTF extensions are unsupported')
    if len(g.get('buffers', [])) != 1 or g['buffers'][0].get('uri'):
        raise ValueError('requires one embedded buffer')

    def accessor(index):
        a = g['accessors'][index]
        if a.get('sparse') or a.get('normalized'):
            raise ValueError('sparse/normalized accessors unsupported')
        v = g['bufferViews'][a['bufferView']]
        if v.get('buffer', 0) != 0:
            raise ValueError('external buffer unsupported')
        width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
        kind = {5121: 'B', 5123: 'H', 5125: 'I', 5126: 'f'}[a['componentType']]
        size = struct.calcsize('<' + kind * width)
        stride = v.get('byteStride', size)
        start = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        rows = [list(struct.unpack_from('<' + kind * width, binary, start + i * stride))
                for i in range(a['count'])]
        if not all(math.isfinite(x) for row in rows for x in row):
            raise ValueError('nonfinite accessor')
        return rows

    if len(g.get('skins', [])) != 1:
        raise ValueError('requires exactly one deform skin')
    skin = g['skins'][0]
    nodes, parents = [], {}
    for index, n in enumerate(g['nodes']):
        if 'matrix' in n:
            raise ValueError('node matrix requires upstream TRS export')
        scale = n.get('scale', [1, 1, 1])
        if max(scale) - min(scale) > 1e-5 or min(scale) <= 0:
            raise ValueError('requires positive uniform node scale')
        nodes.append({'name': n.get('name', str(index)),
                      'translation': n.get('translation', [0, 0, 0]),
                      'rotation': n.get('rotation', [0, 0, 0, 1]), 'scale': scale})
        for child in n.get('children', []):
            if child in parents:
                raise ValueError('node has multiple parents')
            parents[child] = index
    for child, parent in parents.items():
        nodes[child]['parent'] = parent + 1
    images = {}
    for i, image in enumerate(g.get('images', [])):
        if image.get('mimeType') != 'image/png' or 'bufferView' not in image:
            raise ValueError('requires embedded PNG albedo')
        v = g['bufferViews'][image['bufferView']]
        images[f'texture-{i}.png'] = binary[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]
    primitives = []
    for node_index, node in enumerate(g['nodes']):
        if 'mesh' not in node:
            continue
        if node.get('skin') != 0:
            raise ValueError('all character mesh nodes must use the deform skin')
        for p in g['meshes'][node['mesh']]['primitives']:
            if p.get('mode', 4) != 4 or p.get('targets'):
                raise ValueError('requires triangulated deform-only mesh')
            a = p['attributes']
            # The compiler retains UV_DEV layers alongside runtime UV0. They
            # are source authoring data; only the albedo's declared UV0 is used.
            if set(a) - {'POSITION', 'NORMAL', 'TEXCOORD_0', 'TEXCOORD_1', 'TEXCOORD_2', 'JOINTS_0', 'WEIGHTS_0'}:
                raise ValueError('unsupported vertex attributes')
            position, normal, uv, joints, weights = [accessor(a[k]) for k in
                ('POSITION', 'NORMAL', 'TEXCOORD_0', 'JOINTS_0', 'WEIGHTS_0')]
            if len({len(x) for x in (position, normal, uv, joints, weights)}) != 1:
                raise ValueError('attribute counts disagree')
            vertices = []
            for xyz, n, tex, j, w in zip(position, normal, uv, joints, weights):
                if min(w) < 0 or abs(sum(w) - 1) > .001 or any(x >= len(skin['joints']) for x in j):
                    raise ValueError('invalid deform weights/joints')
                vertices.append(xyz + tex + n + [x + 1 for x in j] + w)
            indices = [v[0] + 1 for v in accessor(p['indices'])]
            if len(indices) % 3 or any(i < 1 or i > len(vertices) for i in indices):
                raise ValueError('invalid triangle indices')
            material = g['materials'][p['material']]
            if material.get('alphaMode', 'OPAQUE') != 'OPAQUE':
                raise ValueError('only opaque character materials supported')
            pbr = material['pbrMetallicRoughness']
            texture = g['textures'][pbr['baseColorTexture']['index']]
            if pbr['baseColorTexture'].get('texCoord', 0) != 0:
                raise ValueError('requires UV0')
            primitives.append({'node': node_index + 1, 'vertices': vertices, 'indices': indices,
                               'material': material.get('name', f"material-{p['material']}"),
                               'texture': f"texture-{texture['source']}.png",
                               'color': pbr.get('baseColorFactor', [1, 1, 1, 1])})
    clips = {}
    for animation in g.get('animations', []):
        name = animation['name'].lower()
        if name in clips:
            raise ValueError('duplicate clip name')
        channels, duration = [], 0
        for channel in animation['channels']:
            s = animation['samplers'][channel['sampler']]
            interpolation = s.get('interpolation', 'LINEAR')
            if interpolation not in ('LINEAR', 'STEP'):
                raise ValueError('unsupported interpolation')
            target = channel['target']
            if target['path'] not in ('translation', 'rotation', 'scale'):
                raise ValueError('unsupported animation target')
            times = [r[0] for r in accessor(s['input'])]
            values = accessor(s['output'])
            if len(times) != len(values) or not times or times[0] < 0 or any(b <= a for a, b in zip(times, times[1:])):
                raise ValueError('invalid key times')
            if target['path'] == 'scale' and any(max(v) - min(v) > 1e-5 or min(v) <= 0 for v in values):
                raise ValueError('animated scale must be positive uniform')
            duration = max(duration, times[-1])
            channels.append({'node': target['node'] + 1, 'path': target['path'],
                             'interpolation': interpolation, 'times': times, 'values': values})
        # Blender NLA clips begin at frame 1. Preserve the clip's relative key
        # schedule while publishing a zero-based presentation clock.
        starts = {c['times'][0] for c in channels}
        if len(starts) != 1:
            raise ValueError('clip tracks must share an authored start')
        start = starts.pop()
        for c in channels:
            c['times'] = [t - start for t in c['times']]
        duration -= start
        if duration <= 0:
            raise ValueError('clip must have positive duration')
        clips[name] = {'duration': duration, 'channels': channels}
    if not {'idle', 'walk'} <= clips.keys():
        raise ValueError('character requires authored idle and walk clips')
    bundle = {'kind': 'hichaukitoden-character', 'version': 1,
              'source': {'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(), 'format': 'glTF-2',
                         'up': 'y', 'forward': '+z'},
              'nodes': nodes, 'joints': [j + 1 for j in skin['joints']],
              'inverseBind': accessor(skin['inverseBindMatrices']), 'primitives': primitives, 'clips': clips}
    if len(bundle['inverseBind']) != len(bundle['joints']) or not primitives:
        raise ValueError('missing deform data')
    return bundle, images


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('glb', type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    bundle, images = compile_glb(args.glb)
    outputs = {'character.json': (json.dumps(bundle, separators=(',', ':'), allow_nan=False) + '\n').encode(), **images}
    if not args.check:
        args.out.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        target = args.out / name
        if args.check:
            if not target.exists() or target.read_bytes() != data:
                raise ValueError(f'compiled character stale: {target}')
        else:
            target.write_bytes(data)
    print(f"CHARACTER {'CHECK' if args.check else 'COMPILE'} OK: {len(bundle['joints'])} joints, "
          f"{sum(len(p['indices']) // 3 for p in bundle['primitives'])} triangles, clips={','.join(bundle['clips'])}")


if __name__ == '__main__':
    main()
