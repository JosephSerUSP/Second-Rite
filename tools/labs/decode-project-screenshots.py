#!/usr/bin/env python3
"""Decode `lovec . screenshots` output for disposable lab-review artifacts.

This deliberately does not compare against or write G5 references. Lab captures
are evidence for human review of a candidate game, not owner-approved visual
baselines.
"""

import argparse
import base64
import json
import os
import pathlib
import sys

BEGIN = "SCREENSHOTS BEGIN"
END = "SCREENSHOTS END"


def extract_payload(text: str):
    try:
        start = text.index(BEGIN) + len(BEGIN)
        end = text.index(END)
    except ValueError:
        raise SystemExit(
            "decode-project-screenshots: no SCREENSHOTS BEGIN/END block; "
            "inspect the runtime output for a crash"
        )
    payload = json.loads(text[start:end].strip())
    if payload.get("error"):
        raise SystemExit(f"decode-project-screenshots: harness error: {payload['error']}")
    captures = payload.get("captures") or []
    if not captures:
        raise SystemExit("decode-project-screenshots: runtime produced no captures")
    return captures


def safe_relpath(value: str):
    norm = os.path.normpath(str(value)).replace("\\", "/")
    if norm.startswith("/") or norm.startswith("..") or ":" in norm:
        raise SystemExit(f"decode-project-screenshots: unsafe capture path: {value}")
    return norm


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--project", required=True)
    args = parser.parse_args()

    text = pathlib.Path(args.input).read_text(encoding="utf-8", errors="replace")
    captures = extract_payload(text)
    output = pathlib.Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    manifest = []
    for capture in captures:
        rel = safe_relpath(capture["path"])
        dest = output / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base64.b64decode(capture["image"]))
        manifest.append({
            "path": rel,
            "width": capture.get("width"),
            "height": capture.get("height"),
        })

    (output / "manifest.json").write_text(
        json.dumps({"project": args.project, "captures": manifest}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"LAB SCREENSHOTS OK {args.project}: {len(manifest)} captures -> {output}")


if __name__ == "__main__":
    main()
