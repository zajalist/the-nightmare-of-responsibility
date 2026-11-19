"""Carry the approved Blender scalp tint into a separate UE skin texture; no source blend writes.
Run with the hair blend in Blender, then run plain Python with `tint`.
"""
import sys
from pathlib import Path
import numpy as np

OUT=Path('P:/FoA-Assets/character/mpfb/export/hair')
if 'tint' in sys.argv:
    from PIL import Image
    source=Path('P:/FoA-Assets/character/mpfb/export/teen_cm/textures/T_Teen_young_lightskinned_male_diffuse_Freckles.png')
    image=Image.open(source).convert('RGBA')
    rgba=np.asarray(image).copy()
    mask=Image.fromarray((np.load(OUT/'scalp_mask.npy')*255).astype(np.uint8)).resize(image.size,Image.Resampling.BILINEAR)
    w=np.asarray(mask,dtype=np.float32)[...,None]/255
    srgb=rgba[...,:3]/255
    linear=np.where(srgb<=.04045,srgb/12.92,((srgb+.055)/1.055)**2.4)
    linear=linear*(1-w)+np.array([.02,.013,.008])*w
    srgb=np.where(linear<=.0031308,linear*12.92,1.055*linear**(1/2.4)-.055)
    tinted=np.clip(np.rint(srgb*255),0,255).astype(np.uint8)
    changed=np.asarray(mask)>0
    rgba[...,:3][changed]=tinted[changed]
    assert np.array_equal(rgba[~changed],np.asarray(image)[~changed]), 'Untinted skin pixels changed'
    Image.fromarray(rgba).save(OUT/'T_Teen_Skin_Groom.png')
    mask.save(OUT/'T_Teen_ScalpMask.png')
    assert (np.asarray(mask)>0).sum()>1000
    print('SCALP_TEXTURE',OUT/'T_Teen_Skin_Groom.png')
else:
    import bpy
    body=bpy.data.objects['Human']
    mesh=body.data
    attr=mesh.color_attributes['FoA_scalp']
    weights=np.array([c.color[0] for c in attr.data])
    skin=body.vertex_groups['body'].index
    valid={v.index for v in mesh.vertices if any(g.group==skin and g.weight>0 for g in v.groups)}
    mesh.calc_loop_triangles()
    uv=mesh.uv_layers.active.data
    size=2048
    mask=np.zeros((size,size),dtype=np.float32)
    for tri in mesh.loop_triangles:
        if not set(tri.vertices)<=valid or weights[list(tri.vertices)].max()==0:
            continue
        p=np.array([uv[i].uv[:] for i in tri.loops])*size
        p[:,1]=size-p[:,1]
        lo=np.maximum(np.floor(p.min(0)).astype(int),0)
        hi=np.minimum(np.ceil(p.max(0)).astype(int),size-1)
        if np.any(lo>hi):continue
        y,x=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        a,b,c=p
        denominator=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(denominator)<1e-8:continue
        u=((b[1]-c[1])*(x+.5-c[0])+(c[0]-b[0])*(y+.5-c[1]))/denominator
        v=((c[1]-a[1])*(x+.5-c[0])+(a[0]-c[0])*(y+.5-c[1]))/denominator
        w=1-u-v
        value=u*weights[tri.vertices[0]]+v*weights[tri.vertices[1]]+w*weights[tri.vertices[2]]
        value=np.where((u>=0)&(v>=0)&(w>=0),value,0)
        mask[lo[1]:hi[1]+1,lo[0]:hi[0]+1]=np.maximum(mask[lo[1]:hi[1]+1,lo[0]:hi[0]+1],value)
    assert (mask>.5).sum()>1000
    np.save(OUT/'scalp_mask.npy',mask)
    print('SCALP_MASK',int((mask>0).sum()),'pixels')
