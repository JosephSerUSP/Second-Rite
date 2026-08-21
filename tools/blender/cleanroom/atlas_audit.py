"""Measure how the baked atlas allocates texels vs screen-space need."""
import json, math
from pathlib import Path

PKG = Path(r"D:\Antigravity\hk-cleanroom\projects\hichaukitoden-game\assets\environments\town_cleanroom")
EYE = (0.9, 5.5, 0.0)
K = 512.0                    # px per (world unit / depth) both axes
CENTER_Y = 70.0
W, H = 426.0, 240.0
OFFSETS = (-96, 0, 96)
ATLAS = 1024

def load_obj(p):
    V, VT, F = [], [], []
    for line in Path(p).read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.split()
        if not s: continue
        if s[0] == "v":  V.append(tuple(float(x) for x in s[1:4]))
        elif s[0] == "vt": VT.append(tuple(float(x) for x in s[1:3]))
        elif s[0] == "f":
            idx = []
            for tok in s[1:]:
                a = tok.split("/")
                vi = int(a[0]) - 1
                ti = int(a[1]) - 1 if len(a) > 1 and a[1] else None
                idx.append((vi, ti))
            for i in range(1, len(idx) - 1):
                F.append((idx[0], idx[i], idx[i+1]))
    return V, VT, F

def tri_area3(a, b, c):
    u = [b[i]-a[i] for i in range(3)]; v = [c[i]-a[i] for i in range(3)]
    n = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
    return 0.5*math.sqrt(sum(x*x for x in n)), n

def project(pt, cx):
    d = pt[0] - EYE[0]
    if d <= 0.05: return None
    return (cx + K*(pt[1]-EYE[1])/d, CENTER_Y - K*pt[2]/d)

def clip_poly(poly, W, H):
    def inside(p, e):
        return (p[0] >= 0) if e == 0 else (p[0] <= W) if e == 1 else (p[1] >= 0) if e == 2 else (p[1] <= H)
    def inter(p, q, e):
        if e in (0, 1):
            xe = 0.0 if e == 0 else W
            t = (xe - p[0])/(q[0]-p[0]) if q[0] != p[0] else 0.0
            return (xe, p[1] + t*(q[1]-p[1]))
        ye = 0.0 if e == 2 else H
        t = (ye - p[1])/(q[1]-p[1]) if q[1] != p[1] else 0.0
        return (p[0] + t*(q[0]-p[0]), ye)
    out = poly
    for e in range(4):
        if not out: return []
        inp, out = out, []
        for i in range(len(inp)):
            cur, prv = inp[i], inp[i-1]
            if inside(cur, e):
                if not inside(prv, e): out.append(inter(prv, cur, e))
                out.append(cur)
            elif inside(prv, e):
                out.append(inter(prv, cur, e))
    return out

def poly_area(p):
    if len(p) < 3: return 0.0
    return abs(sum(p[i][0]*p[(i+1)%len(p)][1] - p[(i+1)%len(p)][0]*p[i][1]
                   for i in range(len(p))))*0.5

V, VT, F = load_obj(PKG/"environment.obj")
rows = []
for tri in F:
    p3 = [V[i] for i, _ in tri]
    uv = [VT[t] for _, t in tri if t is not None]
    a3, n = tri_area3(*p3)
    uva = poly_area(uv) if len(uv) == 3 else 0.0
    texels = uva * ATLAS * ATLAS
    cen = tuple(sum(p[i] for p in p3)/3 for i in range(3))
    view = tuple(EYE[i]-cen[i] for i in range(3))
    facing = sum(n[i]*view[i] for i in range(3)) > 0
    best = 0.0
    if facing:
        for off in OFFSETS:
            cx = 213.0 - off
            pr = [project(p, cx) for p in p3]
            if any(q is None for q in pr): continue
            best = max(best, poly_area(clip_poly(pr, W, H)))
    rows.append({"area3": a3, "texels": texels, "screen": best, "facing": facing})

tot_tex = sum(r["texels"] for r in rows)
vis = [r for r in rows if r["screen"] > 0.5]
inv = [r for r in rows if r["screen"] <= 0.5]
tex_vis = sum(r["texels"] for r in vis); tex_inv = sum(r["texels"] for r in inv)
scr_tot = sum(r["screen"] for r in vis)

print("triangles                    : %d  (%d ever visible, %d never)" % (len(rows), len(vis), len(inv)))
print("atlas texels allocated       : %.0f  (%.1f%% of %d^2)" % (tot_tex, 100*tot_tex/ATLAS**2, ATLAS))
print("  -> to NEVER-VISIBLE faces  : %.0f  (%.1f%% of allocated)" % (tex_inv, 100*tex_inv/max(tot_tex,1)))
print("  -> to visible faces        : %.0f  (%.1f%%)" % (tex_vis, 100*tex_vis/max(tot_tex,1)))
print("total visible screen px      : %.0f  (frame is %d px)" % (scr_tot, int(W*H)))
print()
ratios = sorted((r["texels"]/r["screen"], r) for r in vis if r["screen"] > 4)
print("texels per visible screen pixel, across visible triangles:")
for q, lbl in ((0.0,"min"), (0.25,"p25"), (0.5,"median"), (0.75,"p75"), (1.0,"max")):
    i = min(int(q*(len(ratios)-1)), len(ratios)-1)
    print("   %-7s %8.2f" % (lbl, ratios[i][0]))
print()
print("if every visible face got exactly 1 texel per screen pixel, the atlas")
print("would need %.0f texels = %.0f x %.0f  (vs %d x %d today)"
      % (scr_tot, math.sqrt(scr_tot), math.sqrt(scr_tot), ATLAS, ATLAS))
over = sum(max(0.0, r["texels"] - r["screen"]) for r in vis)
print("texels above 1:1 need on visible faces: %.0f (%.1f%% of allocated)" % (over, 100*over/max(tot_tex,1)))
