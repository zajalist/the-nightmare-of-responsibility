"""Author the phone on the measured UE mesh with anatomical local hinges; no Blender conversion."""
import copy
import json
from pathlib import Path
import sys
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R
from scipy.spatial import cKDTree
import trimesh
from ue_hand import Hand, m

ROOT = Path('P:/FoA')
H = Hand(ROOT / 'Saved/AnimShots/review/ue_hand_l_fixture.json')
print('UE calibration', H.check_native_capture(), flush=True)
OLD = json.loads((ROOT / 'Saved/AnimShots/phone_grip_solution.json').read_text())
K = 170/180
DIG = ('index','middle','ring','pinky')
A = m.PoseAdapter()
A.parent = H.parents
refw = H.world(H.ref)
oldw = H.world(OLD['hold'])
PQ = R.from_quat(m.qmul(oldw['hand_l'][1],OLD['out']['attach']['rotation']))
P = np.array(OLD['out']['phone_centre'])
eye = np.array(OLD['out']['eye'])
F, RIGHT, UP = np.array((0,1,0)), np.array((-1,0,0)), np.array((0,0,1))
hp = np.array(refw['hand_l'][0])
fd = np.array(refw['middle_01_l'][0])-hp
fd /= np.linalg.norm(fd)
align = R.align_vectors([[0,-1,0],[0,0,-1]],[fd,H.palm_normal])[0]
palm_c = H.points[H.palm].mean(axis=0)
seat = np.array((-2.,3.5,1.3))
start_hand = seat-align.apply((palm_c-hp)*K)
hand_rows = np.array([i for i,b in enumerate(H.dom) if b.startswith('hand_') or b.split('_')[0] in DIG+('thumb',)])
digit_rows = {d:np.array([i for i,b in enumerate(H.dom) if b.startswith(d+'_')]) for d in DIG+('thumb',)}
FLEX = {b:H.flex_axis(b) for b in H.ref if b.startswith(DIG+('thumb',)) and b.endswith('_l')}
thumb_front = np.array([i for i,b in enumerate(H.dom) if b in ('thumb_02_l','thumb_03_l')])
thumb_pad = np.array([i for i,b in enumerate(H.dom) if b == 'thumb_03_l'])
surface = json.loads((ROOT/'Saved/AnimShots/review/phone_surface.json').read_text())
SURFACE = trimesh.Trimesh(surface['positions'],surface['triangles'],process=True)
if SURFACE.volume < 0:
    SURFACE.invert()
SURFACE_TREE = cKDTree(SURFACE.triangles_center)


def pose(x):
    local = copy.deepcopy(H.ref)
    for n,d in enumerate(DIG):
        for j in (1,2,3):
            b = f'{d}_0{j}_l'
            delta = R.from_rotvec(np.deg2rad(x[6+3*n+j-1])*FLEX[b])
            if j == 1:
                delta = R.from_rotvec(np.deg2rad([0,0,x[23+n]]))*delta
            local[b][1] = (R.from_quat(local[b][1])*delta).as_quat().tolist()
    local['thumb_01_l'][1] = (R.from_quat(local['thumb_01_l'][1])*R.from_rotvec(np.deg2rad(x[18:21]))).as_quat().tolist()
    for j,k in ((2,21),(3,22)):
        b = f'thumb_0{j}_l'
        local[b][1] = (R.from_quat(local[b][1])*R.from_rotvec(np.deg2rad(x[k])*FLEX[b])).as_quat().tolist()
    p = m.Pose(local,H.parents)
    target = P+PQ.apply(x[:3]/K)
    rot = PQ*R.from_rotvec(np.deg2rad(x[3:6]))*align*R.from_quat(refw['hand_l'][1])
    sh,el,wr = [refw[b][0] for b in ('upperarm_l','lowerarm_l','hand_l')]
    direction = rot.apply(R.from_quat(refw['hand_l'][1]).inv().apply(fd))
    elbow_pole = target-direction*m.length(m.sub(wr,el))
    q1,q2,reached = m.two_bone(sh,el,wr,target,elbow_pole)
    A.wset(p,'upperarm_l',sh,m.qmul(q1,refw['upperarm_l'][1]))
    e,eq = A.wget(p,'lowerarm_l')
    A.wset(p,'lowerarm_l',e,m.qmul(q2,eq))
    A.wset(p,'hand_l',A.wget(p,'hand_l')[0],rot.as_quat())
    return H.untwist_forearm(p.local,'l')


