"""Read-only (Hayba): every sound reference in the UI-lane Blueprints: SoundBase pin defaults in every graph and
sound-typed class defaults. Prints asset, where, and the sound.  python Tools/Unreal/ui/scan_ui_sounds.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

BPS = ['/Game/FoA/UI/Framework/BP_FoAFrontEnd', '/Game/FoA/UI/Game/WBP_HUD', '/Game/FoA/UI/Game/WBP_Phone',
       '/Game/FoA/UI/Game/BP_Phone', '/Game/FoA/UI/Game/WBP_DayRollover', '/Game/FoA/UI/Widgets/Menus/WBP_Settings',
       '/Game/FoA/UI/Widgets/Menus/WBP_MainMenu', '/Game/FoA/UI/Widgets/Menus/WBP_Pause',
       '/Game/FoA/UI/Widgets/Menus/WBP_Title', '/Game/FoA/UI/Widgets/Common/WBP_SandButton',
       '/Game/FoA/UI/Widgets/Common/WBP_ConfirmDialog', '/Game/FoA/UI/Widgets/Common/WBP_SettingRow_Slider',
       '/Game/FoA/UI/Widgets/Common/WBP_SettingRow_Switcher', '/Game/FoA/UI/Widgets/Menus/WBP_Credits']
for bp in BPS:
    info = hc.call('blueprint_get_info', {'path': bp}).get('data') or {}
    graphs = sorted(set(info.get('functions') or []) | {'EventGraph'})
    for g in graphs:
        off = 0
        while off is not None:
            d = hc.call('blueprint_inspect_graph', {'path': bp, 'graph_name': g, 'offset': off}).get('data') or {}
            for n in d.get('nodes', []):
                for p in n.get('pins', []):
                    v = str(p.get('default_value') or p.get('default_object') or '')
                    if '/Audio/' in v or 'SFX' in v or 'Sound' in p['name'] and v:
                        print(bp.rsplit('/', 1)[1], g, n['title'].replace('\n', ' ')[:40], p['name'], v)
            off = ((d.get('page') or {}).get('nodes') or {}).get('next_offset')
    cls = bp.rsplit('/', 1)[1]
    props = (hc.call('object_get_property', {'path': f'{bp}.Default__{cls}_C'}).get('data') or {}).get('properties', {})
    for k, v in props.items():
        if 'Sound' in str(v) or 'SFX' in str(v):
            print(cls, 'DEFAULT', k, v)
