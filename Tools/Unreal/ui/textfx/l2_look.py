"""Level 2's journey card and interview, restyled into the house family (ui lane owns their look and motion; the level2
lane owns their flow and text). In place, idempotent, compile and save in the same lease:
  python Tools/Unreal/ui/textfx/l2_look.py font        WBP_SandLine: instance-editable LineFont (+ bLineFont)
  python Tools/Unreal/ui/textfx/l2_look.py journey     WBP_L2Journey: ink plates off, soft halo, sand title, motion
  python Tools/Unreal/ui/textfx/l2_look.py interview   WBP_L2Interview: no plates or hint box, bottom scrim, motion
Look: no slanted plates, no red, no boxes around hints. Type over a soft dark falloff; titles form from sand; body
rows rise 8 px and fade in (paragraphs fade, words form: aaa_ui_direction.md); hints are plain grey sentences with
" / " read as " or " (" of " in counts). Text arrives through each widget's Refresh, which this script extends at its
tail (AnimateIn) and at its hint/status pins (CleanText), so the level2 lane's callers are untouched."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, entry_of, graph, is_empty, ok, save  # noqa: E402

SANDLINE = '/Game/FoA/UI/Widgets/Common/WBP_SandLine'
SANDLINE_C = SANDLINE + '.WBP_SandLine_C'
JOURNEY = '/Game/FoA/Level2/Journey/WBP_L2Journey'
INTERVIEW = '/Game/FoA/Level2/Journey/WBP_L2Interview'
FONT = '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
FADE = '/Game/FoA/UI/Textures/T_UI_FadeV.T_UI_FadeV'
DOT = '/Game/FoA/UI/Textures/T_UI_SoftDot.T_UI_SoftDot'
KML, KSL = '/Script/Engine.KismetMathLibrary', '/Script/Engine.KismetSystemLibrary'
KTL, KSTR = '/Script/Engine.KismetTextLibrary', '/Script/Engine.KismetStringLibrary'
TB, W = '/Script/UMG.TextBlock', '/Script/UMG.Widget'
INK, SUB, REST = 0.87, 0.43, 0.26          # #F0F0F0, #B0B0B0, #8C8C8C in linear
DT = 0.0167
STEP = sys.argv[1] if len(sys.argv) > 1 else ''


def col(v, a=1.0):
    return {'SpecifiedColor': [v, v, v, a]}


def font(typeface, size):
    return {'FontObject': FONT, 'TypefaceFontName': typeface, 'Size': size}


def xf(sx=1.0, sy=1.0, ty=0.0):
    return {'Translation': {'X': 0, 'Y': ty}, 'Scale': {'X': sx, 'Y': sy}, 'Shear': {'X': 0, 'Y': 0}, 'Angle': 0.0}


def text_sets(path):
    """Refresh's entry id, {text widget: its SetText node}, and {(node, pin): feeding node}."""
    e, nodes, edges = entry_of(path, 'Refresh')
    fed = {(ed['to_node'], ed['to_pin']): ed['from_node'] for ed in edges}
    sets = {ed['from_pin']: ed['to_node'] for ed in edges if ed['to_pin'] == 'self'
            and next(n for n in nodes if n['node_id'] == ed['to_node'])['title'].startswith('SetText')}
    return e, nodes, sets, fed


def text(typeface, size, v, shadow=True):
    p = {'Font': font(typeface, size), 'ColorAndOpacity': col(v), 'RenderTransform': xf()}
    if shadow:  # a soft drop under type that sits over the live street (no plate behind it any more)
        p.update(ShadowOffset={'X': 0, 'Y': 2}, ShadowColorAndOpacity=[0, 0, 0, 0.55])
    return p


def setp(path, name, properties=None, slot=None):
    r = hc.call('ui_set_widget_properties', {'widget_blueprint_path': path, 'widget_name': name,
                                             'properties': properties or {}, 'slot_props': slot or {}})
    d = r.get('data') or {}
    assert r.get('ok') and not d.get('failed_properties'), (name, r.get('error'), d.get('failed_properties'))


def tail(path, g):
    """The exec tail of a function graph (the one node whose 'then' leads nowhere)."""
    nodes, edges = graph(path, g)
    outs = {(e['from_node'], e['from_pin']) for e in edges}
    ends = [n['node_id'] for n in nodes if any(p['name'] == 'then' and p.get('direction') == 'output' for p in n['pins'])
            and (n['node_id'], 'then') not in outs and not n['title'].startswith('Branch')]
    assert len(ends) == 1, (g, ends)
    return ends[0], nodes, edges


