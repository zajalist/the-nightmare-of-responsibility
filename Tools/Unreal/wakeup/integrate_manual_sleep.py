"""Apply the user's current resting pose to the game's existing sleep clip only."""
import unreal,json,datetime,shutil
from pathlib import Path
L=unreal.LevelSequenceEditorBlueprintLibrary;E=unreal.EditorAssetLibrary;AP=unreal.AnimPoseExtensions
manual=L.get_current_level_sequence()
assert manual and manual.get_name()=='LS_WakeUp_ManualPose' and not L.is_playing()
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert L.get_current_time()==330,'Integrate only the approved rest frame'
binding=next(b for b in manual.get_bindings() if str(b.get_display_name())=='Player')
p=next(a for a in L.get_bound_objects(manual.get_binding_id(binding)) if isinstance(a,unreal.Actor))
rig=unreal.ControlRigSequencerLibrary.get_control_rigs(manual)[0].control_rig;h=rig.get_hierarchy()
pose={str(k.name):h.get_local_transform(k) for k in h.get_bones()}
assert len(pose)>100,'Expected evaluated Manny Control Rig bones'
channels=[c for b in manual.get_bindings() for t in b.get_tracks() for sec in t.get_sections() for c in sec.get_all_channels()]
def keys():return [(str(c.get_default()),[(k.get_time().frame_number.value,str(k.get_value())) for k in c.get_keys()]) for c in channels]
before=keys();assert E.save_loaded_asset(manual,False)
game=unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
source=next(b for b in game.get_bindings() if str(b.get_display_name())=='Animation source Mesh')
sections=[sec for t in source.get_tracks() if isinstance(t,unreal.MovieSceneSkeletalAnimationTrack) for sec in t.get_sections()]
sleep=next(sec for sec in sections if sec.get_start_frame()==0)
clip=sleep.get_editor_property('params').animation
assert clip.get_name()=='AS_FoA_Wake_Lying' and sleep.get_end_frame()==591
later=[(sec.get_start_frame(),sec.get_end_frame(),sec.get_editor_property('params').animation.get_path_name()) for sec in sections if sec!=sleep]
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=Path('P:/FoA/Saved/Backups/manual_sleep_integration')/stamp;backup.mkdir(parents=True)
for name,asset in [('manual',manual),('game',game),('sleep',clip)]:
 assert E.save_loaded_asset(asset,False)
 path=Path('P:/FoA/Content')/(asset.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
 shutil.copy2(path,backup/(name+'.uasset'))
ref=AP.get_reference_pose(clip.get_editor_property('skeleton'));names=[str(n) for n in AP.get_bone_names(ref)]
missing=set(names)-set(pose)
Path('P:/FoA/Saved/Integration/manual_sleep_missing_bones.json').write_text(json.dumps(sorted(missing)))
assert missing<={'center_of_mass','interaction','weapon_l','weapon_r','ik_foot_l','ik_foot_r','ik_foot_root','ik_hand_gun','ik_hand_l','ik_hand_r','ik_hand_root'},sorted(missing)
# The layered rig leaves helper bones on its original T-pose source.
opts=unreal.AnimPoseEvaluationOptions();opts.evaluation_type=unreal.AnimDataEvalType.RAW
base=AP.get_anim_pose_at_time(unreal.load_asset('/Game/FoA/Cinematics/ManualPose/Manual_A_TPose'),0,opts)
for n in missing:pose[n]=AP.get_bone_pose(base,n,unreal.AnimPoseSpaces.LOCAL)
c=clip.get_editor_property('controller');c.open_bracket('Integrate approved manual sleep pose',False)
try:
 c.set_frame_rate(unreal.FrameRate(30,1),False);c.set_number_of_frames(unreal.FrameNumber(270),False)
 for n in names:
  t=pose[n];c.set_bone_track_keys(n,[t.translation]*271,[t.rotation]*271,[t.scale3d]*271,False)
finally:c.close_bracket(False)
clip.set_editor_property('enable_root_motion',False)
opts=unreal.AnimPoseEvaluationOptions();opts.evaluation_type=unreal.AnimDataEvalType.RAW
baked=AP.get_anim_pose_at_time(clip,0,opts)
maximum=max((AP.get_bone_pose(baked,n,unreal.AnimPoseSpaces.LOCAL).translation-pose[n].translation).length() for n in names)
assert maximum<.001,maximum
assert before==keys() and L.get_current_time()==330 and not L.is_playing()
assert later==[(sec.get_start_frame(),sec.get_end_frame(),sec.get_editor_property('params').animation.get_path_name()) for sec in sections if sec!=sleep]
assert E.save_loaded_asset(clip,False)
body=p.get_editor_property('Body')
report={'clip':clip.get_path_name(),'referenced_by':game.get_path_name(),'backup':str(backup),'source_frame':330,'bone_count':len(names),'maximum_local_position_error_cm':maximum,'later_sections_preserved':later,'manual_channels_preserved':len(channels),'expected_world':{n:list(body.get_socket_location(n).to_tuple()) for n in ('head','pelvis','hand_l','hand_r','foot_l','foot_r')},'pawn_transform':str(p.get_actor_transform())}
Path('P:/FoA/Saved/Integration/manual_sleep_integrated.json').write_text(json.dumps(report,indent=2));print('MANUAL_SLEEP_INTEGRATED',json.dumps(report))
