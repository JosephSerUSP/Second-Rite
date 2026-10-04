#!/usr/bin/env python3
"""Build deterministic low-poly OBJ models for Second Rite items 63-72."""
import json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "models" / "items"
MTL_NAME = "item_batch_63_72.mtl"
ITEMS = {
    63: ("silver_rod", "Silver Rod"),
    64: ("mage_staff", "Mage Staff"),
    65: ("sage_staff", "Sage Staff"),
    66: ("ether_staff", "Ether Staff"),
    67: ("war_staff", "War Staff"),
    68: ("rune_knife", "Rune Knife"),
    69: ("spell_sword", "Spell Sword"),
    70: ("glass_blade", "Glass Blade"),
    71: ("comet_edge", "Comet Edge"),
    72: ("flame_saber", "Flame Saber"),
}
MATS = {
    "old_limestone": (0.561, 0.537, 0.467), "rough_limestone": (0.494, 0.467, 0.396),
    "ritual_gold": (0.569, 0.467, 0.235), "oxidized_bronze": (0.337, 0.337, 0.267),
    "wrought_iron": (0.157, 0.157, 0.149), "dark_wood": (0.275, 0.188, 0.133),
    "aged_cloth": (0.439, 0.353, 0.275), "smoked_glass": (0.196, 0.239, 0.235),
    "wet_residue": (0.196, 0.275, 0.196), "bone": (0.745, 0.698, 0.569),
    "wax": (0.608, 0.494, 0.275), "crystal": (0.353, 0.510, 0.588),
}

def add(a,b): return tuple(a[i]+b[i] for i in range(3))
def sub(a,b): return tuple(a[i]-b[i] for i in range(3))
def mul(a,s): return tuple(x*s for x in a)
def length(a): return math.sqrt(sum(x*x for x in a))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def normalize(a):
    n=length(a)
    if n < 1e-9: raise ValueError("zero vector")
    return tuple(x/n for x in a)

class Mesh:
    def __init__(self,name): self.name=name; self.vertices=[]; self.faces=[]
    def v(self,p): self.vertices.append(tuple(round(x,6) for x in p)); return len(self.vertices)
    def tri(self,mat,a,b,c):
        pa,pb,pc=(self.vertices[i-1] for i in (a,b,c))
        if length(cross(sub(pb,pa),sub(pc,pa))) < 1e-8: raise ValueError(f"degenerate {self.name}")
        self.faces.append((mat,(a,b,c)))
    def quad(self,mat,a,b,c,d): self.tri(mat,a,b,c); self.tri(mat,a,c,d)
    def box(self,center,size,mat):
        cx,cy,cz=center; hx,hy,hz=(s/2 for s in size)
        p=[(cx-hx,cy-hy,cz-hz),(cx+hx,cy-hy,cz-hz),(cx+hx,cy+hy,cz-hz),(cx-hx,cy+hy,cz-hz),
           (cx-hx,cy-hy,cz+hz),(cx+hx,cy-hy,cz+hz),(cx+hx,cy+hy,cz+hz),(cx-hx,cy+hy,cz+hz)]
        i=[self.v(x) for x in p]
        for q in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5)]: self.quad(mat,*(i[k] for k in q))
    def extrude(self,points,z0,z1,mat):
        n=len(points); lo=[self.v((x,y,z0)) for x,y in points]; hi=[self.v((x,y,z1)) for x,y in points]
        for k in range(1,n-1): self.tri(mat,lo[0],lo[k+1],lo[k]); self.tri(mat,hi[0],hi[k],hi[k+1])
        for k in range(n):
            j=(k+1)%n; self.quad(mat,lo[k],lo[j],hi[j],hi[k])
    def prism(self,p0,p1,r0,r1,sides,mat,phase=0.0):
        axis=normalize(sub(p1,p0)); helper=(0,0,1) if abs(axis[2])<.85 else (1,0,0)
        u=normalize(cross(axis,helper)); v=cross(axis,u); rings=[]
        for p,r in ((p0,r0),(p1,r1)):
            ring=[]
            for k in range(sides):
                a=phase+2*math.pi*k/sides; ring.append(self.v(add(p,add(mul(u,math.cos(a)*r),mul(v,math.sin(a)*r)))))
            rings.append(ring)
        c0,c1=self.v(p0),self.v(p1)
        for k in range(sides):
            j=(k+1)%sides; self.tri(mat,c0,rings[0][j],rings[0][k]); self.tri(mat,c1,rings[1][k],rings[1][j]); self.quad(mat,rings[0][k],rings[0][j],rings[1][j],rings[1][k])
    def diamond(self,center,radius,height,mat,sides=6):
        cx,cy,cz=center; ring=[self.v((cx+radius*math.cos(2*math.pi*k/sides),cy,cz+radius*math.sin(2*math.pi*k/sides))) for k in range(sides)]
        top=self.v((cx,cy+height/2,cz)); bot=self.v((cx,cy-height/2,cz))
        for k in range(sides):
            j=(k+1)%sides; self.tri(mat,top,ring[k],ring[j]); self.tri(mat,bot,ring[j],ring[k])
    def center(self):
        lo=[min(p[i] for p in self.vertices) for i in range(3)]; hi=[max(p[i] for p in self.vertices) for i in range(3)]; c=[(lo[i]+hi[i])/2 for i in range(3)]
        self.vertices=[tuple(round(p[i]-c[i],6) for i in range(3)) for p in self.vertices]

