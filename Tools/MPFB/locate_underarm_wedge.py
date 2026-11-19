"""Project exact skinned source vertices into the measured wake camera to locate the notch."""
import bpy,numpy as np,json,sys,math
from pathlib import Path
from mathutils import Matrix
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from sleep_skin_contact import matrix
folder=Path('P:/FoA/Saved/CharacterShots/wake_handoff/20261108_111013')
pose=json.loads((folder/'bed_edge_body_pose.json').read_text())
ref=np.load('P:/FoA/Saved/WakeUp/teen_body_full_skin_cache.npz');refs=dict(zip(ref['bone_names'].tolist(),ref['reference_matrices']))
B=np.diag([100,-100,100,1]);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');shirt=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
poses={r['name']:matrix(r['position'],r['rotation'],r['scale']) for r in pose['bones']}
for bone in rig.pose.bones:
    name='root' if bone.name=='Root' else bone.name
    if name in refs:
        bone.matrix=Matrix((np.linalg.inv(B)@poses[name]@np.linalg.inv(refs[name])@B).tolist())@bone.bone.matrix_local
        bpy.context.view_layer.update()
sm=shirt.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
world=matrix(pose['world']['position'],pose['world']['rotation'],pose['world']['scale'])
row=json.loads((folder/'evidence.json').read_text())['rows'][-1];eye=np.array(row['camera']);yaw=math.radians(-21.601507);pitch=math.radians(-1.141632)
forward=np.array([math.cos(pitch)*math.cos(yaw),math.cos(pitch)*math.sin(yaw),math.sin(pitch)]);right=np.array([-math.sin(yaw),math.cos(yaw),0]);up=np.cross(forward,right)
rows=[]
for v,base in zip(sm.vertices,shirt.data.vertices):
    if not(.13<abs(base.co.x)<.25 and 1.3<base.co.z<1.5):continue
    q=(world@B@np.r_[np.array(v.co),1])[:3]-eye
    sx=960+np.dot(q,right)/np.dot(q,forward)*2133.333;sy=540-np.dot(q,up)/np.dot(q,forward)*2133.333
    if 570<sx<750 and 620<sy<790:rows.append(dict(id=v.index,pixel=[sx,sy],rest_cm=[x*100 for x in base.co]))
out=Path('P:/FoA/Saved/Integration/cinematic_audit/underarm_weights_candidate/wedge_projection.json');out.write_text(json.dumps(rows,indent=2))
print(rows)
