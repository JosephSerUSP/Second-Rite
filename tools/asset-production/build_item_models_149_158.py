#!/usr/bin/env python3
"""Build deterministic low-poly OBJ models for Second Rite items 149-158."""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "models" / "items"
MATERIALS = ROOT / "tools" / "asset-language" / "materials.json"
ITEMS_JSON = ROOT / "data" / "items.json"
MTL_NAME = "item_batch_149_158.mtl"
BATCH_COMMENT = "Second Rite deterministic item batch 149-158"
MATERIAL_IDS = (
    "smoked_glass",
    "crystal",
    "wax",
    "ritual_gold",
    "dark_wood",
    "aged_cloth",
)
ITEMS = {
    149: ("potion", "Potion"),
    150: ("hi_potion", "Hi-Potion"),
    151: ("x_potion", "X-Potion"),
    152: ("mega_potion", "Mega-Potion"),
    153: ("healing_water", "Healing Water"),
    154: ("soma", "Soma"),
    155: ("elixir", "Elixir"),
    156: ("ether", "Ether"),
    157: ("hi_ether", "Hi-Ether"),
    158: ("dry_ether", "Dry Ether"),
}


def add(a, b):
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]


def sub(a, b):
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def length(v):
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


class Mesh:
    def __init__(self, name):
        self.name = name
        self.vertices = []
        self.faces = []

    def vertex(self, point):
        self.vertices.append(tuple(round(value, 6) for value in point))
        return len(self.vertices)

    def triangle(self, material, a, b, c):
        pa, pb, pc = (self.vertices[index - 1] for index in (a, b, c))
        if length(cross(sub(pb, pa), sub(pc, pa))) < 1e-8:
            raise ValueError(f"degenerate face in {self.name}: {a} {b} {c}")
        self.faces.append((material, (a, b, c)))

    def ring(self, y, radius, *, z_offset=0.0, sides=8):
        return [
            self.vertex(
                (
                    radius * math.cos(2 * math.pi * index / sides),
                    y,
                    z_offset + radius * math.sin(2 * math.pi * index / sides),
                )
            )
            for index in range(sides)
        ]

    def connect(self, material, lower, upper):
        for index in range(len(lower)):
            nxt = (index + 1) % len(lower)
            self.triangle(material, lower[index], lower[nxt], upper[nxt])
            self.triangle(material, lower[index], upper[nxt], upper[index])

    def cap(self, material, ring, *, top):
        center = self.vertex(
            (
                0.0,
                sum(self.vertices[index - 1][1] for index in ring) / len(ring),
                sum(self.vertices[index - 1][2] for index in ring) / len(ring),
            )
        )
        for index in range(len(ring)):
            nxt = (index + 1) % len(ring)
            if top:
                self.triangle(material, center, ring[index], ring[nxt])
            else:
                self.triangle(material, center, ring[nxt], ring[index])

    def box(self, center, size, material):
        cx, cy, cz = center
        hx, hy, hz = (value / 2 for value in size)
        points = [
            (cx - hx, cy - hy, cz - hz),
            (cx + hx, cy - hy, cz - hz),
            (cx + hx, cy + hy, cz - hz),
            (cx - hx, cy + hy, cz - hz),
            (cx - hx, cy - hy, cz + hz),
            (cx + hx, cy - hy, cz + hz),
            (cx + hx, cy + hy, cz + hz),
            (cx - hx, cy + hy, cz + hz),
        ]
        vertices = [self.vertex(point) for point in points]
        for a, b, c, d in (
            (0, 3, 2, 1),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (3, 7, 6, 2),
            (0, 4, 7, 3),
            (1, 2, 6, 5),
        ):
            self.triangle(material, vertices[a], vertices[b], vertices[c])
            self.triangle(material, vertices[a], vertices[c], vertices[d])

    def center(self):
        low = [min(point[axis] for point in self.vertices) for axis in range(3)]
        high = [max(point[axis] for point in self.vertices) for axis in range(3)]
        center = [(low[axis] + high[axis]) / 2 for axis in range(3)]
        self.vertices = [
            tuple(round(point[axis] - center[axis], 6) for axis in range(3))
            for point in self.vertices
        ]


