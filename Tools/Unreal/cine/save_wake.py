"""Verify LS_WakeUp's camera-cut track bCanBlend and save the sequence."""
import unreal
seq = unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
cut = next(t for t in seq.get_tracks() if t.get_class().get_name() == 'MovieSceneCameraCutTrack')
txt = unreal.SystemLibrary.get_object_name(cut)
blend = [p for p in str(cut.export_text() if hasattr(cut, 'export_text') else '').split(',') if 'CanBlend' in p]
print('CUT', txt, blend)
print('SAVED', unreal.EditorAssetLibrary.save_loaded_asset(seq, False))
