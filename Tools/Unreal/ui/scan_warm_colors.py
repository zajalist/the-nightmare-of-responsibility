"""Read-only (Hayba ui_layout_snapshot): list text colours and brush tints in the UI-lane widgets that are not neutral grey.
Monochrome rule: UMG draws after the mono post-process, so a warm UI colour shows on screen.
  python Tools/Unreal/ui/scan_warm_colors.py   -> Saved/UIShots/aaa/warm_colors.json"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

WBPS = ['/Game/FoA/UI/Game/WBP_HUD', '/Game/FoA/UI/Game/WBP_Phone', '/Game/FoA/UI/Game/WBP_DayRollover',
        '/Game/FoA/UI/Game/WBP_SkipHint', '/Game/FoA/UI/Widgets/Menus/WBP_Title', '/Game/FoA/UI/Widgets/Menus/WBP_MainMenu',
        '/Game/FoA/UI/Widgets/Menus/WBP_Pause', '/Game/FoA/UI/Widgets/Menus/WBP_Settings',
        '/Game/FoA/UI/Widgets/Menus/WBP_Credits', '/Game/FoA/UI/Widgets/Menus/WBP_BootSplash',
        '/Game/FoA/UI/Widgets/Common/WBP_ConfirmDialog', '/Game/FoA/UI/Widgets/Common/WBP_InputHint',
        '/Game/FoA/UI/Widgets/Common/WBP_SandButton', '/Game/FoA/UI/Widgets/Common/WBP_SettingRow_Slider',
        '/Game/FoA/UI/Widgets/Common/WBP_SettingRow_Switcher', '/Game/FoA/UI/Widgets/Common/WBP_Logotype']
out = []
for p in WBPS:
    off = 0
    while off is not None:
        d = hc.call('ui_layout_snapshot', {'widget_blueprint_path': p, 'screen_width': 1920, 'screen_height': 1080,
                                           'offset': off, 'limit': 50}).get('data') or {}
        for w in d.get('widgets', []):
            for kind, c in (('text', (w.get('text_info') or {}).get('color')), ('tint', (w.get('brush_info') or {}).get('tint')),
                            ('brush', (w.get('brush_info') or {}).get('brush_tint'))):
                if c and max(c[:3]) - min(c[:3]) > 0.02:
                    out.append({'asset': p, 'widget': w['name'], 'kind': kind, 'color': [round(v, 3) for v in c]})
        off = (off + 50) if d.get('has_more') else None
json.dump(out, open('P:/FoA/Saved/UIShots/aaa/warm_colors.json', 'w'), indent=1)
for o in out:
    print(o['asset'].rsplit('/', 1)[1], o['widget'], o['kind'], o['color'])
print('warm colours', len(out))
