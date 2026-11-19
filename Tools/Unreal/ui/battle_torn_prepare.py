"""Short structural preflight inside a battle-ui asset lease; no level save."""
import unreal
import os

def prepare():
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    bp=unreal.load_asset('/Game/FoA/Gameplay/Encounter/WBP_Encounter')
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    print('battle-ui structural preflight',unreal.SystemLibrary.get_engine_version())
    if os.environ.get('FOA_TORN_SAVE')=='1':
        for path in ('/Game/FoA/UI/Materials/MI_UI_BattleCardGrain',
                     '/Game/FoA/Gameplay/Encounter/Icons/T_Battle_TornMask',
                     '/Game/FoA/Gameplay/Encounter/Icons/T_Battle_Button'):
            assert unreal.EditorAssetLibrary.save_asset(path),path

prepare()
