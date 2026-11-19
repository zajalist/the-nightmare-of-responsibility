"""Settings box and arrow fix (the user's screenshot, 2026-11-18). In place, idempotent, compile and save per asset:
  python Tools/Unreal/ui/textfx/settings_box_fix.py
WBP_SandButton (plain-label buttons draw Img_CommandFocus, the grey focus box: the Settings tabs, battle commands):
  - the label no longer steps 12 px right on focus when it is a plain label (the box is the focus cue), so every
    tab's left edge stays put and the label stays inside its box; sand buttons keep the step
  - the sand vortex no longer shows on plain labels (it was the speck of dots left of the box)
  - plain-label height = max(52, LabelSize x 1.808 + 16): Darker Grotesque's line is 1.356 em, so a 32 pt label is
    58 px tall and overflowed the fixed 52 px box (the "p" crossed its bottom edge); now 8 px above and below.
    Horizontal padding 16 and 16 (was 12 and 16).
WBP_SettingRow_Switcher: the < and > glyphs were 32 pt next to a 24 pt value, so they sat about 10 px low; they are
  24 pt now, on the value's line."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, graph, save  # noqa: E402

SB = '/Game/FoA/UI/Widgets/Common/WBP_SandButton'
ROW = '/Game/FoA/UI/Widgets/Common/WBP_SettingRow_Switcher'
KML = '/Script/Engine.KismetMathLibrary'
FONT = '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'


def sand_button():
    nodes, edges = graph(SB, 'PushState')
    by = {n['node_id']: n for n in nodes}
    t = lambda i: by[i]['title']  # noqa: E731
    focus = lambda b: b.fn(f'{KML}:BooleanAND', A=b.get('bHovered'), B=b.fn(f'{KML}:Not_PreBool', A=b.get('bPlainLabel')))  # noqa: E731
    feed = lambda node, pin: next((x['from_node'] for x in edges if x['to_node'] == node and x['to_pin'] == pin), None)  # noqa: E731
    tofloat = next(x['to_node'] for x in edges if x['from_pin'] == 'bHovered' and t(x['to_node']).startswith('To Float')
                   ) if any(x['from_pin'] == 'bHovered' and t(x['to_node']).startswith('To Float') for x in edges) else None
    step = next(n['node_id'] for n in nodes if n['title'] == 'SelectFloat'
                and any(p['name'] == 'A' and p.get('default_value', '').startswith('12') for p in n['pins']))
    alpha = next(n['node_id'] for n in nodes if n['title'] == 'SelectFloat'
                 and any(x['to_node'] == n['node_id'] and x['from_pin'] == 'TextAlphaHover' for x in edges))
    b = B(SB, 'PushState')
    changed = False
    # the 12 px focus step and the vortex: sand buttons only (plain labels show the box instead)
    for node, pin in ((tofloat, 'InBool'), (step, 'bPickA')):
        if node and t(feed(node, pin)) == 'Get bHovered':
            b.refs.add(node)
            b.ops.append(dict(op='disconnect', node_id=node, pin_name=pin))
            b.link(focus(b), 'ReturnValue', node, pin)
            changed = True
    # the first pass rewired the text-alpha select by mistake: it follows bHovered for every button
    if t(feed(alpha, 'bPickA')) != 'Get bHovered':
        stray = feed(alpha, 'bPickA')  # the AND (and its NOT and gets) used by nothing else
        ins = [x['from_node'] for x in edges if x['to_node'] == stray]
        ins += [x['from_node'] for x in edges if x['to_node'] in ins]
        b.refs.add(alpha)
        b.ops.append(dict(op='remove', node_ids=[stray] + ins))
        b.link(b.get('bHovered')[0], 'bHovered', alpha, 'bPickA')
        changed = True
    if changed:
        b.run()
    nodes, edges = graph(SB, 'ApplyLook')
    by = {n['node_id']: n for n in nodes}
    heights = [n['node_id'] for n in nodes if n['title'].startswith('SetHeightOverride')]
    last = next(h for h in heights if not any(x['from_node'] == h and x['from_pin'] == 'then' for x in edges))
    if not any(x['to_node'] == last and x['to_pin'] == 'InHeightOverride' for x in edges):
        b = B(SB, 'ApplyLook')
        b.refs.add(last)
        h = b.fn(f'{KML}:FMax', A=52.0, B=b.fn(f'{KML}:Add_DoubleDouble', B=16.0, A=b.fn(
            f'{KML}:Multiply_DoubleDouble', A=b.get('LabelSize'), B=1.808)))  # LabelSize is a float
        b.link(h, 'ReturnValue', last, 'InHeightOverride')
        for n in nodes:
            if n['title'].startswith('SetPadding') and any(p['name'] == 'InPadding' and p.get('default_value', '').startswith('(Left=12.000000,Top=0.000000')
                                                          for p in n['pins']):
                b.ops.append(dict(op='set_pin', node_id=n['node_id'], pin_name='InPadding', value='(Left=16,Top=0,Right=16,Bottom=0)'))
        b.run()
    compile_bp(SB, widget=True)
    print('sand button', save(SB))


def row():
    for name in ('Txt_Prev', 'Txt_Next'):
        r = hc.call('ui_set_widget_properties', {'widget_blueprint_path': ROW, 'widget_name': name, 'properties': {
            'Font': {'FontObject': FONT, 'TypefaceFontName': 'SemiBold', 'Size': 24}}})
        assert r.get('ok') and not (r.get('data') or {}).get('failed_properties'), r
    compile_bp(ROW, widget=True)
    print('row', save(ROW))


if __name__ == '__main__':
    for path, step in ((SB, sand_button), (ROW, row)):
        token = editor_lock.acquire('ui', wait_s=900, ttl=150, areas=[path])
        try:
            assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
            step()
        finally:
            if token:
                hc.release('ui', token)
                editor_lock.forget('ui', token)