def points(local):
    return PQ.inv().apply(H.skin(local)-P)*K


def sdf(p, exact=False):
    if exact:
        nearest,distance,ids = trimesh.proximity.closest_point(SURFACE,p)
    else:
        # Search candidates cheaply; export always checks the complete triangle surface.
        _,ids = SURFACE_TREE.query(p,k=32)
        nearest = trimesh.triangles.closest_point(SURFACE.triangles[ids].reshape(-1,3,3),np.repeat(p,32,axis=0)).reshape(-1,32,3)
        distance = np.linalg.norm(nearest-p[:,None,:],axis=2)
        best = distance.argmin(axis=1); rows = np.arange(len(p))
        nearest,distance,ids = nearest[rows,best],distance[rows,best],ids[rows,best]
    # shortcut: this surface is open; nearest-face signs need the final UE winding-query proof.
    return distance*np.where(np.einsum('ij,ij->i',p-nearest,SURFACE.face_normals[ids]) >= 0,1,-1)


def residual(x):
    local = pose(x)
    ps = points(local)
    sd = sdf(ps)
    normal = (R.from_rotvec(np.deg2rad(x[3:6]))*align).apply(H.palm_normal)
    values = [80*np.maximum(.12-sd[hand_rows],0),
        4*np.maximum(ps[thumb_front,2]+.65,0),
        np.array([80*max(0,normal[2]+np.cos(np.deg2rad(30))),
                  max(0,np.linalg.norm(x[18:21])-85)])]
    for d in DIG:
        tip = ps[H.tips[d]].mean(axis=0)
        values.append(np.array([2*(tip[1]+4.15), 1.2*(tip[2]-.1),3*max(0,abs(tip[0])-6.8),
                               2*max(0,np.min(sd[digit_rows[d]])-.30)]))
    values.append(5*np.maximum(x[8:18:3]-.75*x[7:18:3]-5,0))
    values.append(.05*x[23:27])
    th = ps[H.tips['thumb']].mean(axis=0)
    values.append(np.array([4*(th[2]+1.05), .15*(th[1]-1.1),.1*(th[0]+2),
                           20*(ps[thumb_pad,2].max()+.65),
                           3*max(0,abs(th[1])-2.8),3*max(0,abs(th[0])-6.0)]))
    tw = H.world(local)['thumb_02_l'][0]
    t2 = PQ.inv().apply(np.array(tw)-P)*K
    values.append(np.array([2*(t2[1]-4.8), (t2[2]+1.2)]))
    pc = ps[H.palm].mean(axis=0)
    values.append(np.array([.3*(pc[0]+2),.25*(pc[1]-3.5),.5*(pc[2]-1.2)]))
    values.append(.002*(x[6:18]-np.tile([15,65,40],4)))
    return np.concatenate(values)


def metrics(x):
    local = pose(x)
    world = H.world(local)
    forearm = m.sub(world['hand_l'][0],world['lowerarm_l'][0])
    knuckles = m.sub(world['middle_01_l'][0],world['hand_l'][0])
    wrist = float(np.degrees(np.arccos(np.clip(m.dot(m.norm(forearm),m.norm(knuckles)),-1,1))))
    ps = points(local)
    sd = sdf(ps,exact=True)
    n = (R.from_rotvec(np.deg2rad(x[3:6]))*align).apply(H.palm_normal)
    return dict(surface=surface['mesh'],wrist_deg=wrist,min_skin_mm=float(sd[hand_rows].min()*10),palm_facing_deg=float(np.rad2deg(np.arccos(-n[2]))),
        tips={d:ps[H.tips[d]].mean(axis=0).tolist() for d in DIG+('thumb',)},
        thumb_base_deg=float(np.linalg.norm(x[18:21])), thumb_pad_gap_mm=float((-ps[thumb_pad,2].max()-.5)*10),
        contacts_mm={d:float(sd[ix].min()*10) for d,ix in digit_rows.items()},
        curl_motion={d:H.curl_motion(local,d) for d in DIG+('thumb',)})



