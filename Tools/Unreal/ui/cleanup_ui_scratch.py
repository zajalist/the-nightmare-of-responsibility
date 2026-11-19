"""Deletes the UI lane's scratch / superseded assets (never forced), then fixes redirectors under /Game/FoA/UI.
Run via ue_remote.py in its own run (nothing else loaded or edited in the same run)."""
import unreal

EAL = unreal.EditorAssetLibrary
AES = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
REG = unreal.AssetRegistryHelpers.get_asset_registry()
CANDIDATES = [
    '/Game/FoA/UI/Dev/WBP_TitleOption_A', '/Game/FoA/UI/Dev/WBP_TitleOption_B', '/Game/FoA/UI/Dev/WBP_TitleOption_C',
    '/Game/FoA/UI/Dev/T_UIDev_BedroomBackdrop',                           # title-option comparison only
    '/Game/FoA/UI/Style/Fonts/Font_FoA_Body', '/Game/FoA/UI/Style/Fonts/Font_FoA_Display',
    '/Game/FoA/UI/Style/Fonts/Font_FoA_Mono',                             # superseded by /Game/FoA/UI/Fonts/F_FoA_*
    '/Game/FoA/UI/Materials/MI_UI_SandButton_Quiet',                      # unused variant
]


def main():
    order = sorted(CANDIDATES, key=lambda p: 0 if '/Dev/WBP_' in p else 1)  # widgets before the texture they use
    deleted, kept = [], []
    for path in order:
        if not EAL.does_asset_exist(path):
            continue
        refs = [str(r) for r in EAL.find_package_referencers_for_asset(path, False)
                if not str(r).startswith(path) and str(r) not in deleted]
        if refs:
            kept.append((path, refs))
            continue
        asset = EAL.load_asset(path)
        AES.close_all_editors_for_asset(asset)
        del asset
        if EAL.delete_asset(path):
            deleted.append(path)
        else:
            kept.append((path, ['delete_asset returned False']))
    print('DELETED', deleted)
    print('KEPT', kept)
    redirs = [a.get_asset() for a in REG.get_assets_by_path('/Game/FoA/UI', recursive=True)
              if str(a.asset_class_path.asset_name) == 'ObjectRedirector']
    if redirs:
        unreal.AssetToolsHelpers.get_asset_tools().fix_up_referencers(redirs)
    print('REDIRECTORS_FIXED', len(redirs))


main()
