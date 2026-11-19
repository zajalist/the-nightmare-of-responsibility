"""Save world lane assets (comma list in FOA_ASSETS) and cap the textures of DoorLock props at 512.
  $env:FOA_AREAS='/Game/FoA/Props'; python Tools/Unreal/ue_remote.py Tools/Lux3D/save_props.py FOA_ASSETS=/Game/..,/Game/.."""
import os
import unreal

EAL = unreal.EditorAssetLibrary
for p in [x for x in os.environ.get('FOA_ASSETS', '').split(',') if x]:
    a = EAL.load_asset(p)
    if isinstance(a, unreal.Texture2D) and '/Props/' in p:
        a.set_editor_property('max_texture_size', 512)
    print('save', p, EAL.save_asset(p, only_if_is_dirty=False))
