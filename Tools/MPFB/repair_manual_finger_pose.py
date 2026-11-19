"""Back up and repair finger controls only at the user's current rest frame, preserving every other channel."""
import unreal,json,re,shutil,datetime
from pathlib import Path
L=unreal.LevelSequenceEditorBlueprintLibrary;E=unreal.EditorAssetLibrary
s=L.get_current_level_sequence();assert s and s.get_name()=='LS_WakeUp_ManualPose' and not L.is_playing()
frame=L.get_current_time();assert frame==330,('User moved frame; do not overwrite',frame)
r=unreal.ControlRigSequencerLibrary.get_control_rigs(s)[0].control_rig;h=r.get_hierarchy()
pattern=re.compile(r'^(thumb|index|middle|ring|pinky)_(metacarpal|0[123]|curl)_([lr])_ctrl$')
controls=[k for k in h.get_controls() if pattern.fullmatch(str(k.name))];assert len(controls)>=38,len(controls)
curls={'index':(10,20,8),'middle':(15,25,10),'ring':(18,28,12),'pinky':(20,30,15),'thumb':(6,8,5)}
desired={}
for k in controls:
    finger,joint,side=pattern.fullmatch(str(k.name)).groups();deg=curls[finger][int(joint)-1] if joint.startswith('0') else 0
    desired[str(k.name)]={'Location':dict(X=0.,Y=0.,Z=0.),'Rotation':dict(X=0.,Y=0.,Z=-float(deg)),'Scale':dict(X=1.,Y=1.,Z=1.)}
channels=[c for b in s.get_bindings() for t in b.get_tracks() if isinstance(t,unreal.MovieSceneControlRigParameterTrack) for sec in t.get_sections() for c in sec.get_all_channels()]
def state(c):return {'name':str(c.get_name()),'default':str(c.get_default()),'keys':[(k.get_time().frame_number.value,str(k.get_value())) for k in c.get_keys()]}
before=[state(c) for c in channels]
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=Path('P:/FoA/Saved/Backups/manual_fingers')/stamp;backup.mkdir(parents=True)
assert E.save_loaded_asset(s,False)
shutil.copy2('P:/FoA/Content/FoA/Cinematics/LS_WakeUp_ManualPose.uasset',backup/'LS_WakeUp_ManualPose.uasset')
(backup/'channels.json').write_text(json.dumps(before,indent=1))
changed=[]
with unreal.ScopedEditorTransaction('Relax only the sleeping fingers'):
    for c in channels:
        parts=str(c.get_name()).split('.')
        if len(parts)!=3 or parts[0] not in desired:continue
        control,group,axis=parts;axis=axis.split('_')[0]
        value=desired[control][group][axis]
        keys=[k for k in c.get_keys() if k.get_time().frame_number.value==frame]
        if keys:
            for key in keys:key.set_value(value)
        else:c.add_key(unreal.FrameNumber(frame),value,time_unit=unreal.MovieSceneTimeUnit.DISPLAY_RATE)
        changed.append(str(c.get_name()))
    for k in controls:
        angles=desired[str(k.name)]['Rotation'];v=unreal.EulerTransform(rotation=unreal.Rotator(roll=angles['X'],pitch=angles['Y'],yaw=angles['Z']))
        h.set_control_value(k,unreal.RigHierarchy.make_control_value_from_euler_transform(v))
    L.set_current_time(frame)
after=[state(c) for c in channels]
assert all(a==b for a,b in zip(before,after) if a['name'] not in changed),'Non-finger channel changed'
for a,b in zip(before,after):
    if a['name'] in changed:
        assert a['default']==b['default']
        assert [k for k in a['keys'] if k[0]!=frame]==[k for k in b['keys'] if k[0]!=frame],a['name']
assert L.get_current_time()==frame
assert E.save_loaded_asset(s,False)
report={'backup':str(backup),'frame':frame,'controls':len(controls),'changed_channels':len(changed),'untouched_channels':len(channels)-len(changed),'other_frames_preserved':True,'defaults_preserved':True,'body_arms_hands_hips_channels_preserved':True,'controls_changed':list(desired)}
Path('P:/FoA/Saved/Integration/manual_finger_repair.json').write_text(json.dumps(report,indent=1));print('FINGER_REPAIR',json.dumps(report))
