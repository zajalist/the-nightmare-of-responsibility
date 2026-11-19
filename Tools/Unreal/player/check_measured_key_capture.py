"""Post-apply proof: actual skin pinch, seated key tip and turning shaft alignment."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

capture=json.loads(Path('Saved/Integration/key_pinch_capture.json').read_text())
measured=json.loads(Path('Saved/Integration/key_pinch_measured.json').read_text())
assert capture['reason']=='captured_three_actual_key_poses'
assert capture.get('early_cancel') and all(capture['early_cancel'].values()),'Early hand-settle cancel was not proved'
assert [r['angle'] for r in capture['rows']]==[0,18,42]
results=[]
for row,pad in zip(capture['rows'],measured['poses']):
    assert row['label']==pad['label']
    assert Path(row['Body'])==Path(pad['source_pose']),'Measure the new capture before checking it'
    key=row['key'];r=Rotation.from_quat(key['rotation'])
    tip=np.array(key['position'])+r.apply(np.array([row['key_local_bounds'][1][0],0,0])*key['scale'])
    contact=row['contact'];contact_axis=Rotation.from_quat(contact['rotation']).apply([1,0,0])
    axis=r.apply([1,0,0]);angle=float(np.degrees(np.arccos(np.clip(np.dot(axis,contact_axis),-1,1))))
    error=float(np.linalg.norm(tip-contact['position']))
    assert error<.05,(row['label'],'key tip',error)
    assert angle<.1,(row['label'],'key shaft axis',angle)
    assert pad['target_error_cm']<.2,(row['label'],'skin pinch misses bow',pad['target_error_cm'])
    assert .30<pad['pad_gap_cm']<.37,(row['label'],'pinch gap',pad['pad_gap_cm'])
    results.append(dict(label=row['label'],tip_error_cm=error,axis_error_deg=angle,
        skin_pinch_error_cm=pad['target_error_cm'],pad_gap_cm=pad['pad_gap_cm']))
Path('Saved/Integration/key_pinch_contact_proof.json').write_text(json.dumps(dict(
    result='actual_three_pose_contact_passed',poses=results,
    limitation='Rendered seated, pressure and bound images still require visual review; cancellation and full solve are separate tests.'),indent=1))
print(json.dumps(results,indent=1))
