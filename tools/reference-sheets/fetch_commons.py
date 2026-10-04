"""Fetch candidate architectural references from Wikimedia Commons with licences.

Review material only: thumbnails land in out/reference/raw with a manifest of
author, licence and source page for every file. Nothing here ships.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "out" / "reference"
RAW = HERE / "raw"
UA = "SecondRite-reference-sheet/1.0 (https://github.com/JosephSerUSP/Second-Rite)"
OPEN = re.compile(r"^(CC0|Public domain|PD|CC BY(-SA)? [0-9.]+)", re.I)

QUERIES = {
    "island_fort_chapel": "Capela de Nossa Senhora do Baluarte Ilha de Moçambique",
    "cape_verde_rosario": "Igreja Nossa Senhora do Rosário Cidade Velha interior",
    "paraty_interior": "Paraty igreja interior nave",
    "azulejo_dado_nave": "capela interior azulejos silhar nave Portugal",
    "talha_dourada": "retábulo talha dourada capela-mor capela",
    "azores_interior": "igreja interior Açores nave azulejo",
    "goa_chapel": "chapel interior Old Goa",
    "macau_guia": "Capela de Nossa Senhora da Guia Macau interior",
    "wooden_ceiling": "forro de madeira igreja colonial interior",
    "side_door": "porta lateral igreja colonial cantaria",
    "holy_water_font": "pia de água benta igreja",
    "pews_side": "igreja colonial interior bancos nave lateral",
    "sao_tome": "São Tomé igreja interior",
    "madeira_chapel": "Capela do Corpo Santo Funchal",
    "olinda_interior": "Olinda igreja interior azulejos",
    # Second round, after reviewing the first: doors, exteriors, island interiors.
    "rosario_exterior": "Cidade Velha Igreja Nossa Senhora do Rosário",
    "mozambique_island": "Ilha de Moçambique igreja interior",
    "side_entrance": "igreja porta lateral Portugal",
    "ermida_interior": "ermida interior Portugal azulejos",
    "paraty_church": "Igreja de Santa Rita Paraty",
}


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def api(**params):
    params.update(format="json")
    return json.loads(get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)))


def strip(html):
    return re.sub(r"<[^>]+>", "", html or "").strip()


def main(per_query=6):
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = []
    for theme, query in QUERIES.items():
        found = api(action="query", generator="search", gsrsearch=f"filetype:bitmap {query}",
                    gsrnamespace=6, gsrlimit=per_query, prop="imageinfo",
                    iiprop="url|extmetadata|mime", iiurlwidth=640)
        pages = sorted((found.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
        for page in pages:
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata", {})
            licence = strip(meta.get("LicenseShortName", {}).get("value"))
            if info.get("mime") not in ("image/jpeg", "image/png") or not OPEN.match(licence):
                continue
            name = f"{theme}__{len([m for m in manifest if m['theme'] == theme]):02d}.jpg"
            try:
                (RAW / name).write_bytes(get(info["thumburl"]))
            except Exception as error:  # noqa: BLE001 - review fetch; skip a bad file
                print("skip", page["title"], error)
                continue
            manifest.append({"theme": theme, "file": name, "title": page["title"],
                             "page": info.get("descriptionurl"), "licence": licence,
                             "licenceUrl": strip(meta.get("LicenseUrl", {}).get("value")),
                             "author": strip(meta.get("Artist", {}).get("value"))[:120],
                             "description": strip(meta.get("ImageDescription", {}).get("value"))[:240]})
            time.sleep(0.3)
        print(theme, sum(1 for m in manifest if m["theme"] == theme))
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
