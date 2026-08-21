"""Fresh material-source acquisition for the clean-room gauntlet.

Two external sources, both acquired *during this task*:

  public    -- Poly Haven, CC0-1.0, verified at https://polyhaven.com/license
               on 2026-08-20 (commercial use and redistribution permitted,
               attribution optional). Candidates were chosen by querying the
               live asset index, not by reading any stored asset list.

  generated -- gpt-image-2, asked for ONE flat, evenly lit, tileable albedo
               per material. Height/roughness/AO are derived numerically
               (see derive.py). No generated normal map is ever used.

Everything lands in a temporary workspace. Only the sources the winning scene
actually needs get promoted into the repository.
"""
from __future__ import annotations

import base64
import concurrent.futures as futures
import hashlib
import io
import json
import os
import time
from datetime import date
from pathlib import Path

import requests
from PIL import Image

PH_API = "https://api.polyhaven.com"
PH_LICENSE = "CC0-1.0"
PH_LICENSE_URL = "https://polyhaven.com/license"
RETRIEVED = date.today().isoformat()

# Source maps are stored small on purpose: the render target is 426x240 and
# these textures exist only to feed a bake. A 2K set pushes the scene into CPU
# fallback for no visible gain.
SOURCE_PX = 512


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# public library
# --------------------------------------------------------------------------

def ph_search(terms, *, limit=40):
    """Live query against the public index; returns (slug, tags) candidates."""
    assets = requests.get(PH_API + "/assets?t=textures", timeout=90).json()
    out = []
    for slug, meta in assets.items():
        blob = (slug + " " + " ".join(meta.get("tags", []))
                + " " + " ".join(meta.get("categories", []))).lower()
        if any(t in blob for t in terms):
            out.append((slug, meta.get("name", slug), meta.get("tags", [])))
    return sorted(out)[:limit]


def _download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, timeout=300, stream=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
    return dest


def _downsample(path, px=SOURCE_PX, grayscale=False):
    img = Image.open(path)
    img = img.convert("L" if grayscale else "RGB")
    if img.size != (px, px):
        img = img.resize((px, px), Image.LANCZOS)
    out = path.with_suffix(".png")
    img.save(out)
    if out != path:
        path.unlink(missing_ok=True)
    return out


def fetch_polyhaven(slug, out_dir, *, res="1k", maps=("Diffuse", "Rough", "Displacement", "AO")):
    out_dir = Path(out_dir) / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    info = requests.get(PH_API + "/info/" + slug, timeout=90).json()
    files = requests.get(PH_API + "/files/" + slug, timeout=90).json()
    record = {
        "id": slug,
        "name": info.get("name", slug),
        "library": "Poly Haven",
        "sourceUrl": "https://polyhaven.com/a/" + slug,
        "apiUrl": PH_API + "/files/" + slug,
        "license": PH_LICENSE,
        "licenseUrl": PH_LICENSE_URL,
        "licenseVerified": RETRIEVED,
        "authors": info.get("authors", {}),
        "retrieved": RETRIEVED,
        "downloadedResolution": res,
        "storedResolution": "%dx%d" % (SOURCE_PX, SOURCE_PX),
        "scaleMetres": info.get("scale"),
        "dimensions": info.get("dimensions"),
        "files": {},
    }
    key_for = {"Diffuse": "albedo", "Rough": "roughness",
               "Displacement": "height", "AO": "ao"}
    paths = {}
    for m in maps:
        node = files.get(m)
        if not node or res not in node:
            continue
        fmt = "jpg" if "jpg" in node[res] else "png"
        url = node[res][fmt]["url"]
        raw = out_dir / ("%s_%s.%s" % (slug, key_for[m], fmt))
        _download(url, raw)
        final = _downsample(raw, grayscale=(m != "Diffuse"))
        paths[key_for[m]] = str(final)
        record["files"][key_for[m]] = {
            "file": final.name,
            "remote": url,
            "sha256": sha256(final),
            "bytes": final.stat().st_size,
        }
    record["paths"] = paths
    (out_dir / "provenance.json").write_text(json.dumps(record, indent=2),
                                             encoding="utf-8")
    return paths, record


# --------------------------------------------------------------------------
# generated
# --------------------------------------------------------------------------

FLAT_ALBEDO_RULES = (
    "This is a MATERIAL ALBEDO SOURCE, not a picture and not a render. "
    "Absolutely flat, perfectly even, shadowless, directionless illumination "
    "across the whole square. No light source, no highlight, no vignette, no "
    "gradient from any edge, no drop shadow, no ambient occlusion, no depth of "
    "field, no perspective. Photographed dead-on, orthographic, filling the "
    "frame edge to edge. Seamlessly tileable. No object, no border, no frame, "
    "no text, no watermark, no logo. Colour and small-scale surface detail only."
)


def generate_albedo(prompt, out_path, *, model="gpt-image-2", size="1024x1024",
                    api_key=None, retries=3):
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "model": model,
        "prompt": prompt + "\n\n" + FLAT_ALBEDO_RULES,
        "size": size,
        "n": 1,
    }
    last = None
    for attempt in range(retries):
        try:
            r = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": "Bearer " + api_key,
                         "Content-Type": "application/json"},
                json=body, timeout=600)
            if r.status_code != 200:
                last = "%s %s" % (r.status_code, r.text[:400])
                time.sleep(4 * (attempt + 1))
                continue
            payload = r.json()["data"][0]
            if payload.get("b64_json"):
                raw = base64.b64decode(payload["b64_json"])
            else:
                raw = requests.get(payload["url"], timeout=300).content
            Image.open(io.BytesIO(raw)).convert("RGB").save(out_path)
            return out_path
        except Exception as exc:  # network flake
            last = repr(exc)
            time.sleep(4 * (attempt + 1))
    raise RuntimeError("image generation failed: %s" % last)


def generate_many(specs, out_dir, *, workers=4, model="gpt-image-2"):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = {
            pool.submit(generate_albedo, spec["prompt"],
                        out_dir / (spec["id"] + "_raw.png"), model=model): spec
            for spec in specs
        }
        for job in futures.as_completed(jobs):
            spec = jobs[job]
            try:
                results[spec["id"]] = {"raw": str(job.result()), "spec": spec}
            except Exception as exc:
                results[spec["id"]] = {"error": str(exc), "spec": spec}
    return results
