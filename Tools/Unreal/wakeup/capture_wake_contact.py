"""Read-only observer for a coordinator-owned actual wake proof.

Run after PIE starts, alongside the normal film proof. Does not start/stop PIE,
seek animation, change the view, or override any sequence/material state.
Captures actual source and Teen bones at30Hz for contact and framing analysis.
"""
import json,time
from pathlib import Path
import unreal

S={'start':time.time(),'last':-1,'rows':[],'sleep':[],'feet':[],'groom':[],'h':None}
OUT=Path('P:/FoA/Saved/AnimShots/wake_contact_live.json')
BONES=('upperarm_l','lowerarm_l','hand_l','middle_01_l','index_01_l','pinky_01_l','middle_03_l','index_03_l','pinky_03_l','head',
       'pelvis','spine_01','spine_03','neck_01','thigh_l','calf_l','foot_l','ball_l','thigh_r','calf_r','foot_r','ball_r',
       'upperarm_r','lowerarm_r','hand_r','middle_01_r','index_01_r','pinky_01_r','middle_03_r','index_03_r','pinky_03_r')


def xf(tr):
    return dict(position=list(tr.translation.to_tuple()),rotation=list(tr.rotation.to_tuple()),scale=list(tr.scale3d.to_tuple()))


def finish(reason):
    if S['h'] is not None:
        unreal.unregister_slate_post_tick_callback(S['h']);S['h']=None
    OUT.write_text(json.dumps(dict(reason=reason,rows=S['rows'],sleep=S['sleep'],feet=S['feet'],groom=S['groom'],bed=S.get('bed')),indent=1))
    unreal.log('[wake-contact] '+reason+' samples='+str(len(S['rows'])))


