"""Derived mesh preparation; never alters authored mesh datablocks."""
import bmesh


def prepare(mesh):
    """Repair closed-body winding and identify sheets for parity-cull exclusion."""
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        is_open = any(not edge.is_manifold for edge in bm.edges)
        if not is_open:
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            is_open = abs(bm.calc_volume(signed=True)) < 1e-9
            if not is_open:
                bm.to_mesh(mesh)
                mesh.update()
        return is_open
    finally:
        bm.free()