def bottle(stem, profile, *, glass="smoked_glass", cap="wax", sides=8, band=False, tag=False):
    mesh = Mesh(stem)
    rings = [mesh.ring(y, radius, sides=sides) for y, radius in profile]
    mesh.cap(glass, rings[0], top=False)
    for lower, upper in zip(rings, rings[1:]):
        mesh.connect(glass, lower, upper)
    mesh.cap(glass, rings[-1], top=True)

    cap_y = profile[-1][0] + 0.08
    cap_radius = profile[-1][1] * 1.18
    lower = mesh.ring(cap_y, cap_radius, sides=sides)
    upper = mesh.ring(cap_y + 0.16, cap_radius * 0.96, sides=sides)
    mesh.connect(cap, lower, upper)
    mesh.cap(cap, lower, top=False)
    mesh.cap(cap, upper, top=True)

    if band:
        y = (profile[1][0] + profile[-2][0]) / 2
        mesh.box(
            (0, y, profile[1][1] * 0.92),
            (profile[1][1] * 1.35, 0.10, 0.06),
            "ritual_gold",
        )
    if tag:
        mesh.box(
            (profile[1][1] * 0.78, profile[1][0] + 0.15, 0),
            (0.06, 0.34, 0.42),
            "aged_cloth",
        )

    mesh.center()
    return mesh


def models():
    return {
        149: bottle("potion", [(-0.85, 0.34), (-0.55, 0.46), (0.18, 0.46), (0.48, 0.28), (0.62, 0.18)]),
        150: bottle("hi_potion", [(-1.00, 0.30), (-0.72, 0.44), (0.38, 0.42), (0.72, 0.24), (0.88, 0.17)], cap="ritual_gold", band=True),
        151: bottle("x_potion", [(-0.82, 0.42), (-0.68, 0.50), (0.32, 0.50), (0.52, 0.34), (0.72, 0.18)], glass="crystal", sides=6, band=True),
        152: bottle("mega_potion", [(-1.08, 0.48), (-0.86, 0.62), (0.42, 0.58), (0.76, 0.34), (0.94, 0.22)], cap="ritual_gold", band=True, tag=True),
        153: bottle("healing_water", [(-0.88, 0.22), (-0.70, 0.38), (-0.10, 0.52), (0.42, 0.36), (0.68, 0.16)], glass="crystal"),
        154: bottle("soma", [(-0.94, 0.36), (-0.72, 0.58), (0.30, 0.58), (0.64, 0.30), (0.82, 0.18)], glass="crystal", cap="ritual_gold", sides=10, band=True),
        155: bottle("elixir", [(-1.02, 0.30), (-0.78, 0.44), (0.18, 0.54), (0.58, 0.30), (0.78, 0.16)], glass="crystal", cap="ritual_gold", sides=6, band=True, tag=True),
        156: bottle("ether", [(-1.04, 0.22), (-0.88, 0.30), (0.42, 0.30), (0.70, 0.18), (0.86, 0.12)]),
        157: bottle("hi_ether", [(-0.96, 0.30), (-0.72, 0.48), (0.22, 0.46), (0.64, 0.22), (0.82, 0.14)], glass="crystal", band=True),
        158: bottle("dry_ether", [(-0.86, 0.36), (-0.68, 0.46), (0.28, 0.42), (0.56, 0.26), (0.72, 0.14)], cap="dark_wood", sides=6, tag=True),
    }


def material_registry():
    data = json.loads(MATERIALS.read_text(encoding="utf-8"))
    registry = {
        material["id"]: tuple(material["legacyMtl"]["kd"])
        for material in data["materials"]
    }
    missing = [material for material in MATERIAL_IDS if material not in registry]
    if missing:
        raise ValueError(f"batch materials missing from canonical registry: {missing}")
    return {material: registry[material] for material in MATERIAL_IDS}