def tick(dt):
    try:
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not world:return finish('pie_ended')
        if time.time()-S['start']>48:return finish('timeout')
        d=unreal.GameplayStatics.get_actor_of_class(world,unreal.load_class(None,'/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
        if not d:return
        sequence=d.get_editor_property('SeqPlayer')
        if not sequence:return
        q=sequence.get_current_time();t=(q.time.frame_number.value+q.time.sub_frame)*q.rate.denominator/q.rate.numerator
        if 0<=t<=28.4 and int(t*10)!=S.get('feet_last'):
            S['feet_last']=int(t*10)
            pawn=unreal.GameplayStatics.get_player_character(world,0)
            if 'bed' not in S:
                bed=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor) if a.get_actor_label()=='Bed')
                boxes=[unreal.SystemLibrary.get_component_bounds(c) for c in bed.get_components_by_class(unreal.StaticMeshComponent)]
                o,e,_=max(boxes,key=lambda box:box[2]);S['bed']=dict(origin=o.to_tuple(),extent=e.to_tuple())
            S['feet'].append(dict(sequence_seconds=t,components={name:{bone:xf(pawn.get_editor_property(name).get_socket_transform(bone,unreal.RelativeTransformSpace.RTS_WORLD))
                for bone in ('thigh_l','calf_l','foot_l','ball_l','thigh_r','calf_r','foot_r','ball_r')} for name in ('Mesh','Body')}))
            hair=pawn.get_editor_property('Hair');face=pawn.get_editor_property('Face')
            groom=hair.get_editor_property('groom_asset');binding=hair.get_editor_property('binding_asset')
            origin,extent,_=unreal.SystemLibrary.get_component_bounds(hair)
            S['groom'].append(dict(sequence_seconds=t,parent=hair.get_attach_parent().get_name(),
                relative=xf(hair.get_relative_transform()),visible=hair.is_visible(),
                groom=groom.get_path_name() if groom else None,binding=binding.get_path_name() if binding else None,
                face_tick_option=str(face.get_editor_property('visibility_based_anim_tick_option')),
                face_head=xf(face.get_socket_transform('head',unreal.RelativeTransformSpace.RTS_WORLD)),
                body_head=xf(pawn.get_editor_property('Body').get_socket_transform('head',unreal.RelativeTransformSpace.RTS_WORLD)),
                bounds_origin=list(origin.to_tuple()),bounds_extent=list(extent.to_tuple())))
        if 9.2<=t<19.7 and int(t*2)!=S.get('sleep_last'):
            S['sleep_last']=int(t*2)
            pawn=unreal.GameplayStatics.get_player_character(world,0)
            face=pawn.get_editor_property('Face');body=pawn.get_editor_property('Body')
            if t>=12 and not S.get('full_sleep'):
                S['full_sleep']=True
                bones=[dict(name=str(body.get_bone_name(i)),**xf(body.get_socket_transform(body.get_bone_name(i),unreal.RelativeTransformSpace.RTS_COMPONENT)))
                       for i in range(body.get_num_bones())]
                OUT.with_name('wake_sleep_body_pose.json').write_text(json.dumps(dict(mesh=body.get_skeletal_mesh_asset().get_path_name(),
                    space='component',world=xf(body.get_world_transform()),bones=bones),indent=1))
            o,e,_=unreal.SystemLibrary.get_component_bounds(body)
            S['sleep'].append(dict(sequence_seconds=t,wall_time=time.time(),sleep_eye_closure=pawn.get_editor_property('SleepEyeClosure'),
                blink_left=face.get_morph_target('eyeBlinkLeft'),blink_right=face.get_morph_target('eyeBlinkRight'),
                head=xf(face.get_socket_transform('head',unreal.RelativeTransformSpace.RTS_WORLD)),
                body_bounds_origin=list(o.to_tuple()),body_bounds_extent=list(e.to_tuple()),
                components={name:{bone:xf(pawn.get_editor_property(name).get_socket_transform(bone,unreal.RelativeTransformSpace.RTS_WORLD))
                                  for bone in BONES} for name in ('Mesh','Body')}))
        if t>28.4 and S['rows']:return finish('captured_actual_sequence')
        frame=int(t*30)
        if not 23.7<=t<=28.4 or frame==S['last']:return
        S['last']=frame
        pawn=unreal.GameplayStatics.get_player_character(world,0)
        pc=unreal.GameplayStatics.get_player_controller(world,0)
        row=dict(sequence_seconds=t,wall_time=time.time(),actor=xf(pawn.get_actor_transform()),components={})
        row['wrinkles']={name:list(pawn.get_editor_property(name).to_tuple()) for name in
                         ('WrinkleWeightsL','WrinkleWeightsR','WrinklePhasesL','WrinklePhasesR')}
        shirt=pawn.get_editor_property('StartOutfit')
        material=shirt.get_material(0)
        if isinstance(material,unreal.MaterialInstanceDynamic):
            row['wrinkles']['shirt_weights_l']=list(material.get_vector_parameter_value('WrinkleWeightsL').to_tuple())
        for name in ('Mesh','Body'):
            comp=pawn.get_editor_property(name)
            row['components'][name]={bone:xf(comp.get_socket_transform(bone,unreal.RelativeTransformSpace.RTS_WORLD)) for bone in BONES}
        row['camera']=dict(position=list(pc.player_camera_manager.get_camera_location().to_tuple()),
                           rotation=list(pc.player_camera_manager.get_camera_rotation().to_tuple()),
                           quaternion=list(pc.player_camera_manager.get_camera_rotation().quaternion().to_tuple()))
        target=pc.get_view_target()
        camera=target.get_component_by_class(unreal.CineCameraComponent) if target else None
        if camera:
            row['camera'].update(focal_mm=camera.get_editor_property('current_focal_length'),
                                 aperture=camera.get_editor_property('current_aperture'),
                                 sensor_width=camera.get_editor_property('filmback').sensor_width,
                                 sensor_height=camera.get_editor_property('filmback').sensor_height,
                                 focus_cm=camera.get_editor_property('focus_settings').get_editor_property('manual_focus_distance'))
        S['rows'].append(row)
    except Exception as exc:
        finish('error:'+repr(exc))


S['h']=unreal.register_slate_post_tick_callback(tick)
