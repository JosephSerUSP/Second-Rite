"""Pure placement checks over measured geometry, shared by scaffold authoring.

Protected volumes are author-declared design constraints, not runtime collision.
Support rectangles are measured horizontal faces, not whole-object bounding boxes.
"""
import math


def checked_bounds(bounds, field):
    if (len(bounds) != 2 or any(len(v) != 3 for v in bounds) or
            any(not isinstance(v, (int,float)) or not math.isfinite(v) for p in bounds for v in p) or
            any(b<a for a,b in zip(*bounds))):
        raise ValueError(f'{field}: expected finite ordered XYZ bounds')
    return bounds


def translated(bounds, offset):
    return [[v+d for v,d in zip(point,offset)] for point in bounds]


def on_surface(child, surface, offset, field):
    checked_bounds(child, field)
    checked_bounds(surface, field+'.support')
    if len(offset)!=2 or any(not math.isfinite(v) for v in offset):
        raise ValueError(f'{field}.offset: expected two finite metres')
    centre=[(a+b)/2 for a,b in zip(*child)]
    target=[(a+b)/2+d for a,b,d in zip(surface[0][:2],surface[1][:2],offset)]
    delta=[target[0]-centre[0],target[1]-centre[1],surface[1][2]-child[0][2]]
    result=translated(child,delta)
    if any(result[0][i]<surface[0][i]-1e-5 or result[1][i]>surface[1][i]+1e-5 for i in (0,1)):
        raise ValueError(f'{field}: furnishing footprint extends beyond support rectangle')
    return delta


def beside(child, target, axis, side, gap, field):
    checked_bounds(child, field)
    checked_bounds(target, field+'.target')
    if axis not in ('x','y') or side not in (-1,1) or not math.isfinite(gap) or gap<0:
        raise ValueError(f'{field}: beside needs x/y, side -1/1 and nonnegative gap')
    i=0 if axis=='x' else 1
    delta=[(a+b-c-d)/2 for a,b,c,d in zip(target[0],target[1],child[0],child[1])]
    delta[2]=-child[0][2]  # beside is floor-standing, never inferred atop a target
    delta[i]=(target[1][i]+gap-child[0][i]) if side==1 else (target[0][i]-gap-child[1][i])
    return delta


def assert_keep_clear(bounds, protected, field):
    checked_bounds(bounds,field)
    for name, volume in protected.items():
        checked_bounds(volume,'keepClear.'+name)
        if all(min(bounds[1][i],volume[1][i])-max(bounds[0][i],volume[0][i])>1e-5 for i in range(3)):
            raise ValueError(f'{field}: enters protected volume keepClear.{name}')
