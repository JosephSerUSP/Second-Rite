"""Measured evaluated geometry for catalogue and relational scaffold placement."""
import bpy
from mathutils import Vector


def bounds(parts):
    bpy.context.view_layer.update()
    graph=bpy.context.evaluated_depsgraph_get()
    points=[]
    for obj in parts:
        if obj.type!='MESH': continue
        evaluated=obj.evaluated_get(graph)
        mesh=evaluated.to_mesh()
        try:
            points.extend(evaluated.matrix_world @ v.co for v in mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    if not points: raise ValueError('furnishing has no measured vertices')
    return [[round(min(p[i] for p in points),6) for i in range(3)],
            [round(max(p[i] for p in points),6) for i in range(3)]]


def rectangular_top(parts, field):
    """Require one actual horizontal rectangular face at the highest surface.

    A service assembly with several equal-height caps is intentionally ambiguous.
    Do not make its bounding box into a pretend continuous support surface.
    """
    top=bounds(parts)[1][2]
    candidates=[]
    graph=bpy.context.evaluated_depsgraph_get()
    for obj in parts:
        if obj.type!='MESH': continue
        evaluated=obj.evaluated_get(graph)
        mesh=evaluated.to_mesh()
        try:
            for face in mesh.polygons:
                points=[evaluated.matrix_world @ mesh.vertices[i].co for i in face.vertices]
                if len(points)!=4 or any(abs(p.z-top)>1e-5 for p in points): continue
                lo=[min(p[i] for p in points) for i in range(3)]
                hi=[max(p[i] for p in points) for i in range(3)]
                corners={(round(p.x,5),round(p.y,5)) for p in points}
                expected={(round(x,5),round(y,5)) for x in (lo[0],hi[0]) for y in (lo[1],hi[1])}
                if corners==expected and hi[0]>lo[0] and hi[1]>lo[1]: candidates.append([lo,hi])
        finally:
            evaluated.to_mesh_clear()
    if len(candidates)!=1:
        raise ValueError(f'{field}: on requires one rectangular top face; found {len(candidates)}')
    return candidates[0]


def translate(parts, delta):
    bpy.context.view_layer.update()
    # Each emitted part is a sibling under the same scaffold root. Lights move too.
    for obj in parts:
        matrix=obj.matrix_world.copy()
        matrix.translation+=Vector(delta)
        obj.matrix_world=matrix
    bpy.context.view_layer.update()