def write_mtl(materials):
    lines = [f"# Shared semantic materials for deterministic item batch 149-158"]
    for material in MATERIAL_IDS:
        r, g, b = materials[material]
        lines.extend((f"newmtl {material}", f"Kd {r:.3f} {g:.3f} {b:.3f}", ""))
    (OUT / MTL_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_obj(mesh, path, label, allowed_materials):
    used = []
    for material, _ in mesh.faces:
        if material not in used:
            used.append(material)
    missing = [material for material in used if material not in allowed_materials]
    if missing:
        raise ValueError(f"unregistered materials in {path.stem}: {missing}")

    lines = [
        f"# {BATCH_COMMENT}",
        f"# {label}",
        f"mtllib {MTL_NAME}",
        f"o {mesh.name}",
        "s off",
    ]
    lines.extend(
        f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in mesh.vertices
    )

    current = None
    for material, face in mesh.faces:
        if material != current:
            lines.append(f"usemtl {material}")
            current = material
        lines.append("f " + " ".join(map(str, face)))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_obj(path):
    vertices = []
    faces = []
    materials = []
    mtllib = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            vertices.append(tuple(map(float, line.split()[1:4])))
        elif line.startswith("f "):
            faces.append(tuple(int(part.split("/")[0]) for part in line.split()[1:]))
        elif line.startswith("usemtl "):
            materials.append(line.split(None, 1)[1])
        elif line.startswith("mtllib "):
            mtllib = line.split(None, 1)[1]

    if not vertices or not faces or mtllib != MTL_NAME:
        raise ValueError(f"incomplete or misbound OBJ: {path}")
    mtl_path = path.with_name(mtllib)
    if not mtl_path.is_file():
        raise ValueError(f"missing MTL for {path}: {mtl_path}")
    declared = {
        line.split(None, 1)[1]
        for line in mtl_path.read_text(encoding="utf-8").splitlines()
        if line.startswith("newmtl ")
    }
    if not set(materials) <= declared:
        raise ValueError(f"undeclared material in {path}")

    for face in faces:
        if len(face) != 3 or min(face) < 1 or max(face) > len(vertices):
            raise ValueError(f"bad face in {path}: {face}")
        a, b, c = (vertices[index - 1] for index in face)
        if length(cross(sub(b, a), sub(c, a))) < 1e-8:
            raise ValueError(f"degenerate triangle in {path}: {face}")

    low = [min(vertex[axis] for vertex in vertices) for axis in range(3)]
    high = [max(vertex[axis] for vertex in vertices) for axis in range(3)]
    center = [(low[axis] + high[axis]) / 2 for axis in range(3)]
    if max(abs(value) for value in center) > 1e-5:
        raise ValueError(f"off-center bounds in {path}: {center}")
    if any(high[axis] - low[axis] <= 1e-5 for axis in range(3)):
        raise ValueError(f"zero-size bounds in {path}")

    return {
        "vertices": len(vertices),
        "triangles": len(faces),
        "materials": sorted(set(materials)),
        "bounds": [low, high],
    }


def patch_items():
    data = json.loads(ITEMS_JSON.read_text(encoding="utf-8"))
    by_id = {item.get("id"): item for item in data}
    for item_id, (stem, _label) in ITEMS.items():
        item = by_id.get(item_id)
        if item is None:
            raise ValueError(f"missing item {item_id}")
        target = f"assets/models/items/{stem}.obj"
        if item.get("model") not in (None, target):
            raise ValueError(
                f"item {item_id} already has a different model: {item.get('model')}"
            )
        item["model"] = target
    ITEMS_JSON.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    materials = material_registry()
    write_mtl(materials)
    report = {}
    built = models()
    for item_id, (stem, label) in ITEMS.items():
        mesh = built[item_id]
        path = OUT / f"{stem}.obj"
        write_obj(mesh, path, label, materials)
        report[str(item_id)] = {
            "name": label,
            "model": f"assets/models/items/{stem}.obj",
            **validate_obj(path),
        }
    patch_items()
    print(json.dumps({"ok": True, "items": report, "itemsJsonPatched": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
