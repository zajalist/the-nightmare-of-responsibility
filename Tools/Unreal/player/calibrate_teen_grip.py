"""Transfer the accepted MH grip through homologous hand axes, including the imported Teen bone scale."""
import json, math, re, sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal/wakeup')
import wake_math as m
import unreal
old=json.loads(Path('P:/FoA/Saved/AnimShots/screwdriver/hand_frames.json').read_text())['mh']
frame=json.loads(Path('P:/FoA/Saved/AnimShots/teen_hand_frame.json').read_text())
new=frame['bones']
bone_scale=float(re.search(r'Scale3D=\(X=([^,]+)',frame['hand']).group(1))
# The reference skeleton is unit scale; the shipping visual hierarchy is 170/180.
# Cancel inherited component scale in the grip frame so inverse-frame hand IK and
# the screwdriver's authored tip distance use the same world-space centimetres.
bp=unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
cdo=unreal.get_default_object(bp.generated_class())
visual_scale=cdo.get_editor_property('Mesh').get_editor_property('relative_scale3d')
assert max(visual_scale.to_tuple())-min(visual_scale.to_tuple())<.0001,visual_scale
world_bone_scale=bone_scale*visual_scale.x
h=old['hand_r']
def old_local(name):
    d=m.sub(old[name]['loc'],h['loc'])
    return tuple(m.dot(d,h[a]) for a in ('x','y','z'))
of=old_local('middle_01_r'); ot=m.sub(old_local('index_01_r'),old_local('pinky_01_r'))
nf=new['middle_01_r']['local']; nt=m.sub(new['index_01_r']['local'],new['pinky_01_r']['local'])
align=m.align(of,ot,nf,nt)
ratio=m.length(nf)*bone_scale/m.length(of)
# Skin-weighted palm centroid from the shipped Teen mesh; move a handle radius toward its palm-facing normal.
palm=(-1.38939,-6.63917,-.729523)
normal=m.norm(m.cross(nf,nt))
pos=m.mul(m.add(palm,m.mul(normal,1.2)),1/bone_scale)
q=unreal.Rotator(roll=0,pitch=20,yaw=180).quaternion()
rot=m.qnorm(m.qmul(align,(q.x,q.y,q.z,q.w)))
out=dict(location=pos,rotation=rot,scale=(1/world_bone_scale,)*3,palm_size_ratio=ratio,
         reference_bone_scale=bone_scale,visual_hierarchy_scale=visual_scale.x)
assert .7<ratio<1.6 and 4<m.length(pos)*bone_scale<20,out
Path('P:/FoA/Saved/AnimShots/teen_grip_calibration.json').write_text(json.dumps(out,indent=1))
print(out)
