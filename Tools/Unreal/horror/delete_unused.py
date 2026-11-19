"""Deletes the horror lane's superseded trial assets after a referencer check (separate run; editors closed first).
  $env:FOA_EXCLUSIVE='1'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/delete_unused.py
MI_Jumpscare_SandSkin: the M_SandOverlay coat did not show on the dark skin. SM_SandMonster: the splat shell is
unlit near-black and read as nothing at 38 cm. BPL_FoAAudio: not a function-library type. None is referenced."""
import unreal

PATHS = ['/Game/FoA/Gameplay/Jumpscare/MI_Jumpscare_SandSkin',
         '/Game/FoA/Gameplay/Jumpscare/Sand/SM_SandMonster/StaticMeshes/SM_SandMonster',
         '/Game/FoA/Audio/BP_RoomAudio']  # a function and a component both named Presence: rebuilt whole


def main():
    EAL = unreal.EditorAssetLibrary
    aes = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
    for p in PATHS:
        if not EAL.does_asset_exist(p):
            print('gone', p)
            continue
        # find_package_referencers_for_asset returns [] for in-use assets since the 21:50 relaunch: ask the registry
        reg = unreal.AssetRegistryHelpers.get_asset_registry()
        refs = [r for r in reg.get_referencers(p.split('.')[0], unreal.AssetRegistryDependencyOptions()) if str(r) != p.split('.')[0]]
        if refs:
            print('KEEP (referenced)', p, list(refs))
            continue
        aes.close_all_editors_for_asset(EAL.load_asset(p))
        print('deleted' if EAL.delete_asset(p) else 'FAILED', p)
    for d in ('/Game/FoA/Gameplay/Jumpscare/Sand', '/Game/FoA/Gameplay/Jumpscare/Monster'):
        if EAL.does_directory_exist(d) and not EAL.list_assets(d, recursive=True):
            EAL.delete_directory(d)
            print('removed folder', d)


main()
