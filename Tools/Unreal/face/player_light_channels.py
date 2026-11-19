"""BP_FoAPlayer lighting channels (main 2026-11-10: the phone's close screen light saturates his hair into a white fan;
UI puts the phone's ScreenLight on channel 2 only). The lit body and clothes take channels 0+2, so the phone still
lights his skin and clothes; Hair and Eyebrows stay on channel 0 only, so the phone never lights the hair.
Component templates only (no graph change). FOA_OP=revert puts the listed ones back to channel 0 only.
  python Tools/Unreal/ue_remote.py Tools/Unreal/face/player_light_channels.py   (lease on the BP asset), then compile
  and save with Hayba (blueprint_compile, asset_save)."""
import os

import unreal

LIT = ('Body', 'Face', 'BootsWornMesh', 'StartOutfit', 'StartPants', 'StartSocks', 'Shirt', 'Trousers', 'Socks', 'Tie', 'Suit')
KEEP0 = ('Hair', 'Eyebrows')
on2 = os.environ.get('FOA_OP') != 'revert'
bp = unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
seen = {}
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    d = lib.get_data(h)
    name = str(lib.get_variable_name(d))
    if name not in LIT + KEEP0:
        continue
    c = lib.get_object_for_blueprint(d, bp)
    ch = c.get_editor_property('lighting_channels')
    if name in LIT:
        ch.set_editor_property('channel0', True)
        ch.set_editor_property('channel2', on2)
        c.set_editor_property('lighting_channels', ch)
    ch = c.get_editor_property('lighting_channels')
    seen[name] = [int(ch.get_editor_property(f'channel{i}')) for i in range(3)]
assert sorted(seen) == sorted(LIT + KEEP0), sorted(seen)
assert all(seen[n] == [1, 0, int(on2)] for n in LIT) and all(seen[n] == [1, 0, 0] for n in KEEP0), seen
bp.modify()
print('FOA_CHANNELS', seen)
