"""Offline expected rigid scalp envelope in the measured UE sleeping pose."""
import json,sys
from pathlib import Path
import bpy,numpy as np
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from sleep_skin_contact import matrix
p=json.loads(Path('P:/FoA/Saved/WorldShots/chair_nightmare/body_pose.json').read_text())
h=next(b for b in p['bones'] if b['name']=='head');w=p['world']
ref=matrix([0,4.915108,171.702376],[.699010,0,0,-.715111])
xf=matrix(w['position'],w['rotation'],w['scale'])@matrix(h['position'],h['rotation'],h['scale'])
g=bpy.data.objects['basic_short_hair'];v=np.empty(len(g.data.points)*3,np.float32);g.data.points.foreach_get('position',v)
v=v.reshape(-1,3)*[100,-100,100];local=np.c_[v,np.ones(len(v))]@np.linalg.inv(ref).T;world=local@xf.T
eye=np.array([258,35,105]);aim=np.array([258,-191,64]);forward=aim-eye;forward=forward/np.linalg.norm(forward)
right=np.cross([0,0,1],forward);right=right/np.linalg.norm(right);up=np.cross(forward,right)
q=world[:,:3]-eye;depth=q@forward;f=1280/(2*np.tan(np.deg2rad(65/2)))
uv=np.c_[640+(q@right)*f/depth,480-(q@up)*f/depth]
out=Path('P:/FoA/Saved/CharacterShots/groom_pose');out.mkdir(parents=True,exist_ok=True)
np.savez_compressed(out/'rigid_groom_head_local_cm.npz',local=local[:,:3])
report={'source':bpy.data.filepath,'world_min':world[:,:3].min(0).tolist(),'world_max':world[:,:3].max(0).tolist(),'whole_sleep_expected_pixels_min':uv.min(0).tolist(),'whole_sleep_expected_pixels_max':uv.max(0).tolist(),'points':len(v),'caveat':'Expected rigid scalp geometry; actual cast shadows may extend outside this envelope.'}
(out/'expected_envelope.json').write_text(json.dumps(report,indent=1));print('GROOM_ENVELOPE',json.dumps(report))
