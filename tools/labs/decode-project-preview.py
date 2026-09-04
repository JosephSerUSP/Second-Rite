#!/usr/bin/env python3
"""Decode one Thestra PREVIEW payload into a disposable review PNG.

Lab review captures are human-inspection evidence, not G5 golden references.
The input is the stdout produced by `lovec . preview-scene ...` or
`lovec . preview-map ...`.
"""

import argparse
import base64
import json
import pathlib

BEGIN = "PREVIEW BEGIN"
END = "PREVIEW END"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    text = pathlib.Path(args.input).read_text(encoding="utf-8", errors="replace")
    try:
        start = text.index(BEGIN) + len(BEGIN)
        end = text.index(END)
    except ValueError:
        raise SystemExit("decode-project-preview: no PREVIEW BEGIN/END payload; inspect runtime output")

    payload = json.loads(text[start:end].strip())
    if payload.get("error"):
        raise SystemExit(f"decode-project-preview: runtime preview error: {payload['error']}")
    if payload.get("imageError"):
        raise SystemExit(f"decode-project-preview: image render error: {payload['imageError']}")
    image = payload.get("image")
    if not image:
        raise SystemExit("decode-project-preview: preview produced no image")

    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base64.b64decode(image))
    meta = output.with_suffix(output.suffix + ".json")
    meta.write_text(json.dumps({k: v for k, v in payload.items() if k != "image"}, indent=2) + "\n", encoding="utf-8")
    print(f"LAB PREVIEW OK -> {output}")


if __name__ == "__main__":
    main()
