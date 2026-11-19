"""Reframe only the existing clock insert; retain all cuts, timing, player and sound tracks."""
import json,math
from pathlib import Path
import unreal
seq=unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
binding=next(b for b in seq.get_bindings() if str(b.get_display_name())=='Cam_Insert')
p=json.loads(Path('P:/FoA/Saved/WakeUp/placement.json').read_text());x,y,_=p['edge']['clock']
# Clock origin z79.724, visible base76.12/top102.08. The aim is its
# visual centre shifted5cm toward the seated arm, not the lid target.
eye=(x-123,y+83.5,189.97432);aim=(x-5,y-5,94)
d=tuple(b-a for a,b in zip(eye,aim));distance=math.sqrt(sum(v*v for v in d))
values=dict(zip(('Location.X','Location.Y','Location.Z'),eye))
values.update({'Rotation.X':0,'Rotation.Y':math.degrees(math.asin(d[2]/distance)),
               'Rotation.Z':math.degrees(math.atan2(d[1],d[0]))})
tracks=[t for t in binding.get_tracks() if isinstance(t,unreal.MovieScene3DTransformTrack)]
assert len(tracks)==1,tracks
for section in tracks[0].get_sections():
    for channel in section.get_all_channels():
        if str(channel.channel_name) in values:
            for key in channel.get_keys():key.set_value(values[str(channel.channel_name)])
template=binding.get_object_template()
# Unregistered spawn templates do not expose OwnedComponents/get_cine_camera_component.
camera=unreal.find_object(None,template.get_path_name()+'.CameraComponent')
assert isinstance(camera,unreal.CineCameraComponent),template.get_path_name()
camera.set_editor_property('current_focal_length',40.0);camera.set_editor_property('current_aperture',5.6)
focus=camera.get_editor_property('focus_settings');focus.set_editor_property('manual_focus_distance',distance)
camera.set_editor_property('focus_settings',focus)
for child in seq.get_bindings():
    if child.get_parent() and str(child.get_parent().get_display_name())=='Cam_Insert':
        for track in child.get_tracks():
            values_by_property={'ManualFocusDistance':distance,'CurrentFocalLength':40.0,'CurrentAperture':5.6}
            if isinstance(track,unreal.MovieSceneFloatTrack) and str(track.get_property_name()) in values_by_property:
                value=values_by_property[str(track.get_property_name())]
                for section in track.get_sections():
                    for channel in section.get_all_channels():
                        channel.set_default(value)
                        for key in channel.get_keys():key.set_value(value)
assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False)
Path('P:/FoA/Saved/AnimShots/wake_insert_framing.json').write_text(json.dumps(dict(eye=eye,aim=aim,focal_mm=40,aperture=5.6,focus_cm=distance),indent=1))
print('Existing clock insert reframed around full clock, slap and pile; all timing retained')
