"""Interaction montage blends to the production range: 0.25 s in, 0.35 s out (the wake-up's get-up 0.4 s out), every
AM_FoA_* in Player/Montages, edited in place (no rebuild, notifies untouched). Prints each montage's length and blends.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/montage_blends.py FOA_AREAS=/Game/FoA/Characters/Player"""
import unreal

D = "/Game/FoA/Characters/Player/Montages"
OUT_S = {"AM_FoA_WakeUp": 0.4}
EAL = unreal.EditorAssetLibrary
for path in EAL.list_assets(D, recursive=False):
    m = unreal.load_asset(path.split(".")[0])
    if not isinstance(m, unreal.AnimMontage):
        continue
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(m)
    for prop, secs in (("blend_in", 0.25), ("blend_out", OUT_S.get(m.get_name(), 0.35))):
        b = m.get_editor_property(prop)
        b.set_editor_property("blend_time", secs)
        b.set_editor_property("blend_option", unreal.AlphaBlendOption.SINUSOIDAL)  # eased, no linear kink
        m.set_editor_property(prop, b)
    EAL.save_loaded_asset(m, False)
    print(f"{m.get_name():26s} len={m.get_play_length():5.2f}s in={m.get_editor_property('blend_in').get_editor_property('blend_time')}"
          f" out={m.get_editor_property('blend_out').get_editor_property('blend_time')}")
