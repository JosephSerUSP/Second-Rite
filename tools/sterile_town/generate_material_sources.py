import os, json, urllib.request, hashlib
from pathlib import Path

out_dir = Path('tools/sterile_town/materials/sources')
out_dir.mkdir(parents=True, exist_ok=True)

api_key = os.environ.get('OPENAI_API_KEY')

prompts = {
    'stone_ashlar_albedo': 'Flat seamless orthographic texture of weathered medieval stone ashlar wall blocks, aged sandstone and limestone masonry with subtle mortar grooves, completely even neutral studio lighting, no shadows, no perspective, top-down albedo map for 3D PBR texturing.',
    'timber_planks_albedo': 'Flat seamless orthographic texture of weathered dark oak timber planks, aged medieval wood beams and panels with subtle woodgrain, completely even neutral lighting, no harsh shadows, no perspective, top-down albedo map for 3D PBR texturing.',
    'terracotta_tiles_albedo': 'Flat seamless orthographic texture of aged medieval terracotta roof tiles, weathered clay shingles with subtle patina and moss traces, completely even neutral diffuse lighting, no shadows, no perspective, albedo map for 3D PBR.',
    'cobblestone_street_albedo': 'Flat seamless orthographic texture of weathered medieval cobblestone street paving, irregular rounded stone slabs with packed earth mortar, completely even neutral lighting, no shadows, no perspective, top-down albedo map for 3D texturing.'
}

manifest = {}

for name, p in prompts.items():
    print(f'Generating {name}...')
    body = {
        'model': 'dall-e-3',
        'prompt': p,
        'n': 1,
        'size': '1024x1024',
        'quality': 'standard'
    }
    req = urllib.request.Request(
        'https://api.openai.com/v1/images/generations',
        data=json.dumps(body).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        img_url = res['data'][0]['url']
        
    img_path = out_dir / f'{name}.png'
    with urllib.request.urlopen(img_url) as img_resp:
        data = img_resp.read()
        img_path.write_bytes(data)
        
    sha256 = hashlib.sha256(data).hexdigest()
    manifest[name] = {
        'file': str(img_path),
        'sha256': sha256,
        'prompt': p,
        'model': 'dall-e-3',
        'size': '1024x1024',
        'usage': 'Albedo source for procedural PBR material node network'
    }
    print(f'Saved {name}.png ({len(data)} bytes, sha256: {sha256[:12]}...)')

(out_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('Material sources generated and manifest saved.')
