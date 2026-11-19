"""Read-only post-application check of the user's live sequence and control values."""
import unreal,json,re,datetime
from pathlib import Path
L=unreal.LevelSequenceEditorBlueprintLibrary;s=L.get_current_level_sequence();assert s.get_name()=='LS_WakeUp_ManualPose'
report=json.loads(Path('P:/FoA/Saved/Integration/manual_finger_repair.json').read_text())
backup=json.loads((Path(report['backup'])/'channels.json').read_text())
def stable(name):return re.sub(r'_\d+$','',name)
before={stable(c['name']):dict(c,name=stable(c['name'])) for c in backup}
channels=[c for b in s.get_bindings() for t in b.get_tracks() if isinstance(t,unreal.MovieSceneControlRigParameterTrack) for sec in t.get_sections() for c in sec.get_all_channels()]
changed_controls=set(report['controls_changed']);checked=0;outside=[]
for c in channels:
    name=stable(str(c.get_name()));old=before[name]
    current={'name':name,'default':str(c.get_default()),'keys':[[k.get_time().frame_number.value,str(k.get_value())] for k in c.get_keys()]}
    if name.split('.')[0] not in changed_controls:
        checked+=1
        if old!=current:outside.append(name)
r=unreal.ControlRigSequencerLibrary.get_control_rigs(s)[0].control_rig;h=r.get_hierarchy()
auto={str(k.name):unreal.RigHierarchy.get_int_from_control_value(h.get_control_value(k)) for k in h.get_controls() if 'Auto Interpolate' in str(k.name)}
verify={'sequence':s.get_path_name(),'frame':L.get_current_time(),'non_finger_channels_checked':checked,'non_finger_channels_changed':outside,'auto_interpolate':auto,'transient_capture_actors_remaining':[a.get_path_name() for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label().startswith('TMP_handQA_')]}
assert not outside and not any(auto.values()) and not verify['transient_capture_actors_remaining'],verify
Path('P:/FoA/Saved/Integration/manual_finger_verified.json').write_text(json.dumps(verify,indent=1));print('FINGER_VERIFIED',json.dumps(verify))
