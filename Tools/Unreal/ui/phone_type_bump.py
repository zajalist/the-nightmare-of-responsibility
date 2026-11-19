"""Phone body text about 1.2x (main 2026-11-10, a modest secondary to anim's framing fix): task rows, inbox rows, the thread
and notes text, the lock banners and date lines. Headings, the big clock, tabs, the controls line and the status time
stay. Explicit sizes, so a rerun changes nothing.
  python Tools/Unreal/ui/phone_type_bump.py"""
import re
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402

P = '/Game/FoA/UI/Game/WBP_Phone'
SIZES = {**{f'Txt_Task{i}': 36 for i in range(4)}, **{f'Txt_Sender{i}': 34 for i in range(3)},
         'Txt_Message': 34, 'Txt_Notebook': 34, 'Txt_Notif0Head': 31, 'Txt_Notif0Body': 31, 'Txt_Notif1Head': 31,
         'Txt_Notif1Body': 31, 'Txt_DayLabel': 36, 'Txt_DayNum': 36, 'Txt_Crossed': 29, 'Txt_CrossedLabel': 29}
assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = editor_lock.acquire('ui', wait_s=120, ttl=120, areas=[P])
try:
    bad = []
    for w, size in SIZES.items():  # ui_set_text_style is MCP-only: rewrite Font's Size in place over TCP
        path = f'{P}.WBP_Phone:WidgetTree.{w}'
        font = (hc.call('object_get_property', {'path': path, 'properties': ['Font']}).get('data') or {}).get('properties', {}).get('Font', '')
        new = re.sub(r'(?<![A-Za-z])Size=\d+(\.\d+)?', f'Size={size}', font, count=1)  # not OutlineSize=
        r = hc.call('object_set_property', {'path': path, 'properties': {'Font': new}})
        if not r.get('ok') or f'Size={size}' not in new:
            bad.append((w, r.get('error') or 'no Size field'))
    c = hc.call('ui_compile_widget', {'widget_blueprint_path': P})['data']
    s = hc.call('asset_save', {'asset_paths': [P], 'force': True}).get('data') or {}
    print('failed', bad, '| compiled_clean', c.get('compiled_clean'), c.get('errors'), '| saved', s.get('saved_count'))
finally:
    if token:
        hc.release('ui', token)
        editor_lock.forget('ui', token)
m = hc.call('ui_query', {'path': P, 'class_filter': 'TextBlock', 'include_properties': True, 'include_slot': False})['data']['matches']
got = {w['name']: ((w.get('properties') or {}).get('font') or {}).get('size') for w in m}
print('sizes now', {k: got.get(k) for k in SIZES})
assert all(got.get(k) == v for k, v in SIZES.items()), 'size mismatch'
