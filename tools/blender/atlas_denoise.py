"""Fast OIDN study on isolated UV charts, preserving small charts and alpha.

Runs inside Blender; uses its bundled OIDN, without downloads or preferences.
Each filter input contains just one chart, so unrelated surfaces cannot bleed
into one another. Beauty-only filtering needs visual review of material detail.
"""
import ctypes
import os
import time
from pathlib import Path

import numpy as np


def uv_charts(mesh):
    uv = mesh.uv_layers.active.data
    parent = list(range(len(mesh.polygons)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    edges = {}
    for face in mesh.polygons:
        points = [tuple(round(float(x), 7) for x in uv[i].uv) for i in face.loop_indices]
        for a, b in zip(points, points[1:]+points[:1]):
            key = tuple(sorted((a,b)))
            if key in edges: parent[find(face.index)] = find(edges[key])
            else: edges[key] = face.index
    return [find(face.index) for face in mesh.polygons]


def snap_to_texels(mesh, size):
    """Snap complete charts to texel centres; retain charts that would collapse."""
    mesh.calc_loop_triangles()
    uv=mesh.uv_layers.active.data
    groups=uv_charts(mesh)
    original=np.array([loop.uv[:] for loop in uv],dtype=np.float64)
    snapped=original.copy()
    rejected=set()
    # Move boundaries inward, rather than expanding both sides of a gutter
    # onto the same texel. The collision check below also protects concave
    # charts whose internal vertices cannot be classified by a bounding box.
    for group in set(groups):
        indices=[i for face in mesh.polygons if groups[face.index]==group for i in face.loop_indices]
        points=original[indices]*size
        centre=(points.min(axis=0)+points.max(axis=0))/2
        quantized=np.where(points>centre,np.floor(points-.5)+.5,np.ceil(points-.5)+.5)
        if np.any(quantized<points.min(axis=0)-1e-6) or np.any(quantized>points.max(axis=0)+1e-6):
            rejected.add(group)
        snapped[indices]=np.clip(quantized,.5,size-.5)/size
    for tri in mesh.loop_triangles:
        a,b,c=original[list(tri.loops)]*size
        x,y,z=snapped[list(tri.loops)]*size
        before=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        after=(y[0]-x[0])*(z[1]-x[1])-(y[1]-x[1])*(z[0]-x[0])
        if abs(after)<.01 or before*after<=0:rejected.add(groups[tri.polygon_index])
    # Rounding can close a narrow gutter even when each triangle stays valid.
    # Reject both charts if they would newly share a texel; never glue charts
    # together or let a later bake overwrite another surface at that boundary.
    baseline=set()
    chart_labels(mesh,size,coordinates=original,groups=groups,conflicts=baseline)
    while True:
        proposed=snapped.copy()
        for face in mesh.polygons:
            if groups[face.index] in rejected:
                proposed[list(face.loop_indices)]=original[list(face.loop_indices)]
        collisions=set()
        chart_labels(mesh,size,coordinates=proposed,groups=groups,conflicts=collisions)
        new={chart for pair in collisions-baseline for chart in pair}-rejected
        if not new:break
        rejected.update(new)
    for face in mesh.polygons:
        if groups[face.index] not in rejected:
            for i in face.loop_indices:uv[i].uv=snapped[i]
    mesh.update()
    return {'method':'UV boundaries inward to texel centres; preserve chart on collapse, flip or new shared texels',
        'alignedCharts':len(set(groups)-rejected),'preservedUnsafeCharts':len(rejected),
        'existingSharedTexelPairs':len(baseline),'newSharedTexelPairs':len(collisions-baseline),'atlasSize':size}


def chart_labels(mesh, size, *, coordinates=None, groups=None, conflicts=None):
    mesh.calc_loop_triangles()
    uv=mesh.uv_layers.active.data
    if groups is None:groups=uv_charts(mesh)
    labels = np.full((size,size), -1, dtype=np.int32)
    for tri in mesh.loop_triangles:
        pts = (np.array([uv[i].uv[:] for i in tri.loops]) if coordinates is None else coordinates[list(tri.loops)])*size
        low = np.maximum(0,np.floor(pts.min(axis=0)).astype(int))
        high = np.minimum(size-1,np.ceil(pts.max(axis=0)).astype(int))
        x0,y0=low; x1,y1=high
        if x1<x0 or y1<y0: continue
        gx,gy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
        a,b,c=pts
        d=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(d)<1e-12: continue
        w1=((b[1]-c[1])*(gx-c[0])+(c[0]-b[0])*(gy-c[1]))/d
        w2=((c[1]-a[1])*(gx-c[0])+(a[0]-c[0])*(gy-c[1]))/d
        view=labels[y0:y1+1,x0:x1+1]
        mask=(w1>=0)&(w2>=0)&(w1+w2<=1)
        label=groups[tri.polygon_index]
        if conflicts is not None:
            for other in np.unique(view[mask & (view>=0) & (view!=label)]):
                conflicts.add(tuple(sorted((int(other),label))))
        view[mask]=label
    return labels


class Oidn:
    def __init__(self):
        import bpy
        install=Path(bpy.app.binary_path).parent
        directory=install/'blender.shared'
        if os.name!='nt':
            candidates=sorted(install.glob('lib/libOpenImageDenoise.so*'))
            if not candidates:raise RuntimeError('Bundled OIDN library missing from Blender installation')
            directory=candidates[0].parent
        self.directory=os.add_dll_directory(str(directory)) if os.name=='nt' else None
        self.api=ctypes.CDLL(str(directory/'OpenImageDenoise.dll') if os.name=='nt' else str(candidates[0]))
        P=ctypes.c_void_p; I=ctypes.c_int; S=ctypes.c_size_t; C=ctypes.c_char_p
        specs={'oidnNewDevice':([I],P),'oidnCommitDevice':([P],None),
            'oidnNewFilter':([P,C],P),'oidnSetSharedFilterImage':([P,C,P,I,S,S,S,S,S],None),
            'oidnSetFilterBool':([P,C,ctypes.c_bool],None),'oidnSetFilterInt':([P,C,I],None),
            'oidnCommitFilter':([P],None),'oidnExecuteFilter':([P],None),
            'oidnGetDeviceError':([P,ctypes.POINTER(C)],I),
            'oidnReleaseFilter':([P],None),'oidnReleaseDevice':([P],None)}
        for name,(args,result) in specs.items():
            fn=getattr(self.api,name);fn.argtypes=args;fn.restype=result
        # CPU shared buffers avoid device-copy overhead for many small charts.
        self.device=self.api.oidnNewDevice(1);self.api.oidnCommitDevice(self.device)
        self.filter=self.api.oidnNewFilter(self.device,b'RT')
        self.api.oidnSetFilterBool(self.filter,b'hdr',True)
        self.api.oidnSetFilterInt(self.filter,b'quality',4) # OIDN_QUALITY_FAST
        self.check()
    def check(self):
        message=ctypes.c_char_p()
        if self.api.oidnGetDeviceError(self.device,ctypes.byref(message)):
            raise RuntimeError(f'OIDN: {message.value!r}')
    def run(self, color):
        color=np.ascontiguousarray(color,dtype=np.float32);output=np.empty_like(color)
        h,w=color.shape[:2]
        for name,array in ((b'color',color),(b'output',output)):
            self.api.oidnSetSharedFilterImage(self.filter,name,array.ctypes.data,3,w,h,0,0,0)
        self.api.oidnCommitFilter(self.filter);self.api.oidnExecuteFilter(self.filter);self.check()
        return output
    def close(self):
        self.api.oidnReleaseFilter(self.filter);self.api.oidnReleaseDevice(self.device)
        if self.directory:self.directory.close()


def denoise(image, mesh):
    start=time.perf_counter();w,h=image.size
    if w!=h:raise ValueError('Atlas must be square')
    raw=np.empty(w*h*4,dtype=np.float32);image.pixels.foreach_get(raw)
    pixels=raw.reshape(h,w,4);result=pixels.copy();labels=chart_labels(mesh,w)
    worker=Oidn();filtered=0;untouched=0;texels=0
    try:
        for label in np.unique(labels):
            if label<0:continue
            yy,xx=np.where(labels==label)
            # Tiny joinery charts retain the exact bake rather than being blurred.
            if len(xx)<256 or np.ptp(xx)<7 or np.ptp(yy)<7:
                untouched+=1;continue
            x0,x1=int(xx.min()),int(xx.max())+1;y0,y1=int(yy.min()),int(yy.max())+1
            mask=labels[y0:y1,x0:x1]==label
            colors=pixels[y0:y1,x0:x1,:3]
            # All padding comes from this chart; no neighbouring chart enters OIDN.
            isolated=np.empty_like(colors);isolated[:]=colors[mask].mean(axis=0);isolated[mask]=colors[mask]
            padded=np.pad(isolated,((16,16),(16,16),(0,0)),mode='edge')
            clean=worker.run(padded)[16:-16,16:-16]
            result[y0:y1,x0:x1,:3][mask]=clean[mask]
            filtered+=1;texels+=len(xx)
    finally:worker.close()
    if not np.isfinite(result).all():raise RuntimeError('Non-finite denoised atlas')
    image.pixels.foreach_set(result.reshape(-1));image.update()
    return {'method':'OIDN RT FAST CPU; isolated UV charts; beauty only',
        'seconds':time.perf_counter()-start,'filteredCharts':filtered,
        'preservedSmallCharts':untouched,'filteredTexels':texels,'alphaUnchanged':bool(np.array_equal(pixels[:,:,3],result[:,:,3]))}
