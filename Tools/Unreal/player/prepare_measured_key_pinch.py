"""Offline calibration from the captured, skinned Teen pinch and actual key triangles."""
import json
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation

report=json.loads(Path('Saved/Integration/key_pinch_measured.json').read_text())
poses=report['poses'];assert len(poses)==3 and all(p['key_grip'] and p['grip_weight']==1 for p in poses)
offset=np.mean([p['actual_pinch_hand_local'] for p in poses],axis=0)
assert np.max(np.linalg.norm(np.array([p['actual_pinch_hand_local'] for p in poses])-offset,axis=1))<.001
rotation=Rotation.from_quat(poses[1]['measured_grip_rotation'])
roll,pitch,yaw=rotation.as_euler('xyz',degrees=True)
scale=np.mean([p['hand_world_scale'] for p in poses],axis=0)

# Pinch the solid front edge of the bow, not the thick shaft collar or empty hole.
mesh=trimesh.load('P:/FoA-Assets/lux3d/door_key/textured.glb',force='mesh')
vertices=mesh.vertices[:,[0,2,1]]*100;vertices[:,1]*=-1
tri=vertices[mesh.faces];a=tri[:,0][:,[0,2]];b=tri[:,1][:,[0,2]]-a;c=tri[:,2][:,[0,2]]-a
det=b[:,0]*c[:,1]-b[:,1]*c[:,0];valid=np.abs(det)>1e-12
bow_x=-2.8;q=np.array([bow_x,0])-a;u=np.zeros(len(tri));v=u.copy()
u[valid]=(q[valid,0]*c[valid,1]-q[valid,1]*c[valid,0])/det[valid]
v[valid]=(b[valid,0]*q[valid,1]-b[valid,1]*q[valid,0])/det[valid]
hit=valid&(u>=0)&(v>=0)&(u+v<=1)
y=tri[hit,0,1]+u[hit]*(tri[hit,1,1]-tri[hit,0,1])+v[hit]*(tri[hit,2,1]-tri[hit,0,1])
key_scale=7.5/11
thickness=float(np.ptp(y)*key_scale);gap=float(np.mean([p['pad_gap_cm'] for p in poses]))
assert 0 < gap-thickness < .03,(gap,thickness)
result=dict(location=offset.tolist(),rotation=rotation.as_quat().tolist(),
    rotation_degrees=dict(Pitch=float(-pitch),Yaw=float(yaw),Roll=float(-roll)),
    scale=(1/scale).tolist(),key_grip_distance_cm=(5.5-bow_x)*key_scale,
    measured_pad_gap_cm=gap,key_bow_thickness_cm=thickness,
    method='Captured Teen skin pad midpoint/normal, measured hand world scale, actual GLB bow triangle intersection',
    calibration_capture='Saved/Integration/key_pinch_capture.json',live_verified=False)
Path('Saved/AnimShots/teen_key_pinch_measured_calibration.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
