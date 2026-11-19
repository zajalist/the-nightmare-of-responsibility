import unreal
p='/Game/FoA/Audio/BP_RoomAudio'
bp=unreal.load_asset(p)
cdo=unreal.get_default_object(bp.generated_class())
tracks=dict(cdo.get_editor_property('Tracks'))
for name,track in [('Dream','MUS_Dream_Loop'),('City','MUS_CityDrive_Loop')]:
    sound=unreal.load_asset('/Game/FoA/Audio/Music/'+track)
    assert sound,track
    tracks[unreal.Name(name)]=sound
cdo.set_editor_property('Tracks',tracks)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp)
print('Dream and city tracks assigned to existing crossfade')
