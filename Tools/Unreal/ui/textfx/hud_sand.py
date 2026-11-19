"""Text FX kit on the Level 1 HUD's thought lines (WBP_HUD Txt_Narration): each line now forms from sand inside the
existing halo (Calm), shivers when he is shocked (Shock: a headache blink in the last 2.5 s, or a line that starts with
"Ow" or ends with "?" or "!"), and scatters as sand when it is cleared instead of vanishing. In place, idempotent:
  python Tools/Unreal/ui/textfx/hud_sand.py tree     Brd_Narration > Ret_Narration (RetainerBox, MI_UI_SandText_HUD) > Txt_Narration
  python Tools/Unreal/ui/textfx/hud_sand.py graphs   NarrSand (params per SubStep tick), hooks in HandleNarration,
                                                     SubStep, ClearNarration and SetHeadacheBlink
Existing behaviour kept: the 0.26 s rise and fade (SubStep), the read-time ClearNarration timer, subtitles off."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, entry_of, graph, is_empty, ok, save  # noqa: E402

HUD = '/Game/FoA/UI/Game/WBP_HUD'
HUDC = HUD + '.WBP_HUD_C'
MI = '/Game/FoA/UI/Materials/MI_UI_SandText_HUD.MI_UI_SandText_HUD'
KML, KSL, KSTR, KTL = ('/Script/Engine.KismetMathLibrary', '/Script/Engine.KismetSystemLibrary',
                       '/Script/Engine.KismetStringLibrary', '/Script/Engine.KismetTextLibrary')
GS, W, TB, RB = '/Script/Engine.GameplayStatics', '/Script/UMG.Widget', '/Script/UMG.TextBlock', '/Script/UMG.RetainerBox'
MID = '/Script/Engine.MaterialInstanceDynamic'
DT = 0.0167
STEP = sys.argv[1] if len(sys.argv) > 1 else ''


def names():
    return str(hc.call('ui_query', {'path': HUD}).get('data'))


def tree():
    if 'Ret_Narration' not in names():
        # a Border holds one child: park the text on Ovl_Frame, put the retainer in the border, then the text back in it
        ok(hc.call('ui_reparent_element', {'widget_blueprint_path': HUD, 'widget_name': 'Txt_Narration',
                                           'new_parent_name': 'Ovl_Frame'}), 'park')
        ok(hc.call('ui_add_element', {'widget_blueprint_path': HUD, 'child_class': 'RetainerBox', 'parent_widget_name': 'Brd_Narration',
                                      'name': 'Ret_Narration'}), 'retainer')
        ok(hc.call('ui_reparent_element', {'widget_blueprint_path': HUD, 'widget_name': 'Txt_Narration',
                                           'new_parent_name': 'Ret_Narration'}), 'text')
        ok(hc.call('ui_set_variable', {'widget_blueprint_path': HUD, 'widget_name': 'Ret_Narration', 'is_variable': True}), 'var')
    r = hc.call('ui_set_widget_properties', {'widget_blueprint_path': HUD, 'widget_name': 'Ret_Narration', 'properties': {
        'EffectMaterial': MI, 'TextureParameter': 'Texture', 'Visibility': 'HitTestInvisible'}})
    assert r.get('ok') and not (r.get('data') or {}).get('failed_properties'), r
    # room inside the retainer for grains blown in from the left and the echo below; the halo keeps its old size
    for name, props in (('Txt_Narration', {'Margin': '(Left=24,Top=12,Right=32,Bottom=22)'}),
                        ('Brd_Narration', {'Padding': '(Left=48,Top=10,Right=40,Bottom=0)'})):
        r = hc.call('ui_set_widget_properties', {'widget_blueprint_path': HUD, 'widget_name': name, 'properties': props})
        assert r.get('ok') and not (r.get('data') or {}).get('failed_properties'), r
    compile_bp(HUD, widget=True)
    print('tree', save(HUD))


def node_by(nodes, title, **pins):
    for n in nodes:
        if n['title'].replace('\n', ' ').startswith(title) and all(
                any(p['name'] == k and p.get('default_value') == v for p in n['pins']) for k, v in pins.items()):
            return n['node_id']
    raise LookupError(title)


def graphs():
    have = {v['name'] for v in hc.call('blueprint_get_info', {'path': HUD})['data'].get('variables', [])}
    for name, typ, val in (('NarrShock', 'real', '0.0'), ('NarrOut', 'bool', 'false'), ('NarrOutT', 'real', '0.0'),
                           ('HeadacheAt', 'real', '-100.0')):
        if name not in have:
            ok(hc.call('blueprint_add_variable', {'path': HUD, 'variable_name': name, 'variable_type': typ, 'default_value': val,
                                                   'category': 'HUD|Motion'}), name)
    if 'NarrSand' not in hc.call('blueprint_get_info', {'path': HUD})['data']['functions']:
        ok(hc.call('blueprint_add_function', {'path': HUD, 'function_name': 'NarrSand'}), 'NarrSand')
    compile_bp(HUD, widget=True)

    if is_empty(HUD, 'NarrSand'):  # one SubStep tick of the sand: form, shiver, scatter, and the deferred clear
        e, _, _ = entry_of(HUD, 'NarrSand')
        b = B(HUD, 'NarrSand')

        def ramp(v, span):
            return b.fn(f'{KML}:FClamp', Value=b.fn(f'{KML}:Divide_DoubleDouble', A=v, B=span), Min=0.0, Max=1.0)
        mid = b.fn(f'{RB}:GetEffectMaterial', self=b.get('Ret_Narration'))
        out_t = b.set('NarrOutT', b.fn(f'{KML}:SelectFloat', A=b.fn(f'{KML}:Add_DoubleDouble', A=b.get('NarrOutT'), B=DT),
                                         B=0.0, bPickA=b.get('NarrOut')))
        shock = b.fn(f'{KML}:Greater_DoubleDouble', A=b.get('NarrShock'), B=0.0)
        rev = b.fn(f'{KML}:Ease', A=0.0, B=1.0, EasingFunc='EaseOut', BlendExp=4.0,
                   Alpha=ramp(b.get('SubT'), b.fn(f'{KML}:SelectFloat', A=0.3, B=0.6, bPickA=shock)))
        shv = b.fn(f'{KML}:Ease', A=b.get('NarrShock'), B=0.0, EasingFunc='EaseOut', BlendExp=2.0, Alpha=ramp(b.get('SubT'), 0.9))
        out = b.fn(f'{KML}:Ease', A=0.0, B=1.0, EasingFunc='EaseIn', BlendExp=2.0, Alpha=ramp(b.get('NarrOutT'), 0.42))
        p1 = b.fn(f'{MID}:SetScalarParameterValue', self=mid, ParameterName='Reveal', Value=rev)
        p2 = b.fn(f'{MID}:SetScalarParameterValue', self=mid, ParameterName='Shiver', Value=shv)
        p3 = b.fn(f'{MID}:SetVectorParameterValue', self=mid, ParameterName='State', Value=b.fn(f'{KML}:MakeColor', R=0.0, G=0.0, B=0.0, A=out))
        done = b.node('branch', {'Condition': b.fn(f'{KML}:BooleanAND', A=b.get('NarrOut'),
                                                    B=b.fn(f'{KML}:GreaterEqual_DoubleDouble', A=b.get('NarrOutT'), B=0.45))})
        b.chain(e, out_t, p1, p2, p3, done, b.set('NarrOut', False),
                b.fn(f'{TB}:SetText', self=b.get('Txt_Narration'), InText=''),
                b.fn(f'{W}:SetVisibility', self=b.get('Brd_Narration'), InVisibility='Collapsed'),
                b.fn(f'{KSL}:K2_ClearTimer', FunctionName='SubStep'))
        b.run()

    nodes, edges = graph(HUD, 'SubStep')
    if not any('NarrSand' in n['title'].replace(' ', '') for n in nodes):
        # SubStep: NarrSand before its stop branch; the stop now waits for the form (0.95 s) and never cuts a scatter
        tr, br = node_by(nodes, 'SetRenderTranslation'), node_by(nodes, 'Branch')
        ge = node_by(nodes, 'float >= float')
        b = B(HUD, 'SubStep')
        call = b.fn(f'{HUDC}:NarrSand')
        both = b.fn(f'{KML}:BooleanAND', A=(ge, 'ReturnValue'), B=b.fn(f'{KML}:Not_PreBool', A=b.get('NarrOut')))
        b.ops += [dict(op='disconnect', node_id=tr, pin_name='then'), dict(op='disconnect', node_id=br, pin_name='Condition'),
                  dict(op='set_pin', node_id=ge, pin_name='B', value='0.95')]
        b.link(tr, 'then', call, 'execute'); b.link(call, 'then', br, 'execute')
        b.link(both, 'ReturnValue', br, 'Condition')
        b.run()

    nodes, edges = graph(HUD, 'HandleNarration')
    if not any(n['title'].startswith('Set NarrShock') for n in nodes):
        # HandleNarration: before SubT = 0, pick the mood and reset the sand (Reveal 0, State.A 0, not leaving)
        vis, sub = node_by(nodes, 'SetVisibility'), node_by(nodes, 'Set SubT')
        e = next(n['node_id'] for n in nodes if n['title'] == 'HandleNarration')
        b = B(HUD, 'HandleNarration')
        line = b.fn(f'{KTL}:Conv_TextToString', InText=(e, 'Line'))
        recent = b.fn(f'{KML}:Less_DoubleDouble', A=b.fn(f'{KML}:Subtract_DoubleDouble', A=b.fn(f'{GS}:GetTimeSeconds'),
                                                            B=b.get('HeadacheAt')), B=2.5)
        marks = b.fn(f'{KML}:BooleanOR', A=b.fn(f'{KSTR}:EndsWith', SourceString=line, InSuffix='?'),
                     B=b.fn(f'{KML}:BooleanOR', A=b.fn(f'{KSTR}:EndsWith', SourceString=line, InSuffix='!'),
                            B=b.fn(f'{KSTR}:StartsWith', SourceString=line, InPrefix='Ow')))
        shock = b.fn(f'{KML}:SelectFloat', A=1.0, B=0.0, bPickA=b.fn(f'{KML}:BooleanOR', A=recent, B=marks))
        mid = b.fn(f'{RB}:GetEffectMaterial', self=b.get('Ret_Narration'))
        seq = [b.set('NarrShock', shock), b.set('NarrOut', False), b.set('NarrOutT', 0.0),
               b.fn(f'{MID}:SetScalarParameterValue', self=mid, ParameterName='Reveal', Value=0.0),
               b.fn(f'{MID}:SetVectorParameterValue', self=mid, ParameterName='State', Value='(R=0,G=0,B=0,A=0)')]
        b.ops.append(dict(op='disconnect', node_id=vis, pin_name='then'))
        b.link(vis, 'then', seq[0], 'execute')
        b.chain(*seq)
        b.link(seq[-1], 'then', sub, 'execute')
        b.run()

    nodes, edges = graph(HUD, 'ClearNarration')
    if not any(n['title'].startswith('Branch') for n in nodes):
        # ClearNarration: a line on screen scatters (SubStep finishes the clear); nothing on screen clears at once
        e = next(n['node_id'] for n in nodes if n['title'] == 'ClearNarration')
        st = node_by(nodes, 'SetText')
        b = B(HUD, 'ClearNarration')
        up = b.node('branch', {'Condition': b.fn(f'{KML}:BooleanAND', A=b.fn(f'{W}:IsVisible', self=b.get('Brd_Narration')),
                                                  B=b.fn(f'{KML}:Not_PreBool', A=b.get('NarrOut')))})
        b.ops.append(dict(op='disconnect', node_id=e, pin_name='then'))
        b.link(e, 'then', up, 'execute')
        b.chain(up, b.set('NarrOut', True), b.set('NarrOutT', 0.0),
                b.fn(f'{KSL}:K2_SetTimer', FunctionName='SubStep', Time=DT, bLooping=True))
        b.link(up, 'else', st, 'execute')
        b.run()

    nodes, edges = graph(HUD, 'SetHeadacheBlink')
    if not any(n['title'].startswith('Set HeadacheAt') for n in nodes):
        last = node_by(nodes, 'SetRenderScale')
        outs = {(x['from_node'], x['from_pin']) for x in edges}
        last = next(n['node_id'] for n in nodes if n['title'].startswith('SetRenderScale') and (n['node_id'], 'then') not in outs)
        e = next(n['node_id'] for n in nodes if n['title'] == 'SetHeadacheBlink')
        b = B(HUD, 'SetHeadacheBlink')
        on = b.node('branch', {'Condition': b.fn(f'{KML}:Greater_DoubleDouble', A=(e, 'Amount'), B=0.05)})
        b.chain(last, on, b.set('HeadacheAt', b.fn(f'{GS}:GetTimeSeconds')))
        b.run()
    compile_bp(HUD, widget=True)
    print('graphs', save(HUD))


if __name__ == '__main__':
    token = editor_lock.acquire('ui', wait_s=600, ttl=240, areas=[HUD])
    try:
        assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
        {'tree': tree, 'graphs': graphs}[STEP]()
    finally:
        if token:
            hc.release('ui', token)
            editor_lock.forget('ui', token)
