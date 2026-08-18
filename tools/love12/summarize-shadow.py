#!/usr/bin/env python3
import json, os, re, sys
from pathlib import Path
from PIL import Image

root = Path(sys.argv[1]).resolve()

def envelope(path, begin, end):
    text = path.read_text(encoding='utf-8', errors='replace')
    m = re.search(re.escape(begin) + r'\s*(\{.*?\})\s*' + re.escape(end), text, re.S)
    return json.loads(m.group(1)) if m else None

def profile(path):
    text = path.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'MAP BUILD PROFILE BEGIN\s*(\{.*?\})\s*MAP BUILD PROFILE END', text, re.S)
    return json.loads(m.group(1)) if m else {'rawMarkerPresent': 'MAP BUILD PROFILE' in text}

def compare_dirs(a, b):
    pa = {p.relative_to(a).as_posix(): p for p in a.rglob('*.png')}
    pb = {p.relative_to(b).as_posix(): p for p in b.rglob('*.png')}
    changed_files = 0
    changed_pixels = 0
    total_pixels = 0
    max_channel_delta = 0
    for rel in sorted(set(pa) | set(pb)):
        if rel not in pa or rel not in pb:
            changed_files += 1
            continue
        ia = Image.open(pa[rel]).convert('RGBA')
        ib = Image.open(pb[rel]).convert('RGBA')
        if ia.size != ib.size:
            changed_files += 1
            continue
        total_pixels += ia.width * ia.height
        aa = ia.tobytes(); bb = ib.tobytes()
        file_changed = False
        for index in range(0, len(aa), 4):
            delta = max(abs(aa[index+c] - bb[index+c]) for c in range(4))
            if delta:
                changed_pixels += 1
                file_changed = True
                if delta > max_channel_delta: max_channel_delta = delta
        if file_changed: changed_files += 1
    return {
        'filesA': len(pa), 'filesB': len(pb), 'changedFiles': changed_files,
        'changedPixels': changed_pixels, 'totalPixels': total_pixels,
        'changedPixelFraction': (changed_pixels / total_pixels) if total_pixels else None,
        'maxChannelDelta': max_channel_delta,
    }

frames = {p.stem: envelope(p, 'LOVE12 SHADOW BEGIN', 'LOVE12 SHADOW END') for p in sorted(root.glob('frame-*.txt'))}
profiles = {p.stem: profile(p) for p in sorted(root.glob('profile-*.txt'))}
visuals = {}
a = root / 'visual-11a-opengl'; b = root / 'visual-11b-opengl'; c = root / 'visual-12-opengl'; v = root / 'visual-12-vulkan'
if a.exists() and b.exists(): visuals['11a_vs_11b_control'] = compare_dirs(a,b)
if a.exists() and c.exists(): visuals['11a_vs_12_opengl'] = compare_dirs(a,c)
if c.exists() and v.exists(): visuals['12_opengl_vs_12_vulkan'] = compare_dirs(c,v)

def load_json(name):
    p = root / name
    return json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else None

summary = {
    'environment': load_json('environment.json'),
    'vulkan': load_json('vulkan-status.json'),
    'frames': frames,
    'profiles': profiles,
    'visuals': visuals,
}
(root / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
