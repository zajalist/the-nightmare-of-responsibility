"""Native-skin calibration and runtime offsets for the four screwdriver contacts."""
import copy,json
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation as R
from ue_hand import Hand,m,matrix
ROOT=Path('P:/FoA/Saved/AnimShots'); K=170/180
H=Hand(ROOT/'review/screwdriver_0_fixture.json')
assert H.check_native_capture()['max_mm']<.01
surface=json.loads((ROOT/'review/screwdriver_surface.json').read_text()); mesh=trimesh.Trimesh(surface['positions'],surface['triangles'],process=True)
if mesh.volume<0: mesh.invert()
BODY=R.from_euler('z',-90,degrees=True); FRAME=R.from_euler('x',45,degrees=True)
TIP=np.array([0,0,max(np.array(surface['positions'])[:,2])]); GRIP=np.array([-16,0,0])

def load(i,native=True):
 suffix='_native' if native else ''
 s=json.loads((ROOT/f'screwdriver_screw{i}{suffix}_solution.json').read_text()); p=copy.deepcopy(H.ref)
 for b,q in s['pose'].items():
  if b in p:p[b][1]=q
 w=H.world(p); delta=m.sub(s['hand_ue'][0],w['hand_r'][0]);p['pelvis'][0]=m.add(p['pelvis'][0],m.qrot(m.qinv(w[H.parents['pelvis']][1]),delta))
 return s,p

def distance(s,p):
 o=s['object_ue']; a=R.from_quat(o['quat']).inv().apply(H.skin(p)-o['loc'])/o['scale'];q,d,ids=trimesh.proximity.closest_point(mesh,a)
 d*=np.where(np.einsum('ij,ij->i',a-q,mesh.face_normals[ids])>=0,1,-1)*K*o['scale'][0]*10
 return {digit:float(min(d[k] for k,b in enumerate(H.dom) if b.startswith(digit+'_'))) for digit in ('hand','thumb','index','middle','ring','pinky')}

if __name__=='__main__':
 out=[]
 for i in range(4):
  source_index=i^1  # The twin numbers columns from the opposite side of the door.
  s,p=load(source_index);w=H.world(p);o=s['object_ue']; oq=BODY*R.from_quat(o['quat']);ol=BODY.apply(np.array(o['loc'])*K); os=np.array(o['scale'])*K
  tip=ol+oq.apply(TIP*os);hl=BODY.apply(np.array(w['hand_r'][0])*K)-tip;hq=BODY*R.from_quat(w['hand_r'][1]);el=BODY.apply(np.array(w['lowerarm_r'][0])*K)-tip
  loc=hq.inv().apply(GRIP-hl)/K; q=hq.inv()*FRAME
  assert np.linalg.norm(hl+hq.apply(loc*K)-GRIP)<1e-6
  assert (hq*q*FRAME.inv()).magnitude()<1e-6
  driverloc=-oq.apply(TIP*os)
  assert np.linalg.norm(driverloc+oq.apply(TIP*os))<1e-6
  row=dict(index=i,source=f'screwdriver_screw{source_index}_native_solution.json',grip_offset=[loc.tolist(),q.as_quat().tolist(),[1/K]*3],root_in_tip=(-tip).tolist(),elbow_in_frame=FRAME.inv().apply(el-GRIP).tolist(),driver_transform=[driverloc.tolist(),oq.as_quat().tolist(),os.tolist()],native_clearance_mm=distance(s,p))
  actual_tip=np.array([373.83,46.4+(4.2 if i%2 else 0),93-(9 if i>=2 else 0)])
  assert np.linalg.norm((actual_tip-tip)[:2]-[310.31610895,23])<.001
  print(i,row,flush=True);out.append(row)
 (ROOT/'screw_runtime.json').write_text(json.dumps(out,indent=2))
