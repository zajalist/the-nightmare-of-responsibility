"""Keep the native wrist straight by letting the shoulder follow each ratchet stroke."""
import copy,json
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R
from export_screw_runtime import H,ROOT,K,BODY,TIP,load
from ue_hand import m

AXIS=BODY.inv().apply([1,0,0])

def solve(index):
    source,base=load(index); initial=H.world(base); obj=source['object_ue']
    tip=np.array(obj['loc'])+R.from_quat(obj['quat']).apply(TIP*np.array(obj['scale']))
    grip=tip-AXIS*16/K
    shoulder,elbow,wrist,middle=[np.array(initial[b][0]) for b in ('upperarm_r','lowerarm_r','hand_r','middle_01_r')]
    upper=np.linalg.norm(elbow-shoulder); lower=np.linalg.norm(wrist-elbow)
    frames=[]; checks=[]; previous=np.zeros(3)
    for angle in np.linspace(0,90,31):
        turn=R.from_rotvec(AXIS*np.deg2rad(-angle))
        target=grip+turn.apply(wrist-grip)
        handq=turn*R.from_quat(initial['hand_r'][1])
        handdir=turn.apply(middle-wrist);handdir/=np.linalg.norm(handdir)
        forearm=handdir+AXIS;forearm/=np.linalg.norm(forearm)
        pole=target-lower*forearm
        def stance(x):
            p=copy.deepcopy(base)
            p['spine_01'][1]=(R.from_quat(base['spine_01'][1])*R.from_rotvec(np.deg2rad(x))).as_quat().tolist()
            return p
        def residual(x):
            s=np.array(H.world(stance(x))['upperarm_r'][0])
            return np.r_[1000*(np.linalg.norm(pole-s)-upper),.05*x]
        fit=least_squares(residual,previous,bounds=(-30,30),max_nfev=100,diff_step=1e-3)
        previous=fit.x;p=stance(fit.x)
        for bone,child,goal in [('upperarm_r','lowerarm_r',pole),('lowerarm_r','hand_r',target)]:
            w=H.world(p);start=np.array(w[bone][0])
            q=R.from_quat(m.from_to(np.array(w[child][0])-start,goal-start))*R.from_quat(w[bone][1])
            p[bone][1]=(R.from_quat(w[H.parents[bone]][1]).inv()*q).as_quat().tolist()
        w=H.world(p);p['hand_r'][1]=(R.from_quat(w['lowerarm_r'][1]).inv()*handq).as_quat().tolist();w=H.world(p)
        p=H.untwist_forearm(p,'r');w=H.world(p)
        actual=np.array(w['hand_r'][0]);f=actual-np.array(w['lowerarm_r'][0]);f/=np.linalg.norm(f)
        deg=lambda a,b:float(np.rad2deg(np.arccos(np.clip(np.dot(a,b),-1,1))))
        check=dict(angle=float(angle),wrist=deg(f,handdir),inline=deg(f,AXIS),hand_error_mm=float(np.linalg.norm(actual-target)*K*10),spine_delta=fit.x.tolist())
        check['wrist_joint_rotation_deg']=float((R.from_quat(H.ref['hand_r'][1]).inv()*R.from_quat(p['hand_r'][1])).magnitude()*180/np.pi)
        axis=R.from_quat(H.ref['hand_r'][1]).inv().apply(H.ref['hand_r'][0]);axis/=np.linalg.norm(axis)
        delta=R.from_quat(H.ref['hand_r'][1]).inv()*R.from_quat(p['hand_r'][1])
        check['wrist_axial_twist_deg']=float(np.dot(delta.as_rotvec(),axis)*180/np.pi)
        assert abs(check['wrist_axial_twist_deg'])<.001,check
        assert check['hand_error_mm']<.01 and check['wrist']<=20 and check['inline']<=20,check
        for b in ('foot_l','foot_r','pelvis'):
            assert np.linalg.norm(np.array(w[b][0])-initial[b][0])<1e-6
        frames.append(p);checks.append(check)
    out=dict(frames=frames,checks=checks,lower_length_cm=float(lower*K),hand_direction_local=R.from_quat(initial['hand_r'][1]).inv().apply((middle-wrist)/np.linalg.norm(middle-wrist)).tolist())
    (ROOT/f'screwdriver_screw{index}_turn.json').write_text(json.dumps(out))
    print(index,'wrist',max(c['wrist'] for c in checks),'inline',max(c['inline'] for c in checks),'spine',max(np.linalg.norm(c['spine_delta']) for c in checks),flush=True)

if __name__=='__main__':
    for i in range(4):solve(i)