def sword(m,length_,half_width,thickness,guard,grip,point,blade="wrought_iron",accent=None,fuller=False,curve=0.0):
    y0=-length_/2+grip+.25; y1=length_/2-point
    poly=[(-half_width,y0),(-half_width*1.08,y0+.35),(-half_width*.82+curve,y1),(curve,y1+point),(half_width*.82+curve,y1),(half_width*1.08,y0+.35),(half_width,y0)]
    m.extrude(poly,-thickness/2,thickness/2,blade); m.box((0,y0-.10,0),(guard,.16,thickness*2),accent or blade)
    m.prism((0,y0-.16,0),(0,y0-grip,0),.11,.09,6,"dark_wood"); m.diamond((0,y0-grip-.08,0),.16,.20,accent or blade,4)
    if fuller: m.box((curve*.35,(y0+y1)/2,thickness*.55),(half_width*.20,(y1-y0)*.68,thickness*.16),accent or "ritual_gold")

def silver_rod():
    m=Mesh("silver_rod"); m.prism((0,-1.5,0),(0,1.05,0),.095,.075,8,"wrought_iron")
    m.prism((0,.92,0),(0,1.34,0),.17,.11,6,"ritual_gold"); m.diamond((0,1.52,0),.25,.46,"crystal",8)
    m.box((0,-.92,0),(.24,.10,.20),"ritual_gold"); m.center(); return m

def mage_staff():
    m=Mesh("mage_staff"); pts=[(0,-1.55,0),(.05,-.55,.02),(-.04,.40,-.01),(0,1.10,0)]
    for a,b in zip(pts,pts[1:]): m.prism(a,b,.11,.09,7,"dark_wood")
    m.prism((0,1.05,0),(-.42,1.50,0),.09,.05,6,"dark_wood"); m.prism((0,1.05,0),(.42,1.50,0),.09,.05,6,"dark_wood")
    m.diamond((0,1.45,0),.27,.48,"crystal",6); m.box((0,.93,0),(.42,.12,.20),"ritual_gold"); m.center(); return m

def sage_staff():
    m=Mesh("sage_staff"); m.prism((0,-1.65,0),(0,1.05,0),.115,.09,8,"dark_wood")
    for sx in (-1,1):
        m.prism((0,.96,0),(.46*sx,1.38,0),.10,.055,6,"ritual_gold"); m.prism((.46*sx,1.38,0),(.25*sx,1.66,0),.055,.04,6,"ritual_gold")
    m.diamond((0,1.45,0),.30,.58,"crystal",8); m.prism((0,-1.50,0),(0,-1.82,0),.16,.12,6,"ritual_gold"); m.center(); return m

def ether_staff():
    m=Mesh("ether_staff"); m.prism((0,-1.72,0),(0,.88,0),.12,.08,8,"wrought_iron")
    # open halo around the head, visibly unlike the lower tiers
    r=.48; pts=[]
    for k in range(9):
        a=-2.5+5.0*k/8; pts.append((r*math.cos(a),1.35+r*math.sin(a),0))
    for a,b in zip(pts,pts[1:]): m.prism(a,b,.065,.065,6,"ritual_gold")
    m.diamond((0,1.35,0),.25,.62,"crystal",8); m.diamond((0,-1.82,0),.18,.24,"crystal",6); m.center(); return m

def war_staff():
    m=Mesh("war_staff"); m.prism((0,-1.55,0),(0,1.20,0),.14,.115,8,"dark_wood")
    m.box((0,1.26,0),(1.12,.18,.22),"wrought_iron")
    for sx in (-1,1): m.prism((.48*sx,1.26,0),(.62*sx,1.08,0),.11,.04,5,"wrought_iron")
    m.box((0,-.90,0),(.30,.14,.24),"aged_cloth"); m.center(); return m

def rune_knife():
    m=Mesh("rune_knife"); sword(m,2.25,.22,.105,.50,.56,.34,accent="ritual_gold")
    for y in (.10,.42,.74): m.box((0,y,.064),(.10,.13,.035),"crystal")
    m.center(); return m

