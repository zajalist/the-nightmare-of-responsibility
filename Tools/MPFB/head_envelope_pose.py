"""Offline rigid head skin/groom envelope in the latest measured sleeping pose."""
import sys,json
from pathlib import Path
import bpy,numpy as np
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from sleep_skin_contact import matrix
body=bpy.data.objects['Human'];hg=body.vertex_groups['head'].index;sg=body.vertex_groups['body'].index
points=[]
for v in body.data.vertices:
    w={g.group:g.weight for g in v.groups}
    if w.get(hg,0)>.99 and w.get(sg,0)>0:
        p=body.matrix_world@v.co;points.append((p.x*100,-p.y*100,p.z*100,1))
points=np.array(points);reference=matrix([0,4.915108,171.702376],[.699010,0,0,-.715111])
local=points@np.linalg.inv(reference).T
path=Path('P:/FoA/Saved/AnimShots/wake_sleep_body_pose.json');pose=json.loads(path.read_text())
head=next(b for b in pose['bones'] if b['name']=='head');world=pose['world']
xf=matrix(world['position'],world['rotation'],world['scale'])@matrix(head['position'],head['rotation'],head['scale'])
posed=local@xf.T
groom=bpy.data.objects['basic_short_hair'];gp=np.empty(len(groom.data.points)*3,dtype=np.float32);groom.data.points.foreach_get('position',gp)
gp=gp.reshape(-1,3)*np.array([100,-100,100]);gp=np.column_stack([gp,np.ones(len(gp))])
hair=(gp@np.linalg.inv(reference).T)@xf.T
report={'pose':str(path),'skin_vertices':len(points),'skin_min_cm':posed[:,:3].min(0).tolist(),'skin_max_cm':posed[:,:3].max(0).tolist(),
        'hair_min_cm':hair[:,:3].min(0).tolist(),'hair_max_cm':hair[:,:3].max(0).tolist(),
        'headward_skin_vertex_cm':posed[np.argmax(posed[:,0]),:3].tolist(),'neck_or_blended_vertices_excluded':True}
folder=Path('P:/FoA/Saved/CharacterShots/mpfb/portrait_face')
np.savez_compressed(folder/'rigid_head_local_cm.npz',local=local[:,:3])
(folder/'sleep_head_envelope.json').write_text(json.dumps(report,indent=2));print('HEAD_POSE_ENVELOPE',json.dumps(report))
