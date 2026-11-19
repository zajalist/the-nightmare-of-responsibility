"""Offline source geometry comparison and actual palm surface landmarks; never saves source."""
import sys,json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
sys.path.insert(0,'P:/FoA/Tools/MPFB')
from load_teen import load_teen

rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
shirt=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
layered=np.array([v.co[:] for v in shirt.data.vertices])
body=bpy.data.objects['Human']
for p in rig.pose.bones:p.matrix_basis.identity()
for m in body.modifiers:
    if m.type in ('MASK','SUBSURF'):m.show_viewport=False
bpy.context.view_layer.update()
ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
report={'palms':{}}
for side in ('l','r'):
    bone=rig.data.bones['hand_'+side]; inv=bone.matrix_local.inverted()
    # Thumb-base protrudes toward palm, away from plane of wrist/index/pinky joints.
    index=inv@rig.data.bones['index_01_'+side].head_local
    pinky=inv@rig.data.bones['pinky_01_'+side].head_local
    thumb=inv@rig.data.bones['thumb_02_'+side].head_local
    normal=index.cross(pinky).normalized()
    if normal.dot(thumb)<0:normal=-normal
    gi=body.vertex_groups['hand_'+side].index;skin=body.vertex_groups['body'].index
    rows=[]
    for v in body.data.vertices:
        w={g.group:g.weight for g in v.groups}
        p=inv@mesh.vertices[v.index].co
        n=(inv.to_3x3()@mesh.vertices[v.index].normal).normalized()
        if w.get(gi,0)>.7 and w.get(skin,0)>0 and .035<p.y<.09 and n.dot(normal)>.65:
            rows.append((p,n,v.index))
    assert len(rows)>=5,(side,len(rows))
    p=sum((r[0] for r in rows),Vector())/len(rows)
    n=sum((r[1] for r in rows),Vector()).normalized()
    report['palms'][side]={'centroid_ue_cm':[p.x*100,-p.y*100,p.z*100],
        'normal_ue':[n.x,-n.y,n.z], 'vertices':[r[2] for r in rows],
        'thumb_plane_ue':[normal.x,-normal.y,normal.z]}
ev.to_mesh_clear()
body,rig=load_teen()
shirt=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
source=np.array([v.co[:] for v in shirt.data.vertices])
assert source.shape==layered.shape
delta=np.linalg.norm(layered-source,axis=1)*100
ix=np.argsort(delta)[-20:]
report['shirt']={'vertices':len(source),'layering_displacement_cm_percentiles':np.percentile(delta,[0,50,90,99,100]).tolist(),
    'worst':[{'vertex':int(i),'source':source[i].tolist(),'layered':layered[i].tolist(),'delta_cm':float(delta[i])} for i in ix]}
Path('P:/FoA/Saved/CharacterShots/mpfb/shirt_palm_diagnostic.json').write_text(json.dumps(report,indent=2))
print('DIAGNOSTIC',json.dumps(report))
