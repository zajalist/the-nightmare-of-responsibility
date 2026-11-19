"""Scratch: duplicate LS_WakeUp to TMP_anim_WakeRetime (FOA_MODE=dup) or delete it (FOA_MODE=del)."""
import os
import unreal
E = unreal.EditorAssetLibrary
T = '/Game/FoA/Cinematics/TMP_anim_WakeRetime'
if os.environ.get('FOA_MODE', 'dup') == 'dup':
    if E.does_asset_exist(T):
        E.delete_asset(T)
    print('DUP', E.duplicate_asset('/Game/FoA/Cinematics/LS_WakeUp', T))
else:
    a = unreal.load_asset(T)
    if a:
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(a)
    print('DEL', E.delete_asset(T))
