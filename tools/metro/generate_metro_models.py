# tools/metro/generate_metro_models.py
"""
Generates 3D OBJ/MTL models for Stratum III:
- metro_rails (East-West depressed track trench, ballast, ties, steel rails)
- metro_rails_ns (North-South variant)
- metro_column (reinforced concrete station column with fluted shaft and capital)
- metro_wagon (center, lead, and rear cars with animated door states and line-specific livery stripes)
"""

import os
import sys

def w2o(wx, wy, wz):
    # Thestra engine coordinates: world_x = obj_x, world_y = -obj_z, world_z = obj_y
    return (wx, wz, -wy)

class ObjBuilder:
    def __init__(self, mtllib_name):
        self.mtllib = mtllib_name
        self.verts = []
        self.normals = []
        self.groups = []
        self.cur_mtl = None
        self.cur_faces = []

    def set_mtl(self, mtl):
        if self.cur_mtl != mtl:
            if self.cur_faces:
                self.groups.append((self.cur_mtl, self.cur_faces))
                self.cur_faces = []
            self.cur_mtl = mtl

    def add_box(self, x1, y1, z1, x2, y2, z2, mtl):
        self.set_mtl(mtl)
        corners = [
            (x1, y1, z1), (x2, y1, z1), (x2, y2, z1), (x1, y2, z1),
            (x1, y1, z2), (x2, y1, z2), (x2, y2, z2), (x1, y2, z2),
        ]
        base_v = len(self.verts) + 1
        for c in corners:
            self.verts.append(w2o(*c))

        self.add_quad(base_v+0, base_v+3, base_v+2, base_v+1, (0, 0, -1))
        self.add_quad(base_v+4, base_v+5, base_v+6, base_v+7, (0, 0, 1))
        self.add_quad(base_v+2, base_v+3, base_v+7, base_v+6, (0, 1, 0))
        self.add_quad(base_v+0, base_v+1, base_v+5, base_v+4, (0, -1, 0))
        self.add_quad(base_v+0, base_v+4, base_v+7, base_v+3, (-1, 0, 0))
        self.add_quad(base_v+1, base_v+2, base_v+6, base_v+5, (1, 0, 0))

    def add_quad(self, v1, v2, v3, v4, world_n):
        norm_idx = len(self.normals) + 1
        self.normals.append(w2o(*world_n))
        self.cur_faces.append((v1, v2, v3, norm_idx))
        self.cur_faces.append((v1, v3, v4, norm_idx))

    def add_plane_face(self, p1, p2, p3, p4, world_n, mtl):
        self.set_mtl(mtl)
        base_v = len(self.verts) + 1
        for p in (p1, p2, p3, p4):
            self.verts.append(w2o(*p))
        norm_idx = len(self.normals) + 1
        self.normals.append(w2o(*world_n))
        self.cur_faces.append((base_v, base_v+1, base_v+2, norm_idx))
        self.cur_faces.append((base_v, base_v+2, base_v+3, norm_idx))

    def write(self, filepath):
        if self.cur_faces:
            self.groups.append((self.cur_mtl, self.cur_faces))
            self.cur_faces = []
        with open(filepath, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"# Generated Model\nmtllib {self.mtllib}\n")
            for v in self.verts:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            for n in self.normals:
                f.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")
            for mtl, faces in self.groups:
                f.write(f"usemtl {mtl}\n")
                for f1, f2, f3, ni in faces:
                    f.write(f"f {f1}//{ni} {f2}//{ni} {f3}//{ni}\n")

def generate_rails(out_dir):
    b = ObjBuilder("metro_rails.mtl")
    b.add_plane_face((-0.5, -0.5, -0.50), (0.5, -0.5, -0.50), (0.5, 0.5, -0.50), (-0.5, 0.5, -0.50), (0, 0, 1), "rail_ballast")
    b.add_plane_face((-0.5, -0.5, -0.50), (-0.5, -0.5, 0.00), (0.5, -0.5, 0.00), (0.5, -0.5, -0.50), (0, 1, 0), "platform_curb")
    b.add_plane_face((0.5, 0.5, -0.50), (0.5, 0.5, 0.00), (-0.5, 0.5, 0.00), (-0.5, 0.5, -0.50), (0, -1, 0), "platform_curb")
    for x in (-0.33, 0.0, 0.33):
        b.add_box(x - 0.08, -0.38, -0.50, x + 0.08, 0.38, -0.44, "rail_tie")
    # North Rail
    b.add_box(-0.5, -0.26, -0.44, 0.5, -0.18, -0.42, "rail_steel")
    b.add_box(-0.5, -0.23, -0.42, 0.5, -0.21, -0.38, "rail_steel")
    b.add_box(-0.5, -0.245, -0.38, 0.5, -0.195, -0.35, "rail_steel")
    # South Rail
    b.add_box(-0.5, 0.18, -0.44, 0.5, 0.26, -0.42, "rail_steel")
    b.add_box(-0.5, 0.21, -0.42, 0.5, 0.23, -0.38, "rail_steel")
    b.add_box(-0.5, 0.195, -0.38, 0.5, 0.245, -0.35, "rail_steel")
    b.write(os.path.join(out_dir, "metro_rails.obj"))

    with open(os.path.join(out_dir, "metro_rails.mtl"), "w", encoding="utf-8", newline="\n") as f:
        f.write("""# Metro Rail Bed Materials
newmtl rail_steel
Kd 0.78 0.82 0.86

newmtl rail_tie
Kd 0.28 0.24 0.20

newmtl rail_ballast
Kd 0.16 0.15 0.15

newmtl platform_curb
Kd 0.48 0.48 0.50
""")

