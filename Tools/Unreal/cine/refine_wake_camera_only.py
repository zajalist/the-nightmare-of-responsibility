"""Prepare/apply ONLY Cam_PushIn framing. Default inspect; root clearance required for apply.

Run via ue_remote with FOA_CAMERA_MODE=inspect|apply. No sequence editor/frame changes.
Accepted animation/ControlRig/cut/audio/MPC tracks are hashed before and after.
"""
import datetime,hashlib,json,math,os,shutil
from pathlib import Path
import unreal

ROOT=Path('P:/FoA');OUT=ROOT/'Saved/Integration/cinematic_audit';OUT.mkdir(exist_ok=True)
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
seq=unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp');assert seq
mode=os.environ.get('FOA_CAMERA_MODE','inspect');assert mode in ('inspect','apply')
accepted=json.loads((ROOT/'Saved/Integration/manual_sleep_integrated.json').read_text())
aim=[v+d for v,d in zip(accepted['expected_world']['head'],(0,0,6))]
axis=(-.45,.57,.69);length=math.sqrt(sum(v*v for v in axis));axis=[v/length for v in axis]

def value(v):
    if hasattr(v,'export_text'):return v.export_text()
    if hasattr(v,'get_path_name'):return v.get_path_name()
    return v

def track_data(track):
    data=dict(path=track.get_path_name(),kind=track.get_class().get_name(),sections=[])
    for section in track.get_sections():
        row=dict(path=section.get_path_name(),start=section.get_start_frame() if section.has_start_frame() else None,
                 end=section.get_end_frame() if section.has_end_frame() else None,channels=[])
        if isinstance(section,unreal.MovieSceneSkeletalAnimationSection):row['animation_params']=section.get_editor_property('params').export_text()
        for channel in section.get_all_channels():
            keys=[]
            for key in channel.get_keys():
                t=key.get_time();keys.append([t.frame_number.value,t.sub_frame,value(key.get_value())])
            row['channels'].append([str(channel.channel_name),keys])
        data['sections'].append(row)
    return data

def editable(binding,track):
    name=str(binding.get_display_name());parent=binding.get_parent()
    if name=='Cam_PushIn' and isinstance(track,unreal.MovieScene3DTransformTrack):return True
    return bool(parent and str(parent.get_display_name())=='Cam_PushIn' and isinstance(track,unreal.MovieSceneFloatTrack)
                and str(track.get_property_name()) in ('ManualFocusDistance','CurrentAperture'))

def protected():
    records=[track_data(t) for t in seq.get_tracks()]
    for binding in seq.get_bindings():
        records.append(dict(binding=binding.get_id().export_text(),name=str(binding.get_display_name()),
                            tracks=[track_data(t) for t in binding.get_tracks() if not editable(binding,t)]))
    (OUT/'protected_latest.json').write_text(json.dumps(records,sort_keys=True,default=str,indent=1))
    return hashlib.sha256(json.dumps(records,sort_keys=True,default=str).encode()).hexdigest()

def protected_files():
    names=['Content/FoA/Cinematics/LS_WakeUp_ManualPose.uasset','Content/FoA/Cinematics/WakeUp/AS_FoA_Wake_Lying.uasset','Content/FoA/Cinematics/WakeUp/AS_FoA_Wake_EdgeReach.uasset']
    return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}

binding=next(b for b in seq.get_bindings() if str(b.get_display_name())=='Cam_PushIn')
transform=next(t for t in binding.get_tracks() if isinstance(t,unreal.MovieScene3DTransformTrack))
sections=transform.get_sections();assert len(sections)==1
channels={str(c.channel_name):c for c in sections[0].get_all_channels()}
times=[[k.get_time().frame_number.value for k in channels[n].get_keys()] for n in ('Location.X','Location.Y','Location.Z')]
assert times[0]==times[1]==times[2] and len(times[0])==4,('Unexpected camera authoring; inspect before adapting',times)
distances=[125.,125.,100.,100.]
keys=[]
for frame,distance in zip(times[0],distances):
    eye=[a+v*distance for a,v in zip(aim,axis)];delta=[a-e for a,e in zip(aim,eye)]
    keys.append(dict(frame=frame,eye=eye,pitch=math.degrees(math.atan2(delta[2],math.hypot(*delta[:2]))),yaw=math.degrees(math.atan2(delta[1],delta[0])),focus_cm=distance))
template=binding.get_object_template();camera=unreal.find_object(None,template.get_path_name()+'.CameraComponent')
assert isinstance(camera,unreal.CineCameraComponent)
try:
    before=protected();files=protected_files()
    assert protected()==before,'Protection serialization must be stable before any mutation'
except Exception:
    import traceback
    (OUT/'wake_camera_error.txt').write_text(traceback.format_exc())
    raise
report=dict(mode=mode,aim=aim,keys=keys,focal_mm=50,aperture=3.5,protected_tracks_sha256=before,protected_files=files,
            camera_before=track_data(transform),scope='Cam_PushIn transform/focus/aperture only; no POV/handback/cut changes')
if mode=='apply':
    shutil.copy2(OUT/'protected_latest.json',OUT/'protected_before_apply.json')
    backup=ROOT/'Saved/Backups/wake_camera_only'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
    shutil.copy2(ROOT/'Content/FoA/Cinematics/LS_WakeUp.uasset',backup/'LS_WakeUp.uasset')
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    for i,row in enumerate(keys):
        vals=dict(zip(('Location.X','Location.Y','Location.Z'),row['eye']))
        vals.update({'Rotation.X':0.,'Rotation.Y':row['pitch'],'Rotation.Z':row['yaw']})
        for name,v in vals.items():channels[name].get_keys()[i].set_value(v)
    camera.set_editor_property('current_aperture',3.5)
    for child in seq.get_bindings():
        parent=child.get_parent()
        if not parent or str(parent.get_display_name())!='Cam_PushIn':continue
        for track in child.get_tracks():
            if not editable(child,track):continue
            for section in track.get_sections():
                for channel in section.get_all_channels():
                    if str(track.get_property_name())=='CurrentAperture':
                        channel.set_default(3.5)
                        for key in channel.get_keys():key.set_value(3.5)
                    else:
                        focuskeys=channel.get_keys();assert [k.get_time().frame_number.value for k in focuskeys]==times[0]
                        for key,distance in zip(focuskeys,distances):key.set_value(distance)
    assert protected()==before,'Unrelated sequence track changed'
    assert protected_files()==files,'Accepted pose asset changed'
    assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False)
    report.update(backup=str(backup),protected_after=protected(),camera_after=track_data(transform),saved=True)
(OUT/('wake_camera_'+mode+'.json')).write_text(json.dumps(report,indent=2,default=str))
print('WAKE_CAMERA_ONLY',mode,before)
