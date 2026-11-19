"""Head skin + accessory envelope in neck-local UE centimetres for animated bounds."""
import bpy,json,numpy as np
from pathlib import Path
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for p in rig.pose.bones:p.matrix_basis.identity()
body=bpy.data.objects['Human']
for m in body.modifiers:
    if m.type in ('MASK','SUBSURF'):m.show_viewport=False
bpy.context.view_layer.update()
inv=rig.data.bones['neck_01'].matrix_local.inverted();points=[]
for obj in bpy.data.objects:
    if obj.type!='MESH':continue
    if obj!=body and not any(token in obj.name.lower() for token in ('short01','eyebrow','eyelash','high-poly','teeth','tongue')):continue
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
    if obj==body:
        hg=body.vertex_groups['head'].index;sg=body.vertex_groups['body'].index
        indexes=[]
        for v in body.data.vertices:
            w={g.group:g.weight for g in v.groups}
            if w.get(hg,0)>.5 and w.get(sg,0)>0:indexes.append(v.index)
    else:indexes=range(len(mesh.vertices))
    for i in indexes:
        p=inv@(obj.matrix_world@mesh.vertices[i].co);points.append((p.x*100,-p.y*100,p.z*100))
    ev.to_mesh_clear()
points=np.array(points);center=(points.min(0)+points.max(0))*.5
radius=float(np.linalg.norm(points-center,axis=1).max())+1
report={'bone':'neck_01','center_cm':center.tolist(),'radius_cm':radius,'vertices':len(points),
        'minimum_cm':points.min(0).tolist(),'maximum_cm':points.max(0).tolist()}
Path('P:/FoA/Saved/CharacterShots/mpfb/head_bounds_envelope.json').write_text(json.dumps(report,indent=2))
print('HEAD_ENVELOPE',json.dumps(report))
