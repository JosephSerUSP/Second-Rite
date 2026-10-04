"""Compose the chapel reference sheet from reviewed Commons picks."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "out" / "reference"
MANIFEST = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))

GROUPS = [
    ("THE MODEL ROOM - Nossa Senhora do Rosario, Cidade Velha, Cape Verde (1495)", [
        (57, "Nave: limewash, azulejo dado, timber roof, red carpet, pews both sides"),
        (9, "Altar end: one step across the nave, side altars, tile to the sill"),
        (53, "Outside: limewash over stone quoins, buttress, arched side door"),
        (52, "Side door in the long wall: stone frame in whitewash"),
    ]),
    ("CAMERA - oblique across the pews, not square to the aisle", [
        (8, "Rosario from a corner: pews cut the foreground diagonally"),
        (70, "Remedios, Peniche: pews in front, tall tile panel beyond"),
        (44, "Sesimbra: carpet aisle leading the eye to the altar"),
        (40, "Rans: carpet + gilt retable as the far focal point"),
    ]),
    ("DOORS - the way out is a door in the far wall", [
        (61, "Sardoal: round-arched stone frame, dark panelled leaves"),
        (63, "Elvas: carved limestone surround, worn threshold"),
        (60, "Carmo: carved panelled leaves in a tiled surround"),
        (64, "Almoster: side door in the long wall, set deep"),
    ]),
    ("ALTAR AND FURNISHING", [
        (16, "Talha dourada retable: gilt frame round a dark centre"),
        (15, "Side altar: retable over an azulejo dado"),
        (37, "Holy-water font on a turned column (Salvador, Brazil)"),
        (35, "Wall font with a shell back"),
    ]),
    ("ISLAND CHAPELS - scale, wear and colour", [
        (0, "Baluarte, Ilha de Mocambique: small, weathered, island light"),
        (58, "Santo Antonio, Ilha de Mocambique: blue apse, white nave"),
        (66, "Ermida da Memoria, Nazare: tile to the vault in a tiny chapel"),
        (32, "Guia, Macau: vault and door seen from within"),
    ]),
    ("THE CHAPEL ON ITS SQUARE", [
        (46, "Corpo Santo, Funchal: fishermen's chapel on an island square"),
        (69, "Ermida de Sao Juliao: white chapel above the sea"),
    ]),
]

CELL_W, CELL_H, COLS, PAD = 400, 270, 4, 10
CAPTION = 34
font = ImageFont.load_default()


def main():
    rows = sum(1 + (len(items) + COLS - 1) // COLS for _, items in GROUPS)
    height = 60 + sum(28 + ((len(items) + COLS - 1) // COLS) * (CELL_H + CAPTION + PAD) for _, items in GROUPS) + 40
    sheet = Image.new("RGB", (COLS * (CELL_W + PAD) + PAD, height), (24, 22, 20))
    draw = ImageDraw.Draw(sheet)
    draw.text((PAD, 14), "St. Maria Chapel - architectural references (Wikimedia Commons; credits in "
              "docs/design/references/st-maria-chapel.md)", fill=(240, 232, 200), font=font)
    y = 50
    number = 1
    for title, items in GROUPS:
        draw.text((PAD, y), title, fill=(230, 190, 110), font=font)
        y += 24
        for index, (pick, caption) in enumerate(items):
            col = index % COLS
            if index and col == 0:
                y += CELL_H + CAPTION + PAD
            x = PAD + col * (CELL_W + PAD)
            entry = MANIFEST[pick]
            image = Image.open(HERE / "raw" / entry["file"]).convert("RGB")
            image.thumbnail((CELL_W, CELL_H))
            sheet.paste(image, (x + (CELL_W - image.width) // 2, y + (CELL_H - image.height) // 2))
            draw.text((x, y + CELL_H + 4), f"{number}. {caption}", fill=(235, 235, 235), font=font)
            draw.text((x, y + CELL_H + 18), f"{entry['licence']} - {entry['author'][:44] or 'see source'}",
                      fill=(150, 150, 150), font=font)
            entry["sheetNumber"] = number
            entry["caption"] = caption
            entry["group"] = title
            number += 1
        y += CELL_H + CAPTION + PAD + 8
    sheet = sheet.crop((0, 0, sheet.width, y + 10))
    sheet.save(HERE / "st_maria_chapel_references.png")
    picks = [MANIFEST[p] for _, items in GROUPS for p, _ in items]
    (HERE / "picks.json").write_text(json.dumps(picks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(sheet.size, len(picks))


if __name__ == "__main__":
    main()