def generate_column(out_dir):
    b = ObjBuilder("metro_column.mtl")
    b.add_box(-0.35, -0.35, 0.00, 0.35, 0.35, 0.15, "pillar_base")
    b.add_box(-0.30, -0.30, 0.15, 0.30, 0.30, 0.90, "concrete_pillar")
    b.add_box(-0.38, -0.38, 0.90, 0.38, 0.38, 1.00, "pillar_base")
    b.write(os.path.join(out_dir, "metro_column.obj"))

    with open(os.path.join(out_dir, "metro_column.mtl"), "w", encoding="utf-8", newline="\n") as f:
        f.write("""# Metro Platform Architectural Pillar
newmtl concrete_pillar
Kd 0.68 0.70 0.72

newmtl pillar_base
Kd 0.30 0.32 0.35
""")

def generate_wagon_model(out_dir, variant="center", door_mode="open", line_suffix="", mtl_name="metro_wagon.mtl"):
    b = ObjBuilder(mtl_name)

    # Bogies
    for bx in (-1.0, 1.0):
        b.add_box(bx - 0.28, -0.32, -0.32, bx + 0.28, 0.32, -0.20, "bogie_dark")
        b.add_box(bx - 0.20, -0.25, -0.35, bx - 0.05, -0.19, -0.15, "wheel_steel")
        b.add_box(bx + 0.05, -0.25, -0.35, bx + 0.20, -0.19, -0.15, "wheel_steel")
        b.add_box(bx - 0.20,  0.19, -0.35, bx - 0.05,  0.25, -0.15, "wheel_steel")
        b.add_box(bx + 0.05,  0.19, -0.35, bx + 0.20,  0.25, -0.15, "wheel_steel")

    # Lower skirt & floor
    b.add_box(-1.48, -0.42, -0.10, 1.48, 0.42, 0.00, "bogie_dark")
    b.add_box(-1.48, -0.42, 0.00, 1.48, 0.42, 0.03, "floor_mat")

    stripe_mat = "stripe_accent" if "l" in line_suffix else "stripe_blue"
    seat_mat = "seat_accent" if "l" in line_suffix else "seat_blue"

    b.add_box(-1.48, 0.40, 0.03, 1.48, 0.44, 0.12, stripe_mat)
    b.add_box(-1.48, -0.44, 0.03, -0.45, -0.40, 0.12, stripe_mat)
    b.add_box( 0.45, -0.44, 0.03,  1.48, -0.40, 0.12, stripe_mat)

    # Lower walls
    b.add_box(-1.48, 0.40, 0.12, 1.48, 0.44, 0.38, "car_exterior")
    b.add_box(-1.48, -0.44, 0.12, -0.45, -0.40, 0.38, "car_exterior")
    b.add_box( 0.45, -0.44, 0.12,  1.48, -0.40, 0.38, "car_exterior")

    # Window sills
    b.add_box(-1.48, 0.39, 0.38, 1.48, 0.43, 0.40, "car_exterior")
    b.add_box(-1.48, -0.43, 0.38, -0.45, -0.39, 0.40, "car_exterior")
    b.add_box( 0.45, -0.43, 0.38,  1.48, -0.39, 0.40, "car_exterior")

    # Window posts (transparent apertures)
    for wx in (-1.48, -1.02, -0.98, -0.48):
        b.add_box(wx, -0.44, 0.40, wx + 0.04, -0.40, 0.70, "car_exterior")
    for wx in (0.45, 0.98, 1.02, 1.44):
        b.add_box(wx, -0.44, 0.40, wx + 0.04, -0.40, 0.70, "car_exterior")
    for wx in (-1.48, -1.02, -0.98, -0.48, -0.45, -0.02, 0.02, 0.45, 0.48, 0.98, 1.02, 1.44):
        b.add_box(wx, 0.40, 0.40, wx + 0.04, 0.44, 0.70, "car_exterior")

    # Window headers & roof
    b.add_box(-1.48, 0.39, 0.70, 1.48, 0.43, 0.72, "car_exterior")
    b.add_box(-1.48, -0.43, 0.70, -0.45, -0.39, 0.72, "car_exterior")
    b.add_box( 0.45, -0.43, 0.70,  1.48, -0.39, 0.72, "car_exterior")

    b.add_box(-1.48, 0.40, 0.72, 1.48, 0.44, 0.82, "car_exterior")
    b.add_box(-1.48, -0.44, 0.72, 1.48, -0.40, 0.82, "car_exterior")

    b.add_box(-1.48, -0.42, 0.82, 1.48, 0.42, 0.85, "car_exterior")
    b.add_box(-1.10, -0.28, 0.85, -0.40, 0.28, 0.91, "ac_unit")
    b.add_box( 0.40, -0.28, 0.85,  1.10, 0.28, 0.91, "ac_unit")

    # Ceiling light
    b.add_box(-1.30, -0.06, 0.80, 1.30, 0.06, 0.82, "ceiling_light")

    # Seats
    b.add_box(-1.40, 0.16, 0.03, -0.60, 0.38, 0.22, seat_mat)
    b.add_box(-1.40, 0.34, 0.22, -0.60, 0.38, 0.42, seat_mat)
    b.add_box(-0.35, 0.16, 0.03,  0.35, 0.38, 0.22, seat_mat)
    b.add_box(-0.35, 0.34, 0.22,  0.35, 0.38, 0.42, seat_mat)
    b.add_box( 0.60, 0.16, 0.03,  1.40, 0.38, 0.22, seat_mat)
    b.add_box( 0.60, 0.34, 0.22,  1.40, 0.38, 0.42, seat_mat)

    # Poles
    for px in (-0.9, 0.0, 0.9):
        b.add_box(px - 0.02, -0.02, 0.03, px + 0.02, 0.02, 0.80, "pole_steel")
    b.add_box(-1.40, -0.15, 0.72, 1.40, -0.12, 0.74, "pole_steel")
    b.add_box(-1.40,  0.12, 0.72, 1.40,  0.15, 0.74, "pole_steel")

    # Gangways
    if variant in ("center", "lead"):
        b.add_box(-1.50, -0.42, 0.03, -1.48, -0.26, 0.82, "bellows_dark")
        b.add_box(-1.50,  0.26, 0.03, -1.48,  0.42, 0.82, "bellows_dark")
        b.add_box(-1.50, -0.42, 0.74, -1.48,  0.42, 0.82, "bellows_dark")
    if variant == "rear":
        b.add_box(-1.65, -0.42, 0.03, -1.48, 0.42, 0.82, "car_exterior")
        b.add_box(-1.66, -0.32, 0.35, -1.64, -0.22, 0.40, "taillight_red")
        b.add_box(-1.66,  0.22, 0.35, -1.64,  0.32, 0.40, "taillight_red")

    if variant in ("center", "rear"):
        b.add_box( 1.48, -0.42, 0.03,  1.50, -0.26, 0.82, "bellows_dark")
        b.add_box( 1.48,  0.26, 0.03,  1.50,  0.42, 0.82, "bellows_dark")
        b.add_box( 1.48, -0.42, 0.74,  1.50,  0.42, 0.82, "bellows_dark")
    if variant == "lead":
        b.add_box( 1.48, -0.42, 0.03,  1.65, 0.42, 0.82, "car_exterior")
        b.add_box( 1.62, -0.35, 0.42,  1.65, 0.35, 0.68, "windshield_frame")
        b.add_box( 1.64, -0.32, 0.35,  1.66, -0.22, 0.40, "headlight_white")
        b.add_box( 1.64,  0.22, 0.35,  1.66,  0.32, 0.40, "headlight_white")
        b.add_box( 1.63, -0.25, 0.72,  1.65, 0.25, 0.78, "rollsign_led")

    # Doors
    b.add_box(-0.45, -0.44, 0.02, 0.45, -0.38, 0.03, "door_metal")
    if door_mode == "closed":
        b.add_box(-0.44, -0.43, 0.03, -0.01, -0.41, 0.72, "door_metal")
        b.add_box(-0.32, -0.435, 0.40, -0.12, -0.405, 0.65, "window_frame")
        b.add_box( 0.01, -0.43, 0.03,  0.44, -0.41, 0.72, "door_metal")
        b.add_box( 0.12, -0.435, 0.40,  0.32, -0.405, 0.65, "window_frame")
    elif door_mode == "half":
        b.add_box(-0.52, -0.43, 0.03, -0.24, -0.41, 0.72, "door_metal")
        b.add_box( 0.24, -0.43, 0.03,  0.52, -0.41, 0.72, "door_metal")
    else: # "open"
        b.add_box(-0.62, -0.43, 0.03, -0.45, -0.41, 0.72, "door_metal")
        b.add_box( 0.45, -0.43, 0.03,  0.62, -0.41, 0.72, "door_metal")

    tag = f"_{line_suffix}" if line_suffix else ""
    if variant == "center":
        filename = f"metro_wagon{tag}.obj" if door_mode == "open" else f"metro_wagon_{door_mode}{tag}.obj"
    elif variant == "lead":
        filename = f"metro_wagon_lead{tag}.obj" if door_mode == "open" else f"metro_wagon_lead_{door_mode}{tag}.obj"
    elif variant == "rear":
        filename = f"metro_wagon_rear{tag}.obj" if door_mode == "open" else f"metro_wagon_rear_{door_mode}{tag}.obj"

    b.write(os.path.join(out_dir, filename))

