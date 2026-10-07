"""Draw original 8px pictograms for the engine's existing system icon atlas.

These are authored pixel patterns, not extracted Parasite Eve artwork.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
PATTERNS = [
    ['.######.', '.#....#.', '.######.', '........', '.######.', '.#..#.#.', '.######.', '........'],
    ['.##.###.', '.#..#...', '.##.##..', '.#..#...', '.#..###.', '........', '.#####..', '.#####..'],
    ['........', '.######.', '.#####..', '....##..', '....#...', '...##...', '...##...', '........'],
    ['........', '......#.', '.....##.', '....##..', '...##...', '..##....', '.##.....', '........'],
    ['.#....#.', '.##..##.', '.######.', '.##..##.', '.##..##.', '.######.', '.######.', '........'],
    ['..####..', '...##...', '..####..', '.######.', '.##..##.', '.##..##.', '.######.', '..####..'],
    ['........', '.######.', '.##..##.', '.######.', '.#....#.', '.######.', '.######.', '........'],
    ['.###....', '.#.#....', '.###....', '...#....', '...####.', '...#.#..', '........', '........'],
    ['..####..', '.##..##.', '.#.#..#.', '.#..#.#.', '.#.#..#.', '.##..##.', '..####..', '........'],
]

def main():
    image = Image.new('RGBA', (80, 8))
    for i, pattern in enumerate(PATTERNS):
        for y, row in enumerate(pattern):
            for x, pixel in enumerate(row):
                if pixel == '#': image.putpixel((i * 8 + x, y), (208, 208, 208, 255))
    out = ROOT / 'projects/pe-day1/assets/system/iconset.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    print('wrote', out)

if __name__ == '__main__':
    main()