def calls(nodes, fn):
    return any(fn in n['title'].replace(' ', '') for n in nodes)


def add_vars(path, rows):
    have = {v['name'] for v in hc.call('blueprint_get_info', {'path': path})['data'].get('variables', [])}
    for name, typ, val, extra in rows:
        if name not in have:
            ok(hc.call('blueprint_add_variable', {'path': path, 'variable_name': name, 'variable_type': typ,
                                                   'default_value': val, 'category': 'Look', **extra}), name)


def add_funcs(path, names):
    have = hc.call('blueprint_get_info', {'path': path})['data']['functions']
    for n in names:
        if n not in have:
            ok(hc.call('blueprint_add_function', {'path': path, 'function_name': n}), n)


def clean(path, set_text_ids, entry, pins, of=False):
    """Insert ToString -> Replace(' / ', ' or '|' of ') -> ToText between Refresh's input pin and each SetText."""
    b = B(path, 'Refresh')
    for sid, pin in zip(set_text_ids, pins):
        s = b.fn(f'{KTL}:Conv_TextToString', InText=(entry, pin))
        r = b.fn(f'{KSTR}:Replace', SourceString=s, From=' / ', To=' of ' if of else ' or ')
        t = b.fn(f'{KTL}:Conv_StringToText', InString=r)
        b.ops.append(dict(op='disconnect', node_id=sid, pin_name='InText'))
        b.link(t, 'ReturnValue', sid, 'InText')
    b.run()


def rise(b, widget, t, start, span, px=8.0, translate=True):
    """widget opacity = easeOut3(clamp((t - start) / span)); translation y = px x (1 - that)."""
    a = b.fn(f'{KML}:Ease', A=0.0, B=1.0, EasingFunc='EaseOut', BlendExp=3.0, Alpha=b.fn(
        f'{KML}:FClamp', Value=b.fn(f'{KML}:Divide_DoubleDouble', A=b.fn(f'{KML}:Subtract_DoubleDouble', A=t, B=start), B=span),
        Min=0.0, Max=1.0))
    out = [b.fn(f'{W}:SetRenderOpacity', self=b.get(widget), InOpacity=a)]
    if translate:
        out.append(b.fn(f'{W}:SetRenderTranslation', self=b.get(widget), Translation=b.fn(
            f'{KML}:MakeVector2D', X=0.0, Y=b.fn(f'{KML}:Lerp', A=px, B=0.0, Alpha=a))))
    return out


def intro_step(path, rows, end):
    """IntroStep: IntroT += dt; each (widget, start, span, translate) rises; stops at `end`."""
    if not is_empty(path, 'IntroStep'):
        return
    e, _, _ = entry_of(path, 'IntroStep')
    b = B(path, 'IntroStep')
    st = b.set('IntroT', b.fn(f'{KML}:Add_DoubleDouble', A=b.get('IntroT'), B=DT))
    seq = [st]
    for widget, start, span, tr in rows:
        seq += rise(b, widget, b.get('IntroT'), start, span, translate=tr)
    br = b.node('branch', {'Condition': b.fn(f'{KML}:GreaterEqual_DoubleDouble', A=b.get('IntroT'), B=end)})
    b.chain(e, *seq, br, b.fn(f'{KSL}:K2_ClearTimer', FunctionName='IntroStep'))
    b.run()


def animate_in(path, key_widget, extra=None):
    """AnimateIn: when key_widget's text differs from LastKey, restart the intro (and extra(b, entry) on change)."""
    if not is_empty(path, 'AnimateIn'):
        return
    e, _, _ = entry_of(path, 'AnimateIn')
    b = B(path, 'AnimateIn')
    now = b.fn(f'{KTL}:Conv_TextToString', InText=b.fn(f'{TB}:GetText', self=b.get(key_widget)))
    changed = b.node('branch', {'Condition': b.fn(f'{KSTR}:NotEqual_StrStr', A=now, B=b.get('LastKey'))})
    seq = [b.set('LastKey', now), b.set('IntroT', 0.0)]
    seq += extra(b) if extra else []
    seq += [b.fn(f'{path}.{path.rsplit("/", 1)[1]}_C:IntroStep'),
            b.fn(f'{KSL}:K2_SetTimer', FunctionName='IntroStep', Time=DT, bLooping=True)]
    b.chain(e, changed, *seq)
    b.run()