def main():
    if '--bezel' in sys.argv:
        return bezel_thumb()
    t1 = seat+align.apply((np.array(refw['thumb_01_l'][0])-palm_c)*K)
    td = align.apply(np.array(refw['thumb_02_l'][0])-refw['thumb_01_l'][0])
    desired = np.array([t1[0]+1,4.6,-.2])-t1
    turn = R.from_quat(m.from_to(td,desired))
    tq = align*R.from_quat(refw['thumb_01_l'][1])
    roll = float(next((a.split('=')[1] for a in sys.argv if a.startswith('roll=')),0))
    turn = R.from_rotvec(desired/np.linalg.norm(desired)*np.deg2rad(roll))*turn
    base = (tq.inv()*turn*tq).as_rotvec()*180/np.pi
    x = np.r_[start_hand,[0,0,0],np.tile([15,65,40],4),base,55,15,[-5,0,0,5]]
    lo = np.r_[start_hand-5,[-28]*3,np.tile([8,12,8],4),[-85]*3,12,12,[-10]*4]
    hi = np.r_[start_hand+5,[28]*3,np.tile([65,105,65],4),[85]*3,55,40,[10]*4]
    out = ROOT / 'Saved/AnimShots/review/phone_native_fit.json'
    if '--resume' in sys.argv and out.exists():
        x = np.clip(json.loads(out.read_text())['x'],lo+1e-5,hi-1e-5)
    print('initial',metrics(x),flush=True)
    fit = least_squares(residual,x,bounds=(lo,hi),max_nfev=150,ftol=1e-5,diff_step=1e-4)
    x = fit.x
    report = metrics(x)
    out.write_text(json.dumps(dict(x=x.tolist(),metrics=report,cost=float(fit.cost),local=pose(x)),indent=2))
    (out.parent / f'phone_native_roll{roll:g}.json').write_text(out.read_text())
    print('NATIVE FIT',report,'cost',fit.cost,flush=True)