def write_mtls(out_dir):
    colors = {
        "l1": ("0.08 0.24 0.59", "0.08 0.24 0.59"), # Blue
        "l2": ("0.04 0.51 0.24", "0.04 0.51 0.24"), # Green
        "l3": ("0.71 0.10 0.10", "0.71 0.10 0.10"), # Red
        "l4": ("0.86 0.69 0.04", "0.86 0.69 0.04"), # Yellow
        "l5": ("0.51 0.24 0.63", "0.51 0.24 0.63"), # Lilac
    }
    for line, (stripe_col, seat_col) in colors.items():
        with open(os.path.join(out_dir, f"metro_wagon_{line}.mtl"), "w", encoding="utf-8", newline="\n") as f:
            f.write(f"""newmtl car_exterior
Kd 0.75 0.77 0.80

newmtl bogie_dark
Kd 0.15 0.16 0.18

newmtl wheel_steel
Kd 0.50 0.52 0.55

newmtl floor_mat
Kd 0.25 0.25 0.28

newmtl stripe_accent
Kd {stripe_col}

newmtl seat_accent
Kd {seat_col}

newmtl pole_steel
Kd 0.85 0.87 0.90

newmtl door_metal
Kd 0.65 0.68 0.72

newmtl ac_unit
Kd 0.40 0.42 0.45

newmtl ceiling_light
Kd 0.95 0.98 1.00

newmtl bellows_dark
Kd 0.12 0.12 0.14

newmtl taillight_red
Kd 0.90 0.10 0.10

newmtl headlight_white
Kd 1.00 0.98 0.85

newmtl rollsign_led
Kd 0.10 0.10 0.12

newmtl windshield_frame
Kd 0.20 0.22 0.25

newmtl window_frame
Kd 0.30 0.32 0.35
""")

    # Default MTL (Line 1)
    with open(os.path.join(out_dir, "metro_wagon.mtl"), "w", encoding="utf-8", newline="\n") as f:
        f.write("""newmtl car_exterior
Kd 0.75 0.77 0.80

newmtl bogie_dark
Kd 0.15 0.16 0.18

newmtl wheel_steel
Kd 0.50 0.52 0.55

newmtl floor_mat
Kd 0.25 0.25 0.28

newmtl stripe_blue
Kd 0.08 0.24 0.59

newmtl seat_blue
Kd 0.08 0.24 0.59

newmtl pole_steel
Kd 0.85 0.87 0.90

newmtl door_metal
Kd 0.65 0.68 0.72

newmtl ac_unit
Kd 0.40 0.42 0.45

newmtl ceiling_light
Kd 0.95 0.98 1.00

newmtl bellows_dark
Kd 0.12 0.12 0.14

newmtl taillight_red
Kd 0.90 0.10 0.10

newmtl headlight_white
Kd 1.00 0.98 0.85

newmtl rollsign_led
Kd 0.10 0.10 0.12

newmtl windshield_frame
Kd 0.20 0.22 0.25

newmtl window_frame
Kd 0.30 0.32 0.35
""")

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_dir = os.path.join(repo_root, "projects/hichaukitoden-game/assets/models/metro")
    if len(sys.argv) > 1:
        out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)

    print(f"Generating metro models in: {out_dir}")
    generate_rails(out_dir)
    generate_column(out_dir)
    write_mtls(out_dir)

    for var in ("center", "lead", "rear"):
        for dm in ("open", "half", "closed"):
            generate_wagon_model(out_dir, var, dm, line_suffix="", mtl_name="metro_wagon.mtl")

    for line_idx in (1, 2, 3, 4, 5):
        suffix = f"l{line_idx}"
        mtl_n = f"metro_wagon_{suffix}.mtl"
        for var in ("center", "lead", "rear"):
            for dm in ("open", "half", "closed"):
                generate_wagon_model(out_dir, var, dm, line_suffix=suffix, mtl_name=mtl_n)

    print("All models successfully generated.")

if __name__ == "__main__":
    main()
