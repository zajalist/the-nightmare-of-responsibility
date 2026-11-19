"""One reusable phone hold on the existing DefaultSlot. Raised arm blends in; hold section loops."""
import json
import sys
from pathlib import Path
import unreal

sys.path.insert(0,'P:/FoA/Tools/Unreal/wakeup')
import wake_common as W
m=W.m
OUT='/Game/FoA/Characters/Player/Anims/AS_FoA_PhoneHold'
MONTAGE='/Game/FoA/Characters/Player/Montages/AM_FoA_PhoneHold'


def main():
    src=unreal.load_asset(W.UAL+'UAL_PickUp_Table')
    A=W.UeAdapter({'rest':src});base=A.pose_at('rest',0.0);pose=base.copy()
    for bone in ('spine_01','spine_02','spine_03'):
        pos,q=A.wget(pose,bone)
        A.wset(pose,bone,pos,m.qnorm(m.qmul(m.qaxis((1,0,0),-3),q)))
    rig=W.player_rig()
    # Teen retarget adds 7.6 cm forward and 1.6 cm sideways at this raised wrist (PIE measurement).
    target=W.world_to_comp((32.4,2.4,53),(0,0,0),0,rig)
    pole=W.world_to_comp((5,35,25),(0,0,0),0,rig)
    sh,sq=A.wget(pose,'upperarm_r');el,_=A.wget(pose,'lowerarm_r');wr,_=A.wget(pose,'hand_r')
    q1,q2,_=m.two_bone(sh,el,wr,target,pole)
    A.wset(pose,'upperarm_r',sh,m.qnorm(m.qmul(q1,sq)))
    el,eq=A.wget(pose,'lowerarm_r');A.wset(pose,'lowerarm_r',el,m.qnorm(m.qmul(q2,eq)))
    hp,hq=A.wget(pose,'hand_r')
    forward=m.sub(A.wget(pose,'middle_01_r')[0],hp)
    thumb=m.sub(A.wget(pose,'index_01_r')[0],A.wget(pose,'pinky_01_r')[0])
    A.wset(pose,'hand_r',hp,m.qnorm(m.qmul(m.align(forward,thumb,(0,0,1),(1,0,0)),hq)))
    ref=unreal.AnimPoseExtensions.get_reference_pose(src.get_editor_property('skeleton'))
    for digit in ('index','middle','ring','pinky'):
        bone=digit+'_metacarpal_r'
        if bone in A.names:
            t=unreal.AnimPoseExtensions.get_bone_pose(ref,bone,W.LOCAL)
            A.lset(pose,bone,tuple(t.translation.to_tuple()),tuple(t.rotation.to_tuple()))
    # Measured case-corner pinch: reused key pose with index opened for the 12 mm case.
    curls={'index':(30,9.9368320973,20),'middle':(40,45,27),'ring':(45,50,30),'pinky':(50,55,33),'thumb':(25,15,15)}
    for digit,angles in curls.items():
        for segment in range(1,4):
            bone=f'{digit}_0{segment}_r'
            pos,_=A.lget(pose,bone)
            q=tuple(unreal.AnimPoseExtensions.get_bone_pose(ref,bone,W.LOCAL).rotation.to_tuple())
            A.lset(pose,bone,pos,m.qnorm(m.qmul(q,m.qaxis((0,0,1),-angles[segment-1]))))
    Path('P:/FoA/Saved/UIShots/phone_hold_debug.json').write_text(json.dumps(dict(shoulder=sh,elbow=el,wrist=wr,target=target,result=A.wget(pose,'hand_r')[0],rig=rig)))
    assert m.length(m.sub(A.wget(pose,'hand_r')[0],target))<.5, 'Phone hand beyond reach'
    for bone in ('foot_l','foot_r','pelvis'):
        assert m.length(m.sub(A.wget(pose,bone)[0],A.wget(base,bone)[0]))<.01
    seq=unreal.load_asset(OUT) or unreal.EditorAssetLibrary.duplicate_asset(src.get_path_name(),OUT)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    unreal.AnimationLibrary.remove_all_animation_notify_tracks(seq)
    ctrl=seq.get_editor_property('controller');ctrl.open_bracket('Phone hold',False)
    ctrl.set_frame_rate(unreal.FrameRate(30,1),False);ctrl.set_number_of_frames(unreal.FrameNumber(30),False)
    for bone in A.names:
        p,q,s=pose.local[bone]
        ctrl.set_bone_track_keys(bone,[unreal.Vector(*p)]*31,[unreal.Quat(*q)]*31,[unreal.Vector(*s)]*31,False)
    ctrl.close_bracket(False);seq.set_editor_property('enable_root_motion',False)
    montage=unreal.load_asset(MONTAGE)
    if not montage:
        factory=unreal.AnimMontageFactory();factory.set_editor_property('source_animation',seq)
        montage=unreal.AssetToolsHelpers.get_asset_tools().create_asset('AM_FoA_PhoneHold',MONTAGE.rsplit('/',1)[0],unreal.AnimMontage,factory)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(montage)
    montage.modify()
    track=montage.get_editor_property('slot_anim_tracks')[0];track.set_editor_property('slot_name','DefaultSlot')
    segment=unreal.AnimSegment();segment.set_editor_property('anim_reference',seq)
    segment.set_editor_property('anim_start_time',0.0);segment.set_editor_property('anim_end_time',1.0)
    segment.set_editor_property('anim_play_rate',1.0);segment.set_editor_property('looping_count',1)
    anim=track.get_editor_property('anim_track');anim.set_editor_property('anim_segments',[segment]);track.set_editor_property('anim_track',anim)
    montage.set_editor_property('slot_anim_tracks',[track])
    for prop,seconds in [('blend_in',.45),('blend_out',.35)]:
        blend=montage.get_editor_property(prop);blend.set_editor_property('blend_time',seconds)
        blend.set_editor_property('blend_option',unreal.AlphaBlendOption.SINUSOIDAL);montage.set_editor_property(prop,blend)
    assert abs(seq.get_play_length()-1)<.01 and abs(montage.get_play_length()-1)<.01
    Path('P:/FoA/Saved/UIShots/phone_hold_calibration.json').write_text(json.dumps(dict(rig=rig,
        target_pawn=[32.4,2.4,53],wrist_error_cm=m.length(m.sub(A.wget(pose,'hand_r')[0],target))),indent=2))
    print('Phone hold baked with pinned feet, reachable wrist and looping hold; native save pending')


main()
