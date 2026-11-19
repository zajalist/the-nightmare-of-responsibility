"""Measure actual skinned fingertip pads from the owned key capture, not bone tips."""
import json, sys
from pathlib import Path
import numpy as np
from scipy.spatial.distance import cdist
from scipy.spatial.transform import Rotation
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from sleep_skin_contact import skin, matrix

report=json.loads(Path('Saved/Integration/key_pinch_capture.json').read_text())
assert report['reason']=='captured_three_actual_key_poses',report
results=[]
existing=json.loads(Path('Saved/AnimShots/teen_key_grip_calibration.json').read_text())
old_frame=Rotation.from_quat(existing['rotation']).as_matrix()
for row in report['rows']:
    path=Path(row['Body']);pose=json.loads(path.read_text());bones={b['name']:b for b in pose['bones']}
    w=pose['world'];world=matrix(w['position'],w['rotation'],w['scale'])
    def bone(name):
        b=bones[name];return world@matrix(b['position'],b['rotation'],b['scale'])
    points,cache,meta=skin(path,'P:/FoA/Saved/WakeUp/teen_body_full_skin_cache.npz')
    assert not meta['fallback'],meta
    names=cache['bone_names'].tolist()
    weights={finger:np.zeros(len(points)) for finger in ('index','thumb')}
    for i in range(len(points)):
        lo,hi=cache['vertex_offsets'][i:i+2]
        for b,v in zip(cache['weight_bones'][lo:hi],cache['weight_values'][lo:hi]):
            for finger in weights:
                if names[b]==finger+'_03_r':weights[finger][i]+=v
    pads={}
    for finger in weights:
        patch=points[weights[finger]>.5]
        joint=bone(finger+'_03_r')[:3,3];prior=bone(finger+'_02_r')[:3,3]
        direction=joint-prior;direction/=np.linalg.norm(direction)
        extension=(patch-joint)@direction
        pads[finger]=patch[extension>max(.1,extension.max()*.45)]
        assert len(pads[finger])>=4,(finger,len(pads[finger]))
    distances=cdist(pads['index'],pads['thumb'])
    i,j=np.unravel_index(distances.argmin(),distances.shape)
    index,thumb=pads['index'][i],pads['thumb'][j];middle=(index+thumb)/2
    hand=bone('hand_r');offset=(np.linalg.inv(hand)@np.r_[middle,1])[:3]
    # Keep the existing approach direction while aligning the pad-to-pad axis
    # with the key bow's thin local Y axis. Choose the nearer wrist orientation.
    normal=np.linalg.solve(hand[:3,:3],index-thumb);normal/=np.linalg.norm(normal)
    if np.dot(normal,old_frame[:,1])<0:normal=-normal
    forward=old_frame[:,0]-normal*np.dot(old_frame[:,0],normal);forward/=np.linalg.norm(forward)
    up=np.cross(forward,normal)
    frame=np.column_stack((forward,normal,up))
    result=dict(label=row['label'],source_pose=str(path),angle=row['angle'],key_grip=row['key_grip'],grip_weight=row['grip_weight'],
        pad_gap_cm=float(distances[i,j]),index_pad=index.tolist(),thumb_pad=thumb.tolist(),
        actual_pinch_world=middle.tolist(),actual_pinch_hand_local=offset.tolist(),
        measured_grip_rotation=Rotation.from_matrix(frame).as_quat().tolist(),
        wrist_frame_correction_deg=Rotation.from_matrix(frame@old_frame.T).magnitude()*180/np.pi,
        target_error_cm=float(np.linalg.norm(middle-np.array(row['grip_target']))),
        hand_world_scale=np.linalg.norm(hand[:3,:3],axis=0).tolist())
    results.append(result)
out=dict(source='Actual captured Teen pose skinned with unchanged canonical Body vertex weights',poses=results)
Path('Saved/Integration/key_pinch_measured.json').write_text(json.dumps(out,indent=1));print(json.dumps(out,indent=1))