def spell_sword():
    m=Mesh("spell_sword"); sword(m,3.45,.25,.12,.90,.78,.44,accent="ritual_gold",fuller=True)
    m.diamond((0,-1.32,0),.18,.23,"crystal",6); m.center(); return m

def glass_blade():
    m=Mesh("glass_blade"); sword(m,3.70,.27,.10,.86,.78,.55,blade="smoked_glass",accent="ritual_gold",fuller=False)
    # metal spine makes the translucent blade read as manufactured, not ice
    m.box((-.18,.35,0),(.065,2.25,.14),"wrought_iron"); m.center(); return m

def comet_edge():
    m=Mesh("comet_edge"); sword(m,4.15,.31,.135,1.08,.88,.58,blade="wrought_iron",accent="ritual_gold",fuller=True,curve=.10)
    for y,s in ((.45,.12),(.95,.10),(1.40,.08)): m.diamond((.16,y,.10),s,.12,"crystal",5)
    m.extrude([(-.48,-1.00),(-.22,-1.24),(0,-.92),(-.20,-.70)],-.08,.08,"ritual_gold"); m.center(); return m

def flame_saber():
    m=Mesh("flame_saber"); sword(m,3.55,.26,.115,.82,.75,.48,blade="wrought_iron",accent="ritual_gold",curve=.17)
    # stepped wax/crystal flame tongue along the back edge, subdued rather than neon
    for y,x,r in ((.35,-.13,.11),(.72,-.10,.10),(1.08,-.06,.085)): m.diamond((x,y,.09),r,.16,"wax",5)
    m.diamond((0,-1.28,0),.17,.22,"crystal",6); m.center(); return m

BUILD={63:silver_rod,64:mage_staff,65:sage_staff,66:ether_staff,67:war_staff,68:rune_knife,69:spell_sword,70:glass_blade,71:comet_edge,72:flame_saber}

def write(mesh,path,label):
    used=[]
    for mat,_ in mesh.faces:
        if mat not in used: used.append(mat)
    missing=[m for m in used if m not in MATS]
    if missing: raise ValueError(missing)
    lines=["# Second Rite deterministic item batch 63-72",f"# {label}",f"mtllib {MTL_NAME}",f"o {path.stem}","s off"]
    lines += [f"v {x:.6f} {y:.6f} {z:.6f}" for x,y,z in mesh.vertices]
    cur=None
    for mat,face in mesh.faces:
        if mat != cur: lines.append(f"usemtl {mat}"); cur=mat
        lines.append("f "+" ".join(map(str,face)))
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return len(mesh.vertices),len(mesh.faces),used

def validate(path):
    verts=[]; faces=[]; uses=[]; mtllib=None
    for line in path.read_text().splitlines():
        if line.startswith("v "): verts.append(tuple(map(float,line.split()[1:4])))
        elif line.startswith("f "): faces.append(tuple(int(x) for x in line.split()[1:]))
        elif line.startswith("usemtl "): uses.append(line.split(None,1)[1])
        elif line.startswith("mtllib "): mtllib=line.split(None,1)[1]
    assert verts and faces and mtllib == MTL_NAME and set(uses) <= set(MATS)
    for f in faces:
        assert len(f)==3 and min(f)>=1 and max(f)<=len(verts)
        a,b,c=(verts[i-1] for i in f); assert length(cross(sub(b,a),sub(c,a))) >= 1e-8

def patch_items():
    path=ROOT/"data"/"items.json"
    if not path.is_file(): return False
    data=json.loads(path.read_text(encoding="utf-8")); by_id={item.get("id"):item for item in data}
    for item_id,(stem,_) in ITEMS.items():
        item=by_id[item_id]; target=f"assets/models/items/{stem}.obj"
        if item.get("model") not in (None,target): raise ValueError(f"item {item_id} already has a different model: {item.get('model')}")
        item["model"]=target
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); return True

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    lines=["# Shared semantic materials for deterministic item batch 63-72"]
    for mat,(r,g,b) in MATS.items(): lines += [f"newmtl {mat}",f"Kd {r:.3f} {g:.3f} {b:.3f}",""]
    (OUT/MTL_NAME).write_text("\n".join(lines)+"\n",encoding="utf-8")
    report={}
    for item_id,(stem,label) in ITEMS.items():
        mesh=BUILD[item_id](); path=OUT/f"{stem}.obj"; v,f,used=write(mesh,path,label); validate(path); report[str(item_id)]={"name":label,"model":f"assets/models/items/{stem}.obj","vertices":v,"triangles":f,"materials":used}
    print(json.dumps({"ok":True,"items":report,"itemsJsonPatched":patch_items()},indent=2)); return 0
if __name__ == "__main__": raise SystemExit(main())
