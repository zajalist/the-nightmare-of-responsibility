"""Translate the straight sleeping body and its close cameras inside the existing bed."""
import json,sys
from pathlib import Path
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/wakeup')
import wake_common as W
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
p=W.load_placement();lay=p['lay']
# Canonical sock surface X157.54 and hair crown X343.57 leave a 20 cm fit window.
shift=20.0;delta=shift-lay.get('foot_clearance_shift_cm',0.0)
seq=unreal.load_asset(W.LS_PATH)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
rate=seq.get_display_rate();fps=rate.numerator/rate.denominator
changed={}
for binding in seq.get_bindings():
    name=str(binding.get_display_name())
    if name not in ('Player','Cam_POV','Cam_PushIn'):continue
    count=0
    for track in binding.get_tracks():
        if not isinstance(track,unreal.MovieScene3DTransformTrack):continue
        for section in track.get_sections():
            for channel in section.get_all_channels():
                if str(channel.channel_name)!='Location.X':continue
                for key in channel.get_keys():
                    seconds=key.get_time().frame_number.value/fps
                    if name=='Player' and seconds>=W.T['edge']:continue
                    key.set_value(key.get_value()+delta);count+=1
    changed[name]=count
assert changed.get('Player')==1,changed
assert changed.get('Cam_POV',0)>0 and changed.get('Cam_PushIn',0)>0,changed
for key in ('loc','head','pelvis','head_end'):
    lay[key][0]+=delta
lay['foot_clearance_shift_cm']=shift
W.save_placement(p)
print('Pending native save',W.LS_PATH,'shift',delta,'channels',changed)
