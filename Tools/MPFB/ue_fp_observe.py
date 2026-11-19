"""Owned-PIE front-end setup and bounded camera/crouch observation; no scene captures."""
import json,time
from pathlib import Path
import unreal
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
pcm=unreal.GameplayStatics.get_player_camera_manager(w,0)
def actor(path):return unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path))
fe=actor('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C');d=actor('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
face=p.get_editor_property('Face');hair=p.get_editor_property('Hair');body=p.get_editor_property('Body');cam=p.get_editor_property('FollowCamera')
out=Path('P:/FoA/Saved/CharacterShots/fp_final');out.mkdir(parents=True,exist_ok=True)
S={'start':time.monotonic(),'phase':0,'rows':[],'h':None,'last':0,'error':None}
def finish(reason):
    unreal.unregister_slate_post_tick_callback(S['h'])
    S['reason']=reason;(out/'report.json').write_text(json.dumps({k:v for k,v in S.items() if k!='h'},indent=1));(out/'done.txt').write_text(reason)
def tick(dt):
    try:
        t=time.monotonic()-S['start']
        if t>31 or (out/'stop.txt').exists():return finish('complete' if t<31 else 'timeout')
        if S['phase']==0 and t>.2:fe.call_method('OnSplashFinished');S['phase']=1
        elif S['phase']==1 and t>.6:fe.call_method('OnTitleConfirmed');S['phase']=2
        elif S['phase']==2 and t>1:fe.call_method('WakeUp');S['phase']=3
        elif S['phase']==3:
            story=fe.get_editor_property('Story')
            if story and story.is_in_viewport():story.call_method('Finish');return
            if not d.get_editor_property('SeqPlayer'):return
            if not d.get_editor_property('bWakeDone'):d.call_method('SkipWakeUp');return
            if pc.get_view_target()!=p:return
            unreal.SystemLibrary.pause_timer(d,'PollStoryMoment');unreal.SystemLibrary.clear_timer(d,'TryStoryMoment')
            pc.set_control_rotation(unreal.Rotator(pitch=0,yaw=-135,roll=0));S['phase']=4;S['settle']=t+1
        elif S['phase']==4 and t>S['settle']:
            (out/'ready.txt').write_text('ready');S['phase']=5
        if S['phase']>=4 and t-S['last']>.015:
            S['last']=t;loc=pcm.get_camera_location();rot=pcm.get_camera_rotation();cr=pc.get_control_rotation()
            across=body.get_socket_location('upperarm_r')-body.get_socket_location('upperarm_l')
            torso=unreal.MathLibrary.make_rot_from_x(unreal.MathLibrary.cross_vector_vector(across,unreal.Vector(0,0,1)))
            delta=unreal.MathLibrary.normalized_delta_rotator(rot,torso)
            eye=unreal.MathLibrary.transform_location(face.get_socket_transform('head',unreal.RelativeTransformSpace.RTS_WORLD),unreal.Vector(0,-3.530588955620998,11.768322164387774))
            S['rows'].append({'t':t,'settled':S['phase']==5,'view':pc.get_view_target().get_name(),'camera':list(loc.to_tuple()),'pitch':rot.pitch,'yaw':rot.yaw,'roll':rot.roll,
                'neck_yaw':delta.yaw,'control_yaw':cr.yaw,'actor_yaw':p.get_actor_rotation().yaw,'torso_yaw':torso.yaw,
                'root_yaw_offset':p.get_editor_property('mesh').get_anim_instance().get_editor_property('RootYawOffset'),
                'input_phase':(out/'input_phase.txt').read_text() if (out/'input_phase.txt').exists() else 'setup','eye_error_cm':(loc-eye).length(),
                'face_visible':face.is_visible(),'hair_visible':hair.is_visible(),'crouched':p.get_editor_property('is_crouched'),
                'capsule_half_height':p.get_editor_property('capsule_component').get_scaled_capsule_half_height(),'position':list(p.get_actor_location().to_tuple()),
                'feet':{n:list(body.get_socket_location(n).to_tuple()) for n in ('foot_l','foot_r','ball_l','ball_r')}})
    except Exception as ex:S['error']=repr(ex);finish('error')
S['h']=unreal.register_slate_post_tick_callback(tick)
