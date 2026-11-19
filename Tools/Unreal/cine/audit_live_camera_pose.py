"""Read-only one-shot snapshot during a COORDINATOR-OWNED proof, never user PIE.
No starts/stops, setters, timers, frame seeking, camera manipulation or screenshot requests.
FOA_OWNED_PROOF=1 and FOA_AUDIT_LABEL identify the externally owned sample.
"""
import datetime,json,os
from pathlib import Path
import unreal
assert os.environ.get('FOA_OWNED_PROOF')=='1','Run only within an explicitly coordinator-owned proof'
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
pc=unreal.GameplayStatics.get_player_controller(w,0);p=unreal.GameplayStatics.get_player_character(w,0);assert pc and p
def path(obj):return obj.get_path_name() if obj else None
def vec(v):return list(v.to_tuple())
def xf(t):return dict(position=vec(t.translation),rotation=vec(t.rotation),scale=vec(t.scale3d))
def serial(v):
    if isinstance(v,unreal.Object):return path(v)
    if hasattr(v,'export_text'):return v.export_text()
    if isinstance(v,(list,tuple,unreal.Array)):return [serial(x) for x in v]
    return v
def props(obj,names):
    result={}
    for name in names:
        try:
            v=obj.get_editor_property(name)
            result[name]=serial(v)
        except Exception as exc:result[name]={'unavailable':str(exc)}
    return result
view=pc.get_view_target();manager=pc.player_camera_manager
report=dict(label=os.environ.get('FOA_AUDIT_LABEL','sample'),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    game_time=unreal.GameplayStatics.get_time_seconds(w),pawn=path(p),pawn_transform=xf(p.get_actor_transform()),
    view_target=path(view),camera=dict(location=vec(manager.get_camera_location()),rotation=str(manager.get_camera_rotation()),fov=manager.get_fov_angle()),
    control_rotation=str(pc.get_control_rotation()),move_ignored=pc.is_move_input_ignored(),look_ignored=pc.is_look_input_ignored(),
    pawn_state=props(p,['bCinematic','bInteractionLocked','bBattleActive','bCameraClose','SleepEyeClosure','bUseControllerRotationYaw']),
    montage=path(p.get_current_montage()),components={})
for name in ('Mesh','Body','Face','StartOutfit','Hair','FollowCamera','HeldTool','HeldToolGrip'):
    c=p.get_editor_property(name)
    row=dict(path=path(c),world=xf(c.get_world_transform()),relative=xf(c.get_relative_transform()),parent=path(c.get_attach_parent()),
        visible=c.is_visible(),properties=props(c,['hidden_in_game','owner_no_see','render_custom_depth','custom_depth_stencil_value','use_attach_parent_bound']))
    if isinstance(c,unreal.SkeletalMeshComponent):
        row.update(mesh=path(c.get_skinned_asset()),anim_class=path(c.get_editor_property('anim_class')),anim_instance=path(c.get_anim_instance()),
            materials=[path(c.get_material(i)) for i in range(c.get_num_materials())],
            active_montage=path(c.get_anim_instance().get_current_active_montage()) if c.get_anim_instance() else None,
            bones={str(c.get_bone_name(i)):xf(c.get_socket_transform(c.get_bone_name(i),unreal.RelativeTransformSpace.RTS_WORLD)) for i in range(c.get_num_bones())})
    if name=='Hair':
        row['groom_properties']=props(c,['groom_asset','binding_asset','attachment_name','hair_groups_desc','cast_shadow'])
        groom=c.get_editor_property('groom_asset')
        row['materials']=[path(c.get_material(i)) for i in range(c.get_num_materials())]
        row['asset_settings']=props(groom,['hair_groups_rendering','hair_groups_lod']) if groom else {}
    if name=='FollowCamera':row['fov']=c.field_of_view
    report['components'][name]=row
find=lambda cls:unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,cls))
director=find('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
if director:
    report['director']=props(director,['bWakeDone','WakeBed','SeqPlayer'])
    player=director.get_editor_property('SeqPlayer')
    if player:report['sequence_seconds']=player.get_current_time().time.frame_number.value/(player.get_frame_rate().numerator/player.get_frame_rate().denominator)
door=find('/Game/FoA/Gameplay/BP_Door.BP_Door_C')
if door:
    report['door']=props(door,['ToolMode','bToolActive','bToolReady','ToolStepIndex','ToolAngle','bToolReleasing','bToolOwnsLocks'])
    report['door']['components']={c.get_name():xf(c.get_world_transform()) for c in door.get_components_by_class(unreal.SceneComponent) if c.get_name() in ('ToolCamera','ToolContact','ToolPivot','ToolTaskLight')}
enc=find('/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C')
if enc:
    report['battle']=props(enc,['BattleState','bActive','PendingMove','TargetIndex','BattleActingMontage','BattleActingAnim'])
    report['battle']['components']={c.get_name():xf(c.get_world_transform()) for c in enc.get_components_by_class(unreal.SceneComponent)}
    report['battle']['garments']=[]
    for garment in enc.get_editor_property('Garments'):
        if not garment:continue
        row={'actor':path(garment),'world':xf(garment.get_actor_transform()),'state':props(garment,['State','Data']), 'components':{}}
        for c in garment.get_components_by_class(unreal.SceneComponent):
            row['components'][c.get_name()]={'world':xf(c.get_world_transform()),'relative':xf(c.get_relative_transform()),'parent':path(c.get_attach_parent())}
            if isinstance(c,unreal.PrimitiveComponent):
                row['components'][c.get_name()]['collision']=str(c.get_collision_enabled())
            if isinstance(c,unreal.SkeletalMeshComponent):
                row['components'][c.get_name()]['mesh']=path(c.get_skinned_asset())
                row['components'][c.get_name()]['bones']={str(c.get_bone_name(i)):xf(c.get_socket_transform(c.get_bone_name(i),unreal.RelativeTransformSpace.RTS_WORLD)) for i in range(c.get_num_bones())}
                row['components'][c.get_name()]['reference']={str(c.get_bone_name(i)):{'parent':str(c.get_parent_bone(c.get_bone_name(i))),**xf(c.get_ref_pose_transform(i))} for i in range(c.get_num_bones())}
        report['battle']['garments'].append(row)
report['furniture_bounds']=[]
for actor in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
    label=actor.get_actor_label()
    if not isinstance(actor,unreal.StaticMeshActor) and not any(term in label.lower() for term in ('bed','chair','desk','wardrobe','commode','nightstand')):continue
    center,extent=actor.get_actor_bounds(True)
    if max(extent.x,extent.y,extent.z)>1:
        report['furniture_bounds'].append(dict(actor=path(actor),label=label,center=vec(center),extent=vec(extent)))
mpc=unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream')
if mpc:
    report['face_effect']={}
    for name in ('FaceOrigin','FaceForward','FaceRight'):
        report['face_effect'][name]=str(unreal.MaterialLibrary.get_vector_parameter_value(w,mpc,name))
    report['face_effect']['FaceSlip']=unreal.MaterialLibrary.get_scalar_parameter_value(w,mpc,'FaceSlip')
out=Path('P:/FoA/Saved/Integration/cinematic_audit')
out.mkdir(exist_ok=True);file=out/('live_'+report['label']+'.json')
file.write_text(json.dumps(report,indent=2,default=str));print('READ_ONLY_CAMERA_POSE',file)