def hook(path, fn):
    """Call fn at the tail of Refresh (once)."""
    t, nodes, _ = tail(path, 'Refresh')
    if calls(nodes, fn):
        return
    b = B(path, 'Refresh')
    b.chain(t, b.fn(f'{path}.{path.rsplit("/", 1)[1]}_C:{fn}'))
    b.run()


# ---- steps --------------------------------------------------------------------------------------------------------
def step_font():
    add_vars(SANDLINE, [('bLineFont', 'bool', 'false', {'instance_editable': True}),
                        ('LineFont', 'struct:/Script/SlateCore.SlateFontInfo', '', {'instance_editable': True})])
    t, nodes, _ = tail(SANDLINE, 'Play')
    if not calls(nodes, 'SetFont'):
        b = B(SANDLINE, 'Play')
        br = b.node('branch', {'Condition': b.get('bLineFont')})
        b.chain(t, br, b.fn(f'{TB}:SetFont', self=b.get('Txt_Line'), InFontInfo=b.get('LineFont')))
        b.run()
    compile_bp(SANDLINE, widget=True)
    print('font', save(SANDLINE))


def step_journey():
    P = JOURNEY
    for name in ('TaskFrame', 'TaskBack', 'TaskTag'):
        setp(P, name, {'Visibility': 'Collapsed'})
    # the card's backing: one soft dark falloff under the type, the HUD subtitle's halo at card size
    # centred on the card's type (x 430, y 860 of 1080) and large enough that the place name and the hint sit well
    # inside the falloff: the street is near-white sand (UIJ run_20261118_0043 card_070 had both on the halo's rim)
    setp(P, 'Page', {'Background': {'ResourceObject': DOT, 'DrawAs': 'Image', 'TintColor': col(0.0)},
                     'BrushColor': [0, 0, 0, 0.96], 'RenderTransform': xf()},
         {'position': [-570, 480], 'size': [2000, 1400]})
    setp(P, 'Txt_Title', {'RenderOpacity': 0.0})          # still the data the level2 lane writes; Line_Title shows it
    setp(P, 'Txt_Progress', text('SemiBold', 22, SUB))
    setp(P, 'Txt_Body', dict(text('Medium', 26, INK), LineHeightPercentage=1.0))
    setp(P, 'Txt_Hint', text('Medium', 21, SUB))  # over a live street, not black: rest grey was unreadable
    setp(P, 'Bar_L2Employability', {'FillColorAndOpacity': [0.62, 0.62, 0.62, 1.0]}, {'size': [660, 4]})
    if 'Line_Title' not in str(hc.call('ui_query', {'path': P}).get('data')):
        ok(hc.call('ui_build_tree', {'widget_blueprint_path': P, 'parent_widget_name': 'RootCanvas', 'tree': {
            'class': SANDLINE_C, 'name': 'Line_Title',
            'slot_props': {'anchors_min': [0, 1], 'anchors_max': [0, 1], 'alignment': [0, 1], 'position': [52, -364],
                           'size': [760, 96], 'z_order': 3}}}), 'Line_Title')
        ok(hc.call('ui_set_variable', {'widget_blueprint_path': P, 'widget_name': 'Line_Title', 'is_variable': True}), 'var')
    setp(P, 'Line_Title', {'Scale': 4.2, 'bLineFont': True, 'LineFont': font('ExtraBold', 46), 'Visibility': 'HitTestInvisible'})
    compile_bp(P, widget=True)
    add_vars(P, [('LastKey', 'string', '', {}), ('IntroT', 'real', '0.0', {})])
    add_funcs(P, ['AnimateIn', 'IntroStep'])
    compile_bp(P, widget=True)
    intro_step(P, [('Txt_Progress', 0.15, 0.3, True), ('Bar_L2Employability', 0.15, 0.3, False),
                   ('Txt_Body', 0.25, 0.32, True), ('Txt_Hint', 0.45, 0.3, True)], 0.8)
    animate_in(P, 'Txt_Title', lambda b: [b.fn(f'{SANDLINE_C}:Play', self=b.get('Line_Title'), Line=b.fn(
        f'{TB}:GetText', self=b.get('Txt_Title')), Mood=2, Hold=0.0)])
    e, _, sets, fed = text_sets(P)
    if fed.get((sets['Txt_Hint'], 'InText')) == e:
        clean(P, [sets['Txt_Hint']], e, ['Hint'])
    hook(P, 'AnimateIn')
    compile_bp(P, widget=True)
    print('journey', save(P))


