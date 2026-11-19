"""LS_WakeUp: dim L6_HitKey (the insert's dial-glow key) so the clock reads as a dark clock with a lit face, not a white
blob (hit_insert3 proof: 0.35 cd at 25 cm blew it out). FOA_CD (default 0.07)."""
import os
import unreal
seq = unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
b = next(x for x in seq.get_bindings() if str(x.get_display_name()) == 'L6_HitKey')
tpl = b.get_object_template()
lc = unreal.find_object(None, tpl.get_path_name() + '.LightComponent0') or next(
    (c for c in tpl.get_components_by_class(unreal.LocalLightComponent)), None)
assert lc, 'no light component on the L6_HitKey template'
before = lc.get_editor_property('intensity')
lc.set_editor_property('intensity', float(os.environ.get('FOA_CD', '0.07')))
print('HITKEY', before, '->', lc.get_editor_property('intensity'), unreal.EditorAssetLibrary.save_loaded_asset(seq, False))
