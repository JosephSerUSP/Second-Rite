"""Editable courtyard attachments, in metres: +X depth, Y frontage, +Z up.

These add objects to a caller-owned collection; they never reset or save a scene.
Openings are applied facade details, not gameplay portals or collision geometry.
"""
import math
import bpy
import second_rite_asset_core as core
from first_stratum.common import box


def block(collection, name, location, size, material, rank="PROP"):
    if any(v <= 0 for v in size):
        raise ValueError("architectural dimensions must be positive")
    obj = box(name, None, size, location, material, core)
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)
    obj["sr_export"] = True
    obj["sr_depth_rank"] = rank
    return obj


def hipped_roof(collection, name, centre, width, depth, rise, material, rank="PROP"):
    """Four slopes with a short longitudinal ridge; no flat slab substitute."""
    if min(width, depth, rise) <= 0:
        raise ValueError("roof dimensions must be positive")
    from house_grammar import BuildingRecipe, Wing, Course, RoofSection
    from house_grammar.roof import build_roof
    x, y, z = centre
    recipe = BuildingRecipe(name, 1,
        (Wing("roof", y, width, depth, setback=x-depth/2,
              courses=(Course("masonry", z, "whitewash"),)),),
        (RoofSection("roof", profile="hip", rise=rise, overhang=0,
                     thickness=.12),))
    record = build_roof(recipe)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(record.world_vertices(), [], record.faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    obj["sr_export"] = True
    obj["sr_depth_rank"] = rank
    return obj


def shuttered_window(collection, name, position, width, height, stone, wood, dark,
                     opening=.25, rank="PROP"):
    """Recess, four trim pieces and independently hinged slatted shutters."""
    if not 0 <= opening <= 1 or min(width, height) <= 0:
        raise ValueError("window size must be positive and opening in [0,1]")
    x,y,z = position
    pieces = [block(collection,name+'_recess',(x,y,z),(.08,width,height),dark,rank)]
    for side in (-1,1):
        pieces.append(block(collection,name+'_jamb'+str(side),(x-.09,y+side*width/2,z),(.2,.10,height+.18),stone,rank))
        pieces.append(block(collection,name+'_horizontal'+str(side),(x-.1,y,z+side*height/2),(.26,width+.28,.12),stone,rank))
        hinge = bpy.data.objects.new(name+'_hinge'+str(side),None)
        collection.objects.link(hinge)
        hinge.location=(x-.16,y+side*width/2,z)
        hinge.rotation_euler.z=side*opening*math.pi*.8
        for n in range(6):
            slat=block(collection,name+'_slat'+str(side)+'_'+str(n),(0,0,0),(.065,width*.46,height/6*.86),wood,rank)
            slat.parent=hinge
            slat.location=(0,-side*width*.24,-height/2+(n+.5)*height/6)
            pieces.append(slat)
    return pieces


def gallery(collection, name, x, y, length, floor_z, height, wood, roof,
            bays=4, depth=1.1):
    """Shared access balcony: deck, posts, open rails and sloping shelter."""
    if bays < 1 or min(length,height,depth) <= 0:
        raise ValueError("gallery requires positive dimensions and at least one bay")
    pieces=[block(collection,name+'_deck',(x,y,floor_z), (depth,length,.16),wood)]
    front=x-depth/2
    for i in range(bays+1):
        yy=y-length/2+length*i/bays
        pieces.append(block(collection,name+'_post'+str(i),(front,yy,floor_z+height/2),(.10,.10,height),wood))
    for z in (.22,.8):
        pieces.append(block(collection,name+'_rail'+str(z),(front,y,floor_z+z),(.08,length,.08),wood))
    shelter=block(collection,name+'_shelter',(x,y,floor_z+height), (depth+.45,length+.4,.13),roof)
    shelter.rotation_euler.y=-.18
    pieces.append(shelter)
    return pieces
