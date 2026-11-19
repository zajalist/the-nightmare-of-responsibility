"""Key pinch on the source rig, with a hand-frame offset derived from the actual Teen reference axes."""
import sys,json
from pathlib import Path
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/wakeup')
import wake_common as W
m=W.m
OUT='/Game/FoA/Characters/Player/Anims/Hands/AS_FoA_Grip_Key_R'
CURL={'index_01_r':30,'index_02_r':65,'index_03_r':20,
      'thumb_01_r':25,'thumb_02_r':15,'thumb_03_r':15,
      'middle_01_r':55,'middle_02_r':70,'middle_03_r':30,
      'ring_01_r':60,'ring_02_r':75,'ring_03_r':35,
      'pinky_01_r':65,'pinky_02_r':75,'pinky_03_r':35}

def main():
    src=unreal.load_asset(W.UAL+'UAL_Idle_Loop');A=W.UeAdapter({'idle':src})
    ref=unreal.AnimPoseExtensions.get_reference_pose(src.get_editor_property('skeleton'))
    base=m.Pose({b:A._xf(unreal.AnimPoseExtensions.get_bone_pose(ref,b,W.LOCAL)) for b in A.names},A.parent)
    pose=base.copy()
    for b,deg in CURL.items():
        pos,q=A.lget(pose,b);A.lset(pose,b,pos,m.qmul(q,m.qaxis((0,0,1),-deg)))
    def tip(f):
        a=A.wget(pose,f+'_02_r')[0];b=A.wget(pose,f+'_03_r')[0]
        return m.add(b,m.mul(m.norm(m.sub(b,a)),1.8 if f=='index' else 2.0))
    gap=m.length(m.sub(tip('index'),tip('thumb')));assert .6<gap<1.5,gap
    hp,hq=A.wget(base,'hand_r');inv=m.qinv(hq)
    old_f=m.qrot(inv,m.sub(A.wget(base,'middle_01_r')[0],hp))
    old_t=m.qrot(inv,m.sub(A.wget(base,'index_01_r')[0],A.wget(base,'pinky_01_r')[0]))
    teen=json.loads(Path('P:/FoA/Saved/AnimShots/teen_hand_frame.json').read_text())['bones']
    nf=teen['middle_01_r']['local'];nt=m.sub(teen['index_01_r']['local'],teen['pinky_01_r']['local'])
    center=m.qrot(inv,m.sub(m.lerp(tip('index'),tip('thumb'),.5),hp))
    offset=m.mul(m.qrot(m.align(old_f,old_t,nf,nt),center),m.length(nf)/m.length(old_f))
    rotation=m.frame_quat(nf,m.cross(nt,nf))
    rotator=unreal.Quat(*rotation).rotator()
    Path('P:/FoA/Saved/AnimShots/teen_key_grip_calibration.json').write_text(json.dumps(dict(location=offset,
        rotation=rotation,rotation_degrees=dict(Pitch=rotator.pitch,Yaw=rotator.yaw,Roll=rotator.roll),
        source_tip_gap_cm=gap,method='Teen hand axes and palm proportions with source pinch fingertips',live_verified=False),indent=2))
    seq=unreal.load_asset(OUT) or unreal.EditorAssetLibrary.duplicate_asset(src.get_path_name(),OUT)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    ctrl=seq.get_editor_property('controller');ctrl.open_bracket('Key pinch',False)
    ctrl.set_frame_rate(unreal.FrameRate(30,1),False);ctrl.set_number_of_frames(unreal.FrameNumber(1),False)
    for b in A.names:
        p,q,s=pose.local[b]
        ctrl.set_bone_track_keys(b,[unreal.Vector(*p)]*2,[unreal.Quat(*q)]*2,[unreal.Vector(*s)]*2,False)
    ctrl.close_bracket(False)
    unreal.AnimationLibrary.remove_all_animation_notify_tracks(seq)
    seq.set_editor_property('enable_root_motion',False)
    print('BAKED',OUT,'pinch gap',gap,'Teen local grip',offset,'native save pending')

main()
