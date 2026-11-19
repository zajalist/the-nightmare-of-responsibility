"""Four-second temple reaction for the existing DefaultSlot; no Blueprint changes.

Run with ue_remote under the two output asset leases, then save both through Hayba asset_save.
"""
import math,sys
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/wakeup')
import wake_common as W
import importlib
importlib.reload(W)
m=W.m
ROOT='/Game/FoA/Characters/Player'
OUT=ROOT+'/Anims/AS_FoA_Headache'
MONTAGE=ROOT+'/Montages/AM_FoA_Headache'
FPS,DURATION=30,4.0

def main():
    src=unreal.load_asset(W.UAL+'UAL_PickUp_Table');assert src
    A=W.UeAdapter({'rest':src});base=A.pose_at('rest',0.0)
    ref=unreal.AnimPoseExtensions.get_reference_pose(src.get_editor_property('skeleton'))
    for b in W.edge_clip.finger_bones(A.names,'r'):
        pos,q=A.lget(base,b)
        rq=unreal.AnimPoseExtensions.get_bone_pose(ref,b,W.LOCAL).rotation
        A.lset(base,b,pos,m.qslerp(q,tuple(rq.to_tuple()),.70))
    start=A.wget(base,'hand_r')[0]

    def frame(t):
        p=base.copy()
        weight=min(m.smooth((t-.15)/.95),1-m.smooth((t-2.75)/1.05))
        if weight<=0:return p
        for b in ('spine_01','spine_02','spine_03'):
            pos,q=A.wget(p,b)
            A.wset(p,b,pos,m.qnorm(m.qmul(m.qaxis((1,0,0),-2*weight),q)))
        for b in ('neck_01','head'):
            pos,q=A.wget(p,b)
            A.wset(p,b,pos,m.qnorm(m.qmul(m.qaxis((1,0,0),-4*weight),q)))
        head=A.wget(p,'head')[0]
        temple=m.add(head,(-15.0,8.0,-5.0))
        target=m.add(m.lerp(start,temple,weight),m.mul((-6,8,2),math.sin(math.pi*weight)))
        sh,sq=A.wget(p,'upperarm_r');el,_=A.wget(p,'lowerarm_r');wr,_=A.wget(p,'hand_r')
        q1,q2,_=m.two_bone(sh,el,wr,target,m.add(sh,(-25,20,-35)))
        A.wset(p,'upperarm_r',sh,m.qnorm(m.qmul(q1,sq)))
        el,eq=A.wget(p,'lowerarm_r');A.wset(p,'lowerarm_r',el,m.qnorm(m.qmul(q2,eq)))
        hp,hq=A.wget(p,'hand_r')
        forward=m.norm(m.sub(hp,A.wget(p,'lowerarm_r')[0]))
        f=m.sub(A.wget(p,'middle_01_r')[0],hp)
        thumb=m.sub(A.wget(p,'index_01_r')[0],A.wget(p,'pinky_01_r')[0])
        want=m.qnorm(m.qmul(m.align(f,thumb,forward,(0,-1,0)),hq))
        A.wset(p,'hand_r',hp,m.qslerp(hq,want,m.smooth(weight/.6)))
        assert m.length(m.sub(hp,target))<.5,('Unreachable temple',t,hp,target)
        if weight>.99:
            finger=m.norm(m.sub(A.wget(p,'middle_01_r')[0],hp))
            assert m.dot(finger,forward)>.995,('Bent temple wrist',t)
        return p

    n=int(FPS*DURATION);frames=[frame(i/FPS) for i in range(n+1)]
    for b in ('foot_l','foot_r','pelvis'):
        assert max(m.length(m.sub(A.wget(p,b)[0],A.wget(base,b)[0])) for p in frames)<.01
    assert frames[0].local==frames[-1].local,'Reaction must return to its starting pose'
    EAL=unreal.EditorAssetLibrary
    seq=unreal.load_asset(OUT) or EAL.duplicate_asset(src.get_path_name(),OUT)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    unreal.AnimationLibrary.remove_all_animation_notify_tracks(seq)
    ctrl=seq.get_editor_property('controller');ctrl.open_bracket('Headache temple reaction',False)
    ctrl.set_frame_rate(unreal.FrameRate(FPS,1),False);ctrl.set_number_of_frames(unreal.FrameNumber(n),False)
    for b in A.names:
        keys=[p.local[b] for p in frames]
        ctrl.set_bone_track_keys(b,[unreal.Vector(*x[0]) for x in keys],[unreal.Quat(*x[1]) for x in keys],
                                [unreal.Vector(*x[2]) for x in keys],False)
    ctrl.close_bracket(False);seq.set_editor_property('enable_root_motion',False)
    montage=unreal.load_asset(MONTAGE)
    if not montage:
        factory=unreal.AnimMontageFactory();factory.set_editor_property('source_animation',seq)
        montage=unreal.AssetToolsHelpers.get_asset_tools().create_asset('AM_FoA_Headache',ROOT+'/Montages',unreal.AnimMontage,factory)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(montage)
    tracks=montage.get_editor_property('slot_anim_tracks');track=tracks[0]
    track.set_editor_property('slot_name','DefaultSlot')
    segment=unreal.AnimSegment();segment.set_editor_property('anim_reference',seq)
    segment.set_editor_property('anim_start_time',0.0);segment.set_editor_property('anim_end_time',DURATION)
    segment.set_editor_property('anim_play_rate',1.0);segment.set_editor_property('looping_count',1)
    anim=track.get_editor_property('anim_track');anim.set_editor_property('anim_segments',[segment]);track.set_editor_property('anim_track',anim)
    montage.set_editor_property('slot_anim_tracks',[track])
    for prop,secs in (('blend_in',.25),('blend_out',.35)):
        blend=montage.get_editor_property(prop);blend.set_editor_property('blend_time',secs)
        blend.set_editor_property('blend_option',unreal.AlphaBlendOption.SINUSOIDAL);montage.set_editor_property(prop,blend)
    assert abs(seq.get_play_length()-DURATION)<.01
    assert abs(montage.get_play_length()-DURATION)<.01
    print('BAKED',OUT,MONTAGE,'4.0 seconds DefaultSlot; pinned feet, aligned wrist, returns to idle; save through Hayba')

main()
