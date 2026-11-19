"""Read-only rigid skull surface measurement in a captured Teen sleeping pose."""
import json
from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from sleep_skin_contact import matrix

rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for p in rig.pose.bones:
    p.matrix_basis.identity()
body=bpy.data.objects['Human']
for m in body.modifiers:
    if m.type in ('MASK','SUBSURF'):
        m.show_viewport=False
bpy.context.view_layer.update()
evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
mesh=evaluated.to_mesh()
head_group=body.vertex_groups['head'].index
skin_group=body.vertex_groups['body'].index
points=[]
for v in body.data.vertices:
    weights={g.group:g.weight for g in v.groups}
    p=body.matrix_world @ mesh.vertices[v.index].co
    if weights.get(head_group,0)>.99 and weights.get(skin_group,0)>0 and p.y>.02 and p.z>1.72:
        points.append((p.x*100,-p.y*100,p.z*100,1))
evaluated.to_mesh_clear()
points=np.asarray(points)
assert len(points)>=10,len(points)
reference=matrix([0,4.915108,171.702376],[.699010,0,0,-.715111])
local=points@np.linalg.inv(reference).T
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
pose_path=Path(args[0] if args else 'P:/FoA/Saved/CharacterShots/sleep_side/20261108_014056/body_pose.json')
pose=json.loads(pose_path.read_text())
head=next(b for b in pose['bones'] if b['name']=='head')
world=pose['world']
posed=local@(matrix(world['position'],world['rotation'],world['scale'])@matrix(head['position'],head['rotation'],head['scale'])).T
i=posed[:,2].argmin()
report={'pose':str(pose_path),'rigid_occiput_vertices':len(points),'lowest_world_cm':posed[i,:3].tolist(),'head_local_point_cm':local[i,:3].tolist(),
        'reference_points_local_cm':local[:,:3].tolist(),
        'world_z_range_cm':[float(posed[:,2].min()),float(posed[:,2].max())]}
Path('P:/FoA/Saved/CharacterShots/mpfb/sleep_occiput_contact.json').write_text(json.dumps(report,indent=2))
print('SLEEP_OCCIPUT',json.dumps(report))
