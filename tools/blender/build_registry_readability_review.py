"""Pair native before/after frames with isolated source-shape inspections."""
import argparse,html,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--before',required=True);p.add_argument('--after',required=True)
    p.add_argument('--parts',required=True)
    p.add_argument('--window-review',nargs='*',default=[])
    p.add_argument('--context-review',nargs='*',default=[])
    p.add_argument('--filename',default='readability.html')
    a=p.parse_args()
    if Path(a.filename).name!=a.filename or not a.filename.endswith('.html'):
        p.error('Review filename must be a local HTML basename')
    destination=a.root/a.after/a.filename
    if destination.exists():p.error('Preserve previous reviews')
    parts=json.loads((a.root/a.parts/'parts.json').read_text())['parts']
    page=['<!doctype html><meta charset=utf-8><title>Registry readability</title>',
      '<style>body{background:#171719;color:#eee;font:16px system-ui;margin:24px}section{display:flex;gap:24px;flex-wrap:wrap}figure{margin:8px 0}img{image-rendering:pixelated;max-width:100%}.native img{width:auto}.zoom img{height:480px}.parts img{width:384px}figcaption{margin:8px 0}p{max-width:950px}</style>',
      '<h1>Registry: shapes and game-scale readability</h1><p>Native frames retain their original pixels. The second row enlarges the same frames with nearest-neighbour display. Source closeups inspect geometry and materials under neutral lights; they do not prove runtime visibility.</p>']
    for surface in ('classic','wide','device'):
        page.append('<h2>'+surface+'</h2>')
        for css in ('native','zoom'):
            page.append('<section class='+css+'>')
            for revision,label in ((a.before,'Previous'),(a.after,'Revised')):
                page.append(f'<figure><img src=../{revision}/review/world/{surface}/3.8833.png><figcaption>{label}: {css}</figcaption></figure>')
            page.append('</section>')
    page.append('<h2>Individual source shapes</h2><p>Each source object is isolated here; its relationship to the room is assessed in the native frames above.</p>')
    for row in parts:
        size=row.get('nativeProjectedSize')
        page.append('<h3>'+html.escape(row['name'])+'</h3>')
        if size:page.append(f'<p>Classic projected bounds: {size[0]:.1f} x {size[1]:.1f} pixels. This includes occluded geometry and is not a visible-pixel count.</p>')
        page.append('<section class=parts>')
        for view in row['views']:
            page.append(f'<figure><img src=../{a.parts}/{view}><figcaption>{html.escape(view)}</figcaption></figure>')
        page.append('</section>')
    for directory in a.window_review:
        page.append('<h2>Window: inside and outside</h2><p>One physical assembly viewed from both sides. External shutters swing outward, glazed casements inward, behind the fixed grille. This is a source assembly inspection, not a claim that the shipping exterior facade has been updated.</p>')
        for row in json.loads((a.root/directory/'parts.json').read_text())['parts']:
            page.append('<section class=parts>')
            for view in row['views']:
                page.append(f'<figure><img src=../{directory}/{view}><figcaption>{html.escape(view)}</figcaption></figure>')
            page.append('</section>')
    for directory in a.context_review:
        record=json.loads((a.root/directory/'parts.json').read_text())
        page.append('<h2>Construction junctions</h2><p>Context meshes retained: '+html.escape(', '.join(record.get('companions',[])))+'. Studio lighting diagnoses the fit; native room views establish the game presentation.</p>')
        for row in record['parts']:
            page.append('<section class=parts>')
            for view in row['views']:
                page.append(f'<figure><img src=../{directory}/{view}><figcaption>{html.escape(view)}</figcaption></figure>')
            page.append('</section>')
    page.append('<p><a href=review.html>Full four-surface source/native/UI review</a></p>')
    destination.write_text(''.join(page),encoding='utf-8');print(destination)

if __name__=='__main__':main()
