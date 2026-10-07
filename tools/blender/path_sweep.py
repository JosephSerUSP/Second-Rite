"""Blender-free, minimum-rotation tube frames for new item scaffolds.

The saved mesh becomes source authority. This library never opens or rewrites it.
UV V follows path distance; U follows section angle with one explicit seam.
"""
import math


def _add(a, b): return tuple(x+y for x, y in zip(a, b))
def _scale(a, s): return tuple(x*s for x in a)
def _dot(a, b): return sum(x*y for x, y in zip(a, b))
def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def _unit(a):
    length=math.sqrt(_dot(a, a))
    if length < 1e-9: raise ValueError('coincident points or reversing path')
    return _scale(a, 1/length)


def transported_frames(points):
    """Return tangent/normal/binormal frames, without global-axis tube pinches.

    Tangents bisect adjacent segment directions. Exact reversals are ambiguous
    and fail. The initial normal uses the least aligned world axis; following
    normals rotate by the shortest tangent-to-tangent rotation.
    """
    if len(points)<2 or any(len(p)!=3 or any(not math.isfinite(x) for x in p) for p in points):
        raise ValueError('at least two finite 3D points required')
    directions=[_unit(_add(b, _scale(a, -1))) for a, b in zip(points, points[1:])]
    tangents=[directions[0]]+[_unit(_add(a,b)) for a,b in zip(directions,directions[1:])]+[directions[-1]]
    axis=min(((1,0,0),(0,1,0),(0,0,1)), key=lambda a:abs(_dot(a,tangents[0])))
    normal=_unit(_add(axis,_scale(tangents[0],-_dot(axis,tangents[0]))))
    result=[];previous=tangents[0]
    for tangent in tangents:
        cross=_cross(previous,tangent);s=math.sqrt(_dot(cross,cross));c=max(-1,min(1,_dot(previous,tangent)))
        if c < -1+1e-8: raise ValueError('reversing frame transport is ambiguous')
        if s>1e-9:
            axis=_scale(cross,1/s)
            normal=_add(_add(_scale(normal,c),_scale(_cross(axis,normal),s)),_scale(axis,_dot(axis,normal)*(1-c)))
        normal=_unit(_add(normal,_scale(tangent,-_dot(normal,tangent))))
        result.append((tangent,normal,_cross(tangent,normal)));previous=tangent
    return result


def sweep_tube(points, radii, *, segments=8):
    """Closed tube mesh + per-corner normalized UVs and smooth-face flags.

    Radius entries are positive (normal, binormal) pairs. No implicit radius
    collapse or hidden weld. End caps have radial UVs; side seam is at angle 0.
    This supplies correspondence, not self-intersection or curvature clearance.
    """
    if not isinstance(segments,int) or segments<3 or len(radii)!=len(points):
        raise ValueError('one radius pair per point and at least three segments required')
    if any(len(r)!=2 or any(not math.isfinite(x) or x<=0 for x in r) for r in radii):
        raise ValueError('finite positive section radii required')
    frames=transported_frames(points)
    lengths=[0.]
    for a,b in zip(points,points[1:]):lengths.append(lengths[-1]+math.dist(a,b))
    vs=[v/lengths[-1] for v in lengths]
    verts=[];faces=[];uvs=[];smooth=[]
    for p,(rn,rb),(_,n,b) in zip(points,radii,frames):
        for j in range(segments):
            angle=j/segments*math.tau
            verts.append(_add(p,_add(_scale(n,rn*math.cos(angle)),_scale(b,rb*math.sin(angle)))))
    for i in range(len(points)-1):
        for j in range(segments):
            k=(j+1)%segments
            faces.append((i*segments+j,i*segments+k,(i+1)*segments+k,(i+1)*segments+j))
            uvs.append(((j/segments,vs[i]),((j+1)/segments,vs[i]),((j+1)/segments,vs[i+1]),(j/segments,vs[i+1])))
            smooth.append(True)
    for i in (0,len(points)-1):
        centre=len(verts);verts.append(tuple(points[i]))
        for j in range(segments):
            k=(j+1)%segments;ids=(centre,i*segments+k,i*segments+j) if i==0 else (centre,i*segments+j,i*segments+k)
            faces.append(ids)
            uvs.append(tuple((.5,.5) if vi==centre else (.5+.5*math.cos((vi%segments)/segments*math.tau),.5+.5*math.sin((vi%segments)/segments*math.tau)) for vi in ids))
            smooth.append(False)
    return verts,faces,uvs,smooth
