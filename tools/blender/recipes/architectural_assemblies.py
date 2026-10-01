"""Detailed architectural sources with explicit, simpler bake targets.

Dimensions describe a masonry aperture, not a collection of unrelated cubes.
The family uses the same stock profile at different sizes; fine joinery belongs
to the source, while aperture reveals and opened shutters retain real depth.
"""
from dataclasses import dataclass,asdict
import json

@dataclass(frozen=True)
class Window:
    name:str
    x:float
    y:float
    sill:float
    width:float=1.35
    height:float=1.70
    reveal:float=.24
    shutters:bool=True
    columns:int=2
    rows:int=3
    shutter_angles:tuple=(110.0,140.0)

    def __post_init__(self):
        import math
        if any(not math.isfinite(value) or value<=0 for value in [self.width,self.height,self.reveal]) or any(type(value)!=int or value<1 for value in [self.columns,self.rows]):
            raise ValueError('Invalid architectural window dimensions')
        if len(self.shutter_angles)!=2 or any(not math.isfinite(angle) or not 0<=angle<=180 for angle in self.shutter_angles):
            raise ValueError('Shutters must have two opening angles between 0 and 180 degrees')


def window(builder,spec,materials):
    import bpy
    stock=materials['sash'];stone=materials['stone'];glass=materials['glass'];shutter=materials['shutter'];iron=materials['iron']
    x,y,z,w,h=spec.x,spec.y,spec.sill,spec.width,spec.height
    frame_x=x+spec.reveal-.045
    root=bpy.data.objects.new(spec.name+' assembly',None);builder.source.objects.link(root)
    root['architectural_spec']=json.dumps(asdict(spec));root['assembly_kind']='rebated casement with louvred shutters'
    def piece(suffix,size,position,material,role='source',bevel=.004):
        obj=builder.part(spec.name+' '+suffix,size,position,material,role=role,bevel=bevel)
        obj.parent=root
        return obj
    # Masonry reveal and projecting sill are physical runtime surfaces.
    for sign,tag in [(-1,'left'),(1,'right')]:
        piece(tag+' reveal',(spec.reveal+.13,.145,h+.19),(x+spec.reveal/2-.025,y+sign*(w/2+.0725),z+h/2),stone,'both',.01)
        piece(tag+' moulded architrave',(.085,.19,h+.32),(x-.062,y+sign*(w/2+.09),z+h/2),stone,bevel=.018)
    piece('head reveal',(spec.reveal+.13,w+.29,.145),(x+spec.reveal/2-.025,y,z+h+.0725),stone,'both',.01)
    piece('sill',(spec.reveal+.38,w+.52,.16),(x+spec.reveal/2-.16,y,z-.075),stone,'both',.018)
    piece('sill drip',(.065,w+.40,.045),(x-.295,y,z-.15),stone)
    piece('head cornice',(.20,w+.43,.11),(x-.105,y,z+h+.20),stone,bevel=.02)
    # Two nested rebates, rounded beads, mortised stiles and six individual panes.
    for sign,tag in [(-1,'left'),(1,'right')]:
        piece(tag+' sash stile',(.065,.085,h),(frame_x,y+sign*(w/2-.045),z+h/2),stock)
        piece(tag+' rebate',(.028,.027,h-.11),(frame_x-.047,y+sign*(w/2-.10),z+h/2),stock)
    for j in range(spec.rows+1):
        zz=z+.04+(h-.08)*j/spec.rows
        piece('sash rail '+str(j),(.07,w-.07,.055 if j not in [0,spec.rows] else .085),(frame_x,y,zz),stock)
    for i in range(1,spec.columns):
        yy=y-w/2+w*i/spec.columns
        piece('sash mullion '+str(i),(.08,.06,h-.07),(frame_x-.01,yy,z+h/2),stock)
        piece('meeting bead '+str(i),(.024,.018,h-.10),(frame_x-.061,yy,z+h/2),stock)
    for row in range(spec.rows):
        for col in range(spec.columns):
            yy=y-w/2+(col+.5)*w/spec.columns;zz=z+(row+.5)*h/spec.rows
            piece(f'glass {col} {row}',(.01,w/spec.columns-.065,h/spec.rows-.055),(frame_x+.045,yy,zz),glass,bevel=0)
    piece('casement latch',(.055,.055,.15),(frame_x-.08,y+.08,z+h*.49),iron)
    builder.receiver(spec.name+' glazing target',frame_x-.02,y,z+h/2,w,h,glass)
    if spec.shutters:
        leaf_w=w*.49
        for sign,tag in [(-1,'left'),(1,'right')]:
            hinge_y=y+sign*(w/2+.10)
            leaf_y=hinge_y-sign*leaf_w/2
            before=set(root.children)
            # This target is absent from beauty: a solid backing would hide the
            # louvres when an opened leaf exposes its rear to the scene camera.
            target=piece(tag+' shutter target',(.055,leaf_w,h),(x-.155,leaf_y,z+h/2),shutter,'receiver',0)
            target.hide_render=True;target['sr_bake_open_surface']=True
            for edge in [-1,1]:
                piece(f'{tag} shutter stile {edge}',(.075,.064,h),(x-.148,leaf_y+edge*(leaf_w/2-.032),z+h/2),shutter)
            for zz in [z+.04,z+h*.49,z+h-.04]:
                piece(f'{tag} shutter crossrail {zz}',(.08,leaf_w,.065),(x-.15,leaf_y,zz),shutter)
            slats=max(10,int(h/.10))
            for j in range(slats):
                zz=z+.11+j*(h-.22)/(slats-1)
                obj=piece(f'{tag} louvre {j}',(.06,leaf_w-.12,.067),(x-.155,leaf_y,zz),shutter)
                obj.rotation_euler.y=.33
            for fraction in [.18,.80]:
                piece(f'{tag} strap hinge {fraction}',(.021,leaf_w*.7,.04),(x-.203,leaf_y-sign*.035,z+h*fraction),iron)
                piece(f'{tag} hinge knuckle {fraction}',(.035,.028,.10),(x-.12,hinge_y,z+h*fraction),iron)
            hinge=bpy.data.objects.new(spec.name+' '+tag+' shutter hinge',None)
            builder.source.objects.link(hinge);hinge.parent=root
            hinge.location=(x-.12,hinge_y,z)
            for obj in set(root.children)-before-{hinge}:
                location=obj.location.copy()
                obj.parent=hinge;obj.location=location-hinge.location
            angle=spec.shutter_angles[0 if sign<0 else 1]
            import math
            hinge.rotation_euler.z=math.radians(-sign*angle)
            hinge['opening_degrees']=angle
    return root
