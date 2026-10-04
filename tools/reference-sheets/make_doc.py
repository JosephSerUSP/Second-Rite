"""Write docs/design/references/st-maria-chapel.md from the reviewed picks (make_sheet.py first)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "out" / "reference"
picks = json.loads((HERE / "picks.json").read_text(encoding="utf-8"))

INTRO = """# St. Maria Chapel: architectural references

Reference for authoring Sister Agnes's chapel (`tools/blender/recipes/st_maria_chapel.py`)
and any small St. Maria church: a limewashed colonial Portuguese chapel on an island
town square. Every image is on Wikimedia Commons under the licence listed; follow the
link for the full-size file and its terms. The composite contact sheet is a review
artefact regenerated into `out/reference/` and is not committed:

```text
python tools/reference-sheets/fetch_commons.py   # licensed candidates + manifest
python tools/reference-sheets/make_sheet.py      # out/reference/st_maria_chapel_references.png
python tools/reference-sheets/make_doc.py        # this file
```

## What the references say about this chapel

- **The model room is Nossa Senhora do Rosario, Cidade Velha (Cape Verde, 1495)**, the
  oldest colonial church in the tropics and an island church: limewashed walls, an
  azulejo dado to the window sills, pews in two banks, a red carpet down the aisle,
  one step across the nave at the altar end (1-2). The St. Maria chapel follows it.
- **The roof is pitched timber, not a flat beamed ceiling** (1, 2, 5). `Interior.ceiling`
  can only build a flat ceiling with beams; a pitched roof is a missing axis.
- **The carpet is red** in every nave that has one (1, 7, 8). The material registry has
  no red cloth, so the chapel's runner uses `aged_cloth` with a terracotta border.
- **The way out is a door in the long wall** (3, 4, 12): an arched opening in a stone
  frame, set into thick limewash, with dark panelled leaves (9-11). The chapel's door is
  in the far wall; its frame is still plain.
- **Seen from a corner, the pews cut the foreground on a diagonal** (5, 6). That is the
  camera this room is reviewed with: yawed off the aisle, not square to it.
- **Gilt is a frame, not a surface** (13, 14): a dark centre inside gold carving. The
  `altar` retable does this; its recess is still empty by design.
- **Fonts stand by the door**, on a turned column or let into the wall (15, 16).
- **Island chapels are small and worn** (17, 18): salt-stained limewash, blue in the
  apse, light from few openings.

## Credits

| # | Teaches | Source | Author | Licence |
|---|---|---|---|---|
"""


def main():
    lines = [INTRO.rstrip("\n")]
    for entry in picks:
        title = entry["title"].removeprefix("File:")
        author = (entry["author"] or "see source").replace("|", "/")
        lines.append(f"| {entry['sheetNumber']} | {entry['caption']} | [{title}]({entry['page']}) | "
                     f"{author} | {entry['licence']} |")
    lines.append("")
    target = ROOT / "docs" / "design" / "references" / "st-maria-chapel.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