def bezel_thumb():
    """Recalibrate only the resting left thumb; keep the existing tap and grip."""
    thumb_names=tuple(f'thumb_0{i}_l' for i in (1,2,3))
    old=OLD['hold'];ix=digit_rows['thumb']
    direction=np.array(refw['thumb_03_l'][0])-refw['thumb_02_l'][0];direction/=np.linalg.norm(direction)
    pad_normal=H.palm_normal-direction*(H.palm_normal@direction);pad_normal/=np.linalg.norm(pad_normal)
    pad=np.array([i for i,b in enumerate(H.dom) if b=='thumb_03_l' and H.normals[i]@pad_normal>.65])
    assert len(pad)>=8,'Native thumb pad patch missing'
    eye_local=PQ.inv().apply(eye-P)*K
    def local(a):
        result=copy.deepcopy(old)
        base=a[:3]*min(1.,85./max(np.linalg.norm(a[:3]),1e-9))
        for bone,delta in ((thumb_names[0],np.deg2rad(base)),
                           (thumb_names[1],np.deg2rad(a[3])*FLEX[thumb_names[1]]),
                           (thumb_names[2],np.deg2rad(a[4])*FLEX[thumb_names[2]])):
            result[bone][1]=(R.from_quat(H.ref[bone][1])*R.from_rotvec(delta)).as_quat().tolist()
        return result
    def projection(ps):
        # Actual glass is13.67x6.60cm on the negative-Z face. Project skin
        # through the measured eye onto that plane rather than using tip bones.
        return eye_local+(ps-eye_local)*((-.53-eye_local[2])/(ps[:,2]-eye_local[2]))[:,None]
    def blend(hold,tap,alpha):
        result=copy.deepcopy(hold)
        for bone in thumb_names:
            a=np.array(hold[bone][1]);b=np.array(tap[bone][1])
            if a@b<0:b=-b
            q=a*(1-alpha)+b*alpha;result[bone][1]=(q/np.linalg.norm(q)).tolist()
        return result
    def residual(a):
        held=local(a);ps=points(held);thumb=ps[ix];sd=sdf(thumb)
        projected=projection(thumb)
        front=np.clip((-.45-thumb[:,2])*8,0,1)
        tip=ps[H.tips['thumb']].mean(0)
        return np.r_[100*np.maximum(.10-sd,0),
            100*np.maximum(3.34-projected[:,1],0)*front,
            2*(tip-np.array([-4.5,3.9,.35])),
            60*max(0,float(sd.min())-.25),
            80*max(0,float(sdf(ps[pad]).min())-.25),
            30*max(0,np.linalg.norm(a[:3])-85),
            .01*(a-start)]
    deltas={b:np.rad2deg((R.from_quat(H.ref[b][1]).inv()*R.from_quat(old[b][1])).as_rotvec()) for b in thumb_names}
    start=np.r_[deltas[thumb_names[0]],*[deltas[b]@FLEX[b] for b in thumb_names[1:]]]
    prior=ROOT/'Saved/AnimShots/review/phone_bezel_fit.json'
    if '--resume' in sys.argv and prior.exists():start=np.array(json.loads(prior.read_text())['parameters'])
    fit=least_squares(residual,start,bounds=([-85,-85,-85,8,8],[85,85,85,69,70]),
                      max_nfev=180,ftol=1e-7,diff_step=1e-4)
    hold=local(fit.x);ps=points(hold);thumb=ps[ix];sd=sdf(ps[hand_rows],exact=True)
    print('Bezel rest solved',fit.cost,fit.x.tolist(),flush=True)
    def tap_residual(angles):
        a=fit.x.copy();a[3:]=angles
        ps=points(local(a));distances=sdf(ps[ix],exact=True);pad_distance=sdf(ps[pad],exact=True).min()
        return np.r_[100*np.maximum(.025-distances,0),30*(pad_distance-.05),.01*(angles-fit.x[3:])]
    pressed=least_squares(tap_residual,fit.x[3:],bounds=(np.maximum(8,fit.x[3:]-6),np.minimum([69,70],fit.x[3:]+6)),max_nfev=60)
    tap_angles=fit.x.copy();tap_angles[3:]=pressed.x;tap=local(tap_angles)
    path=[float(sdf(points(blend(hold,tap,t))[hand_rows],exact=True).min()*10) for t in np.linspace(0,1,17)]
    projected=projection(thumb)
    front=thumb[:,2]<-.53
    overlap=front & (np.abs(projected[:,0])<6.835) & (np.abs(projected[:,1])<3.30)
    report=dict(parameters=fit.x.tolist(),cost=float(fit.cost),
        min_skin_mm=float(sd.min()*10),thumb_tip=ps[H.tips['thumb']].mean(0).tolist(),
        projected_front_min_y=float(projected[front,1].min()) if front.any() else None,
        screen_overlapping_thumb_vertices=int(overlap.sum()),
        thumb_contact_mm=float(sdf(thumb,exact=True).min()*10),
        thumb_pad_contact_mm=float(sdf(ps[pad],exact=True).min()*10),
        tap_contact_mm=float(sdf(points(tap)[ix],exact=True).min()*10),
        interpolated_clearance_mm=path,
        non_thumb_tracks_exact=all(hold[n]==old[n] for n in old if n not in thumb_names),
        attachment_exact=True,tap_non_thumb_tracks_exact=all(tap[n]==OLD['tap'][n] for n in tap if n not in thumb_names))
    sol=copy.deepcopy(OLD);sol.update(hold=hold,tap=tap);sol['out']['bezel_thumb']=report
    folder=ROOT/'Saved/AnimShots/review'
    (folder/'phone_bezel_fit.json').write_text(json.dumps(report,indent=2))
    (ROOT/'Saved/AnimShots/phone_bezel_solution.json').write_text(json.dumps(sol))
    print('BEZEL THUMB',report,flush=True)


if __name__ == "__main__":
    main()
