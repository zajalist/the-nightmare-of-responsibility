"""Keyboard and pad focus inside overlays (menufast, 2026-11-09): BP_FoAFrontEnd.FocusUI sets input mode with
InWidgetToFocus = the overlay itself, after its Construct already focused its first button, so the overlay ROOT kept
focus (keys report SObjectWidget) and Down/Enter/D-pad did nothing in Settings, Credits, the Confirm dialog and Pause.
Fix with the engine's DesiredFocusWidget (UUserWidget::NativeOnFocusReceived forwards root focus to it):
  each overlay forwards to the button its Construct focuses, and THAT button instance is focusable and forwards on to
  its Btn_Hit (FocusButton's target), so the forward lands on a real SButton.
v1 set this on the WBP_SandButton CLASS: the overlays' tree instances had been saved with bIsFocusable False as
overrides, so the forward hit a non-focusable SandButton and Slate fell back to the root (rec sweep_menufast r3).
v2 puts the class back to its defaults and sets only the four forward targets, per instance.
  python Tools/Unreal/ui/aaa_focus_fix.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402

W = '/Game/FoA/UI/Widgets'
SB = f'{W}/Common/WBP_SandButton'
PLAN = {f'{W}/Menus/WBP_Settings': 'Btn_TabGraphics', f'{W}/Menus/WBP_Credits': 'Btn_Back',
        f'{W}/Common/WBP_ConfirmDialog': 'Btn_Cancel', f'{W}/Menus/WBP_Pause': 'Btn_Resume'}


def props(path):
    return (hc.call('object_get_property', {'path': path, 'properties': ['bIsFocusable', 'DesiredFocusWidget']})
            .get('data') or {}).get('properties', {})


assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = editor_lock.acquire('ui', wait_s=300, ttl=120, areas=[SB] + list(PLAN))
try:
    for k, v in (('bIsFocusable', False), ('DesiredFocusWidget', '(WidgetName="")')):  # the class as it was
        r = hc.call('blueprint_set_defaults', {'path': SB, 'properties': {k: v}})
        print('SandButton', k, r.get('ok'), r.get('error') or '')
    c = hc.call('ui_compile_widget', {'widget_blueprint_path': SB})['data']
    print('SandButton compiled_clean', c.get('compiled_clean'), 'saved',
          hc.call('ui_save_widget', {'widget_blueprint_path': SB})['data'].get('saved'))
    for bp, target in PLAN.items():
        n = bp.split('/')[-1]
        r = hc.call('blueprint_set_defaults', {'path': bp, 'properties': {'DesiredFocusWidget': f'(WidgetName="{target}")'}})
        # the root must take focus for the forward to fire: ConfirmDialog's was not (restartproof: the pad's Left/A went
        # to the game viewport under "Restart the day?")
        hc.call('blueprint_set_defaults', {'path': bp, 'properties': {'bIsFocusable': True}})
        r2 = hc.call('ui_set_widget_properties', {'widget_blueprint_path': bp, 'widget_name': target, 'properties': {
            'bIsFocusable': True, 'DesiredFocusWidget': '(WidgetName="Btn_Hit")'}})
        c = hc.call('ui_compile_widget', {'widget_blueprint_path': bp})['data']
        s = hc.call('ui_save_widget', {'widget_blueprint_path': bp})['data']
        root, inst = props(f'{bp}.Default__{n}_C'), props(f'{bp}.{n}:WidgetTree.{target}')
        print(n, r.get('ok'), (r2.get('data') or {}).get('failed') or r2.get('error') or '', 'compiled_clean',
              c.get('compiled_clean'), c.get('errors'), 'saved', s.get('saved'), '| root ->', root.get('DesiredFocusWidget'),
              '|', target, inst.get('bIsFocusable'), inst.get('DesiredFocusWidget'))
        assert f'"{target}"' in root.get('DesiredFocusWidget', '') and root.get('bIsFocusable') == 'True' and inst.get('bIsFocusable') == 'True' and \
            '"Btn_Hit"' in inst.get('DesiredFocusWidget', '') and c.get('compiled_clean'), (n, root, inst)
finally:
    if token:
        hc.release('ui', token)
        editor_lock.forget('ui', token)
print('SandButton class now', props(f'{SB}.Default__WBP_SandButton_C'))
