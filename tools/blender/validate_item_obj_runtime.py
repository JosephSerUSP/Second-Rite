"""Validate study OBJ outputs against the runtime's non-degenerate-face contract.

This intentionally mirrors the hard failure in engine/geometry/model.lua rather
than trusting Blender's exporter merely because it wrote a file successfully.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

EPSILON = 1e-10


def parse_index(token: str, vertex_count: int) -> int:
    raw = token.split("/", 1)[0]
    value = int(raw)
    if value == 0:
        raise ValueError("OBJ indices are 1-based; zero is invalid")
    return value - 1 if value > 0 else vertex_count + value


def cross_length(a, b, c):
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    return math.sqrt(sum(component * component for component in cross))


def validate(path: Path):
    vertices = []
    faces = []
    mtllibs = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if fields[0] == "v" and len(fields) >= 4:
            vertices.append(tuple(float(value) for value in fields[1:4]))
        elif fields[0] == "f":
            if len(fields) < 4:
                raise ValueError(f"{path}:{line_number}: face has fewer than three vertices")
            indices = [parse_index(token, len(vertices)) for token in fields[1:]]
            faces.append((line_number, indices))
        elif fields[0] == "mtllib" and len(fields) >= 2:
            mtllibs.append(" ".join(fields[1:]))

    if len(vertices) < 3 or not faces:
        raise ValueError(f"{path}: missing nontrivial geometry")

    triangles = 0
    for line_number, indices in faces:
        if any(index < 0 or index >= len(vertices) for index in indices):
            raise ValueError(f"{path}:{line_number}: face references out-of-range vertex")
        for i in range(1, len(indices) - 1):
            tri = (indices[0], indices[i], indices[i + 1])
            if len(set(tri)) != 3:
                raise ValueError(f"{path}:{line_number}: degenerate triangle repeats a vertex index: {tri}")
            area2 = cross_length(vertices[tri[0]], vertices[tri[1]], vertices[tri[2]])
            if area2 <= EPSILON:
                raise ValueError(
                    f"{path}:{line_number}: mesh contains a degenerate face; "
                    f"triangle={tri} cross_length={area2:.3e}"
                )
            triangles += 1

    for mtllib in mtllibs:
        if not (path.parent / mtllib).is_file():
            raise ValueError(f"{path}: referenced MTL does not exist: {mtllib}")

    print(f"RUNTIME OBJ OK {path}: vertices={len(vertices)} faces={len(faces)} triangles={triangles}")


def main(argv):
    if len(argv) < 2:
        raise SystemExit("usage: validate_item_obj_runtime.py <obj> [<obj> ...]")
    for value in argv[1:]:
        validate(Path(value))


if __name__ == "__main__":
    main(sys.argv)
