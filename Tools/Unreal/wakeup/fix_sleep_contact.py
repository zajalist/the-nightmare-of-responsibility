"""Only the existing lying clip placement in LS_WakeUp; retain all cameras, timing and edge animation."""
import importlib
import sys
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/wakeup')
import wake_common as W
importlib.reload(W)
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
p=W.load_placement();rig=W.player_rig();m=W.m
clip=unreal.load_asset(W.WAKE+'/AS_FoA_Wake_Lying');assert clip
a=W.UeAdapter({'lying':clip});pose=a.pose_at('lying',0)
pelvis=a.wget(pose,'pelvis')[0];head=a.wget(pose,'head')[0];chest=a.wget(pose,'spine_03')[0]
yaw=p['lay']['yaw'];mid=m.lerp(pelvis,chest,.5)
zero=W.comp_to_world(mid,(0,0,0),yaw,rig)
duvet=W.trace_down(270,-191);assert duvet and 45<duvet<85,duvet
pelvis_zero=W.comp_to_world(pelvis,(0,0,0),yaw,rig)
loc=(270-zero[0],-191-zero[1],duvet+14*rig['mesh_scale']-pelvis_zero[2])
seq=unreal.load_asset(W.LS_PATH)
binding=next(b for b in seq.get_bindings() if str(b.get_display_name())=='Player')
track=next(t for t in binding.get_tracks() if isinstance(t,unreal.MovieScene3DTransformTrack))
rate=seq.get_display_rate();fps=rate.numerator/rate.denominator
values={'Location.X':loc[0],'Location.Y':loc[1],'Location.Z':loc[2],
        'Rotation.X':0.0,'Rotation.Y':0.0,'Rotation.Z':yaw}
count=0
for sec in track.get_sections():
    for channel in sec.get_all_channels():
        name=str(channel.channel_name)
        if name not in values:continue
        for key in channel.get_keys():
            if key.get_time().frame_number.value/fps < W.T['edge']:
                key.set_value(values[name]);count+=1
assert count==6,count
p['rig']=rig
p['lay'].update(loc=loc,pitch=0.0,duvet=duvet,head=W.comp_to_world(head,loc,yaw,rig),
                pelvis=W.comp_to_world(pelvis,loc,yaw,rig))
assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False)
W.save_placement(p)
print('Saved flat lying transform only; full-body contact remains subject to visual validation',p['lay'])
