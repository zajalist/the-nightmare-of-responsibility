"""Scoped repair of the saved wardrobe sequence. Preserve cuts, audio and later shots."""
import json,sys,shutil,math,importlib
from pathlib import Path
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/flow')
import repair_battle_intro_rig as repair
importlib.reload(repair)
from wardrobe_camera_path import opening_keys

PATH='/Game/FoA/Cinematics/Wardrobe/LS_WardrobeFall'
OUT=Path('P:/FoA/Saved/Integration/aim_dot_wardrobe')
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
seq=unreal.load_asset(PATH);assert seq
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
backup=OUT/'LS_WardrobeFall_before.uasset'
if not backup.exists():shutil.copy2('P:/FoA/Content/FoA/Cinematics/Wardrobe/LS_WardrobeFall.uasset',backup)
report=repair.process(seq,apply=True);assert not report['blockers'],report['blockers']
camera=next(b for b in seq.get_bindings() if str(b.get_display_name())=='Cam_01_TheDoor')
track=next(t for t in camera.get_tracks() if repair.kind(t)=='MovieScene3DTransformTrack')
protected=repair.protected(seq,[track])
section=track.get_sections()[0];channels={str(c.channel_name):c for c in section.get_all_channels()}
names=('Location.X','Location.Y','Location.Z','Rotation.X','Rotation.Y','Rotation.Z')
for name in names:
    for key in list(channels[name].get_keys()):channels[name].remove_key(key)
for t,eye,aim in opening_keys():
    delta=[b-a for a,b in zip(eye,aim)];length=math.sqrt(sum(x*x for x in delta))
    pitch=math.degrees(math.asin(delta[2]/length));yaw=math.degrees(math.atan2(delta[1],delta[0]))
    for name,value in zip(names,(*eye,0.,pitch,yaw)):
        channels[name].add_key(unreal.FrameNumber(round(t*30)),value,0.,unreal.MovieSceneTimeUnit.DISPLAY_RATE,unreal.MovieSceneKeyInterpolation.LINEAR)
assert repair.protected(seq,[track])==protected,'Unrelated sequence changed'
assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False)
report.update(opening_frames=70,protected_after_rig=protected)
(OUT/'wardrobe_opening_applied.json').write_text(json.dumps(report,indent=1,default=str))
print('Wardrobe opening saved',report['changed'],report['opening_frames'])
