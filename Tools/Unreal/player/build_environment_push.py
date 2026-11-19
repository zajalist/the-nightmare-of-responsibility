"""A single-hand push using the existing reach body motion and an open-palm finger pose."""
import json,hashlib,unreal
from pathlib import Path
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
P='/Game/FoA/Characters/Player';E=unreal.EditorAssetLibrary;A=unreal.AnimPoseExtensions;L=unreal.AnimPoseSpaces.LOCAL
src=unreal.load_asset(P+'/Anims/UAL/UAL_Interact');path=P+'/Anims/AS_FoA_DoorPush'
seq=unreal.load_asset(path) or E.duplicate_asset(src.get_path_name(),path);assert seq
opt=unreal.AnimPoseEvaluationOptions();opt.evaluation_type=unreal.AnimDataEvalType.RAW
ref=A.get_reference_pose(src.get_editor_property('skeleton'));frames=unreal.AnimationLibrary.get_num_frames(src)+1;length=src.get_play_length()
names=[str(n) for n in A.get_bone_names(ref)];selected=[n for n in names if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
times=[0.,length*.25,length*.5,length*.75,length]
def protected(asset):return [[A.get_bone_pose(A.get_anim_pose_at_time(asset,t,opt),n,L).export_text() for n in names if n not in selected] for t in times]
before=protected(src);c=seq.get_editor_property('controller');c.open_bracket('Open only the pushing fingers',False)
for n in selected:
 p=A.get_bone_pose(A.get_anim_pose_at_time(src,0.,opt),n,L);neutral=A.get_bone_pose(ref,n,L)
 rots=[]
 for i in range(frames):
  t=length*i/(frames-1);a=min(max((t-.12)/.28,0.),max((1.65-t)/.3,0.),1.);a=a*a*(3-2*a)
  rots.append(unreal.MathLibrary.quat_slerp(p.rotation,neutral.rotation,a))
 c.set_bone_track_keys(n,[p.translation]*frames,rots,[p.scale3d]*frames,False)
c.close_bracket(False);assert protected(seq)==before;assert E.save_loaded_asset(seq,False)
mp=P+'/Montages/AM_FoA_PushDoor';m=unreal.load_asset(mp)
if not m:
 f=unreal.AnimMontageFactory();f.set_editor_property('source_animation',seq)
 m=unreal.AssetToolsHelpers.get_asset_tools().create_asset('AM_FoA_PushDoor',P+'/Montages',unreal.AnimMontage,f)
tracks=m.get_editor_property('slot_anim_tracks');t=tracks[0];t.set_editor_property('slot_name','DefaultSlot');m.set_editor_property('slot_anim_tracks',[t])
for prop in ('blend_in','blend_out'):
 b=m.get_editor_property(prop);b.set_editor_property('blend_time',.3);m.set_editor_property(prop,b)
if 'InteractionContact' not in [str(x) for x in unreal.AnimationLibrary.get_animation_notify_track_names(m)]:
 unreal.AnimationLibrary.add_animation_notify_track(m,'InteractionContact')
 cls=unreal.load_class(None,'/Game/FoA/Gameplay/AN_FoA_InteractionContact.AN_FoA_InteractionContact_C')
 unreal.AnimationLibrary.add_animation_notify_event(m,'InteractionContact',.9,cls)
assert E.save_loaded_asset(m,False)
dt=unreal.load_asset('/Game/FoA/Gameplay/DT_Interactions');raw=unreal.DataTableFunctionLibrary.export_data_table_to_json_string(dt);rows=json.loads(raw);changed=[]
for row in rows:
 def value(key):return next((v for k,v in row.items() if k==key or k.startswith(key+'_')),None)
 if value('Interactable')=='Door' and value('State')=='HandleOff' and value('Verb')=='Use' and value('Item') in ('None',''):
  key=next(k for k in row if k=='Montage' or k.startswith('Montage_'));row[key]=m.get_path_name();changed.append(row.get('Name'))
assert len(changed)==1,changed
assert unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(dt,json.dumps(rows));assert E.save_loaded_asset(dt,False)
Path('P:/FoA/Saved/Integration/environment_push.json').write_text(json.dumps(dict(sequence=path,montage=mp,rows=changed,protected_body_tracks_exact=True),indent=1))
print('Single-hand push saved; all non-finger reach tracks exact',changed)
