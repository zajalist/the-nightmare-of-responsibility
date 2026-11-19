"""Insert shot: tilt Cam_Insert up so the raised hand stays in frame at the apex of the slap (v2 slap rises 22 cm).
  FOA_PITCH=-29.5 (default). Only Cam_Insert's Rotation.Y keys change; everything else in LS_WakeUp is untouched."""
import os
import unreal
seq = unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
pitch = float(os.environ.get('FOA_PITCH', '-29.5'))
b = next(x for x in seq.get_bindings() if str(x.get_display_name()) == 'Cam_Insert')
tr = next(t for t in b.get_tracks() if isinstance(t, unreal.MovieScene3DTransformTrack))
ch = {str(c.channel_name): c for c in tr.get_sections()[0].get_all_channels()}['Rotation.Y']
before = [k.get_value() for k in ch.get_keys()]
for k in ch.get_keys():
    k.set_value(pitch)
print('INSERT pitch', before, '->', [k.get_value() for k in ch.get_keys()], unreal.EditorAssetLibrary.save_loaded_asset(seq, False))
