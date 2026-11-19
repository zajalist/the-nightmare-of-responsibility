"""Fit the key's thumb on the captured UE skin, keeping its verified stance and other fingers."""
import copy
import json
from pathlib import Path
import numpy as np
import trimesh
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R
from ue_hand import Hand, matrix

ROOT = Path('P:/FoA/Saved/AnimShots')
H = Hand(ROOT/'review/key_before_native_fixture.json')
print('UE calibration',H.check_native_capture(),flush=True)
LIVE = H.data['live']['local']
xf = np.linalg.inv(matrix(H.data['live']['phone_world'])) @ matrix(H.data['live']['body_world'])
surface = json.loads((ROOT/'review/key_surface.json').read_text())
mesh = trimesh.Trimesh(surface['positions'],surface['triangles'],process=True)
if mesh.volume < 0:
    mesh.invert()
tree = cKDTree(mesh.triangles_center)
rows = np.array([i for i,b in enumerate(H.dom) if b.startswith('thumb_')])
pad = np.array([H.ids[i] for i in H.data['thumb_pad_ids']])
scale = H.data['live']['phone_world'][2][0]
pad_normal = H.normals[pad].mean(axis=0)
pad_normal /= np.linalg.norm(pad_normal)

def normal(local):
    delta=R.from_quat(H.world(local)['thumb_03_r'][1])*R.from_quat(H.data['world']['thumb_03_r'][1]).inv()
    n=xf[:3,:3]@delta.apply(pad_normal)
    return n/np.linalg.norm(n)

def pose(x):
    local = copy.deepcopy(LIVE)
    local['thumb_01_r'][1] = (R.from_quat(H.ref['thumb_01_r'][1])*R.from_rotvec(np.deg2rad(x[:3]))).as_quat().tolist()
    for j in (2,3):
        b = f'thumb_0{j}_r'
        local[b][1] = (R.from_quat(H.ref[b][1])*R.from_rotvec(H.flex_axis(b)*np.deg2rad(x[j+1]))).as_quat().tolist()
    return local

def points(local):
    return H.skin(local) @ xf[:3,:3].T + xf[:3,3]

def distance(p,exact=False):
    if exact:
        q,d,ids = trimesh.proximity.closest_point(mesh,p)
    else:
        _,ids = tree.query(p,k=24)
        q = trimesh.triangles.closest_point(mesh.triangles[ids].reshape(-1,3,3),np.repeat(p,24,axis=0)).reshape(-1,24,3)
        d = np.linalg.norm(q-p[:,None,:],axis=2); j=d.argmin(axis=1); i=np.arange(len(p))
        q,d,ids = q[i,j],d[i,j],ids[i,j]
    # shortcut: nearest-face signs are provisional until the UE winding query checks this pose.
    return d*np.where(np.einsum('ij,ij->i',p-q,mesh.face_normals[ids]) >= 0,1,-1)*scale

def residual(x):
    local=pose(x); p = points(local); d=distance(p[rows]); pd=distance(p[pad])
    return np.r_[400*np.maximum(.16-d,0),
        12*(p[pad].mean(0)-[-4.7,1.2,-1.45])*scale,6*(normal(local)-[0,-1,0]),
        25*(pd.min()-.18),5*max(0,np.linalg.norm(x[:3])-85),.008*(x[3:]-[30,25])]

if __name__ == '__main__':
    old = R.from_quat(H.ref['thumb_01_r'][1]).inv()*R.from_quat(LIVE['thumb_01_r'][1])
    best = None
    starts=[np.array([-1.93267298,-12.98762929,-10.5203391,40.98629141,34.71624939])]
    for x in starts:
        def seat(x):
            local=pose(x)
            return np.r_[points(local)[pad].mean(0)-[-4.7,2.5,-1.45],3*(normal(local)-[0,-1,0])]
        x=least_squares(seat,x,bounds=([-85]*3+[15,15],[85]*3+[70,70]),max_nfev=150).x
        print('normal seed',x,flush=True)
        fit=least_squares(residual,np.clip(x,[-84]*3+[15,15],[84]*3+[69,69]),bounds=([-85]*3+[15,15],[85]*3+[70,70]),max_nfev=150,ftol=1e-7,diff_step=1e-3)
        print('fit',fit.cost,fit.x,flush=True)
        if best is None or fit.cost < best.cost:
            best=fit
    local=pose(best.x); p=points(local); d=distance(p[rows],True); pd=distance(p[pad],True)
    report=dict(x=best.x.tolist(),min_thumb_mm=float(d.min()*10),pad_gap_mm=float(pd.min()*10),pad_key_local=p[pad].mean(0).tolist(),base_deg=float(np.linalg.norm(best.x[:3])),curl={str(j):H.curl_motion(local,'thumb',j,'r') for j in (2,3)})
    print(report,flush=True)
    assert all(H.curl_motion(LIVE,'thumb',j,'r') < 0 for j in (2,3)), 'old thumb regression'
    assert all(v>0 for v in report['curl'].values()) and report['base_deg']<=85
    assert 1<=report['min_thumb_mm']<=3 and 1<=report['pad_gap_mm']<=3,report
    (ROOT/'review/key_native_thumb.json').write_text(json.dumps(dict(report=report,local=local),indent=2))
    source=json.loads((ROOT/'key_pinch_solution.json').read_text())
    for j in (1,2,3):
        b=f'thumb_0{j}_r'
        source['pose'][b]=local[b][1]
    source['native_thumb']=report
    (ROOT/'key_native_solution.json').write_text(json.dumps(source,indent=2))