def step_interview():
    P = INTERVIEW
    for name in ('ConversationEdge', 'SpeakerBack', 'SpeakerTag', 'StatusPanel', 'EvidencePanel'):
        setp(P, name, {'Visibility': 'Collapsed'})
    # bottom scrim: Refresh sizes this panel (336 or 376 tall); a 1.6 x render scale from the bottom edge makes the
    # falloff start well above the speaker without touching the level2 lane's layout code
    setp(P, 'ConversationPanel', {'Background': {'ResourceObject': FADE, 'DrawAs': 'Image', 'TintColor': col(0.0)},
                                  'BrushColor': [0, 0, 0, 0.92],
                                  'RenderTransform': xf(1.1, 1.6, 30.0),  # past the bottom edge: no lit strip under it
                                  'RenderTransformPivot': {'X': 0.5, 'Y': 1.0}})
    setp(P, 'Txt_Speaker', text('SemiBold', 26, SUB), {'size': [544, 40]})
    setp(P, 'Txt_Question', dict(text('SemiBold', 30, INK), LineHeightPercentage=1.0))
    for i in (1, 2):  # the ink fan stepped answers 24 px right each; one left edge now (Refresh moves only answer 0)
        setp(P, f'Btn_Answer{i}', slot={'position': [56, -154 if i == 1 else -82], 'size': [92, 64]})
    for i in range(3):
        setp(P, f'Txt_Answer{i}', text('Medium', 26, INK, shadow=False))
        setp(P, f'AnswerPad{i}', {'Background': {'DrawAs': 'NoDrawType'}, 'Padding': [12, 6, 12, 6]})
    setp(P, 'Txt_Status', text('SemiBold', 22, SUB))
    setp(P, 'Txt_Evidence', text('Medium', 20, SUB))
    setp(P, 'Txt_Hint', text('Medium', 20, REST, shadow=False))
    compile_bp(P, widget=True)
    e, nodes, sets, fed = text_sets(P)
    # unselected answers rest at half brightness (was 0.95: focus showed only as the red ink tag)
    dim = [n['node_id'] for n in nodes if n['title'] == 'SelectFloat' and any(
        p['name'] == 'B' and p.get('default_value') in ('0.95', '0.950000') for p in n['pins'])]
    if dim:
        b = B(P, 'Refresh')
        for nid in dim:
            b.ops.append(dict(op='set_pin', node_id=nid, pin_name='B', value='0.5'))
        b.run()
    raw = [f for f in ('Txt_Hint', 'Txt_Evidence') if fed.get((sets[f], 'InText')) == e]
    if raw:
        clean(P, [sets[f] for f in raw], e, [f[4:] for f in raw])
    if fed.get((sets['Txt_Status'], 'InText')) == e:
        clean(P, [sets['Txt_Status']], e, ['Status'], of=True)
    add_vars(P, [('LastKey', 'string', '', {}), ('IntroT', 'real', '0.0', {})])
    add_funcs(P, ['AnimateIn', 'IntroStep'])
    compile_bp(P, widget=True)
    intro_step(P, [('Txt_Speaker', 0.0, 0.26, True), ('Txt_Question', 0.06, 0.32, True),
                   ('Btn_Answer0', 0.2, 0.26, False), ('Btn_Answer1', 0.25, 0.26, False),
                   ('Btn_Answer2', 0.3, 0.26, False), ('Txt_Hint', 0.4, 0.3, False)], 0.75)
    animate_in(P, 'Txt_Question')
    hook(P, 'AnimateIn')
    compile_bp(P, widget=True)
    print('interview', save(P))


if __name__ == '__main__':
    target = {'font': SANDLINE, 'journey': JOURNEY, 'interview': INTERVIEW}[STEP]
    token = editor_lock.acquire('ui', wait_s=600, ttl=240, areas=[target])  # queues behind any PIE burst's EXCLUSIVE
    try:
        assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
        {'font': step_font, 'journey': step_journey, 'interview': step_interview}[STEP]()
    finally:
        if token:
            hc.release('ui', token)
            editor_lock.forget('ui', token)
