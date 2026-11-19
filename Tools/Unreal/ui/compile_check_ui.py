"""Compile every UI-lane Blueprint and Widget Blueprint the AAA pass touched (Hayba) and report any that do not compile
clean (main's rule: never leave one failing in memory). Waits for PIE to be idle first.
  python Tools/Unreal/ui/compile_check_ui.py"""
import sys
import time

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

W = '/Game/FoA/UI/Widgets'
WIDGETS = [f'{W}/Menus/WBP_BootSplash', f'{W}/Menus/WBP_Title', f'{W}/Menus/WBP_MainMenu', f'{W}/Menus/WBP_Pause',
           f'{W}/Menus/WBP_Settings', f'{W}/Menus/WBP_Credits', f'{W}/Common/WBP_SandButton', f'{W}/Common/WBP_ConfirmDialog',
           f'{W}/Common/WBP_SettingRow_Slider', f'{W}/Common/WBP_SettingRow_Switcher', '/Game/FoA/UI/Game/WBP_HUD',
           '/Game/FoA/UI/Game/WBP_Phone', '/Game/FoA/UI/Game/WBP_DayRollover', '/Game/FoA/UI/Game/WBP_Debug']
BPS = ['/Game/FoA/UI/Framework/BP_FoAFrontEnd', '/Game/FoA/UI/Game/BP_Phone']
while (hc.call('editor_get_state', {}).get('data') or {}).get('pie_running'):
    time.sleep(5)
bad = []
for w in WIDGETS:
    d = hc.call('ui_compile_widget', {'widget_blueprint_path': w}).get('data') or {}
    if not d.get('compiled_clean'):
        bad.append((w, d.get('errors')))
for b in BPS:
    d = hc.call('blueprint_compile', {'path': b}).get('data') or {}
    if not d.get('compiled') or d.get('error_count'):
        bad.append((b, d.get('errors')))
print('checked', len(WIDGETS) + len(BPS), 'failing', bad)
