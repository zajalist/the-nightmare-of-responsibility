"""Measure a read-only user capture; proposes no unverified asset edits."""
import json, math, re
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

d=json.loads(Path('Saved/Integration/screwdriver_user_contact.json').read_text())
def xf(s):
    values=[float(v) for v in re.findall(r'[XYZW]=(-?[\d.]+)',s)]
    assert len(values)==10,values
    return Rotation.from_quat(values[:4]),np.array(values[4:7]),np.array(values[7:])
rotation,position,scale=xf(d['held_tool'])
_,target,_=xf(d['components']['ToolContact'])
tip_local=np.array([0,0,13.510257])
tip=position+rotation.apply(tip_local*scale)
axis=rotation.apply([0,0,1]);normal=np.array(d['door_forward'])
_,grip,grip_scale=xf(d['grip'])
shoulder,elbow,wrist=[np.array(d['bones'][n]) for n in ('upperarm_r','lowerarm_r','hand_r')]
upper,lower=shoulder-elbow,wrist-elbow
l1,l2=np.linalg.norm(upper),np.linalg.norm(lower)
flex=180-math.degrees(math.acos(np.clip(np.dot(upper,lower)/(l1*l2),-1,1)))
desired_flex=60.
distance=math.sqrt(l1*l1+l2*l2+2*l1*l2*math.cos(math.radians(desired_flex)))
delta=wrist-shoulder
parallel=np.dot(delta,normal)
side_sq=np.dot(delta,delta)-parallel*parallel
setback=math.sqrt(max(0,distance*distance-side_sq))-parallel
out=dict(capture_time=d['time'],tip_error_cm=float(np.linalg.norm(tip-target)),
    axis_error_deg=math.degrees(math.acos(np.clip(np.dot(axis,normal),-1,1))),
    grip_error_cm=float(np.linalg.norm(grip-np.array(d['grip_target']))),
    grip_world_scale=grip_scale.tolist(),reciprocal_grip_scale=(1/grip_scale).tolist(),
    upperarm_cm=l1,forearm_cm=l2,elbow_flex_deg=flex,reach_ratio=float(np.linalg.norm(delta)/(l1+l2)),
    proposed_additional_setback_cm=setback,proposed_local_stand_x=-50-setback,
    target_elbow_flex_deg=desired_flex,
    limitation='One actual screwdriver turn sample. Verify corrected stance across all four screws and full wrist cycle before accepting.')
Path('Saved/Integration/screwdriver_contact_measured.json').write_text(json.dumps(out,indent=1))
print(json.dumps(out,indent=1))
