"""Text FX kit, widget half: WBP_SandLine (/Game/FoA/UI/Widgets/Common), one line of type that forms from black sand,
holds almost still, and blows away. Drop it where a TextBlock would go, then:

  Play(Line: Text, Mood: int, Hold: float)    Hold <= 0 keeps the line up until Dismiss
      Mood 0 Calm      letters settle out of sand left to right over 0.8 s
      Mood 1 Shock     forms in 0.3 s, the rows shiver and a grey split ghost trails, decaying over 0.9 s, one light sweep
      Mood 2 Matters   Calm, then one light sweep across the word (new knowledge, a goal that changed)
      Mood 3 Quick     forms in 0.35 s, nothing else (long lines, repeats)
  Dismiss()           the words scatter to the right as sand over 0.42 s, then the widget collapses
  Txt_Line            the TextBlock: set its font, size, colour and wrap in the host's designer or from the host graph
  Scale (instance editable, default 2.5)   grain size in px; about 0.09 x the font size (28 pt -> 2.5, 60 pt -> 5.4)

Motion is the M_UI_SandText material (Reveal, Shiver, Sweep, State.A) driven by a self-stopping 60 Hz timer, so an
idle line costs nothing on the CPU. The retainer keeps render opacity 1 (editor rule); fades go through the material.
Steps (idempotent; PIE off):  python Tools/Unreal/ui/textfx/sandline_build.py widget | graphs"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, entry_of, is_empty, ok, save  # noqa: E402

DIR = '/Game/FoA/UI/Widgets/Common'
WBP = f'{DIR}/WBP_SandLine'
WBPC = f'{WBP}.WBP_SandLine_C'
MI = '/Game/FoA/UI/Materials/MI_UI_SandText_HUD.MI_UI_SandText_HUD'
FONT = '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
KML, KSL = '/Script/Engine.KismetMathLibrary', '/Script/Engine.KismetSystemLibrary'
TB, W, RB = '/Script/UMG.TextBlock', '/Script/UMG.Widget', '/Script/UMG.RetainerBox'
MID = '/Script/Engine.MaterialInstanceDynamic'
STEP = sys.argv[1] if len(sys.argv) > 1 else ''
DT = 0.0167
VARS = [('T', 'real', '0.0'), ('OutT', 'real', '0.0'), ('FormSpan', 'real', '0.8'), ('ShiverAmt', 'real', '0.0'),
        ('SweepOn', 'real', '0.0'), ('SweepAt', 'real', '0.7'), ('bLeaving', 'bool', 'false'), ('Mood', 'int', '0')]


def widget():
    if not hc.call('blueprint_get_info', {'path': WBP}).get('ok'):
        ok(hc.call('ui_create_widget', {'path': DIR, 'name': 'WBP_SandLine'}), 'create')
    if 'Txt_Line' not in str(hc.call('ui_query', {'path': WBP}).get('data')):
        # Overlay padding gives the grains blown in from the left and the echo trailing down room inside the retainer
        ok(hc.call('ui_build_tree', {'widget_blueprint_path': WBP, 'tree': {
            'class': 'RetainerBox', 'name': 'Ret_Line',
            'slot_props': {'anchors_min': [0, 0], 'anchors_max': [1, 1], 'position': [0, 0], 'size': [0, 0]},
            'children': [{'class': 'Overlay', 'name': 'Ovl_Line', 'children': [
                {'class': 'TextBlock', 'name': 'Txt_Line',
                 'slot_props': {'padding': '(Left=24,Top=14,Right=32,Bottom=26)', 'horizontal_alignment': 'HAlign_Fill',
                                'vertical_alignment': 'VAlign_Center'},
                 'properties': {'Text': '', 'AutoWrapText': True,  # level1 2026-11-18: no placeholder (an unplayed line showed it on the T10 threshold)
                                'Font': {'FontObject': FONT, 'TypefaceFontName': 'SemiBold', 'Size': 28},
                                'ColorAndOpacity': {'SpecifiedColor': [1, 1, 1, 1]}}}]}]}}), 'tree')
        for w in ('Ret_Line', 'Txt_Line'):
            ok(hc.call('ui_set_variable', {'widget_blueprint_path': WBP, 'widget_name': w, 'is_variable': True}), w)
    ok(hc.call('ui_set_widget_properties', {'widget_blueprint_path': WBP, 'widget_name': 'Ret_Line', 'properties': {
        'EffectMaterial': MI, 'TextureParameter': 'Texture', 'Visibility': 'HitTestInvisible'}}), 'retainer')
    have = {v['name'] for v in hc.call('blueprint_get_info', {'path': WBP})['data'].get('variables', [])}
    for name, typ, val in VARS:
        if name not in have:
            ok(hc.call('blueprint_add_variable', {'path': WBP, 'variable_name': name, 'variable_type': typ,
                                                   'default_value': val, 'category': 'Sand line'}), name)
    if 'Scale' not in have:
        ok(hc.call('blueprint_add_variable', {'path': WBP, 'variable_name': 'Scale', 'variable_type': 'real', 'default_value': '2.5',
                                               'category': 'Sand line', 'instance_editable': True,
                                               'tooltip': 'Grain size in px, about 0.09 x the font size'}), 'Scale')
    funcs = hc.call('blueprint_get_info', {'path': WBP})['data']['functions']
    for name, spec in (('Play', dict(inputs=[{'name': 'Line', 'type': 'text'}, {'name': 'Mood', 'type': 'int'},
                                             {'name': 'Hold', 'type': 'real'}])), ('Dismiss', {}), ('Step', {})):
        if name not in funcs:
            ok(hc.call('blueprint_add_function', {'path': WBP, 'function_name': name, **spec}), name)
    compile_bp(WBP, widget=True)
    print('widget', save(WBP))


def clamp01(b, v):
    return b.fn(f'{KML}:FClamp', Value=v, Min=0.0, Max=1.0)


def div(b, a, d):
    return b.fn(f'{KML}:Divide_DoubleDouble', A=a, B=d)


def graphs():
    ret = ('Ret_Line',)
    if is_empty(WBP, 'Step'):
        e, _, _ = entry_of(WBP, 'Step')
        b = B(WBP, 'Step')
        st = b.set('T', b.fn(f'{KML}:Add_DoubleDouble', A=b.get('T'), B=DT))
        so = b.set('OutT', b.fn(f'{KML}:SelectFloat', A=b.fn(f'{KML}:Add_DoubleDouble', A=b.get('OutT'), B=DT), B=0.0,
                                bPickA=b.get('bLeaving')))
        mid = b.fn(f'{RB}:GetEffectMaterial', self=b.get(*ret))
        t = b.get('T')
        rev = b.fn(f'{KML}:Ease', A=0.0, B=1.0, EasingFunc='EaseOut', BlendExp=4.0, Alpha=clamp01(b, div(b, t, b.get('FormSpan'))))
        shv = b.fn(f'{KML}:Ease', A=b.get('ShiverAmt'), B=0.0, EasingFunc='EaseOut', BlendExp=2.0, Alpha=clamp01(b, div(b, b.get('T'), 0.9)))
        swp = b.fn(f'{KML}:Multiply_DoubleDouble', A=b.get('SweepOn'), B=clamp01(b, div(b, b.fn(
            f'{KML}:Subtract_DoubleDouble', A=b.get('T'), B=b.get('SweepAt')), 0.9)))
        out = b.fn(f'{KML}:Ease', A=0.0, B=1.0, EasingFunc='EaseIn', BlendExp=2.0, Alpha=clamp01(b, div(b, b.get('OutT'), 0.42)))
        p1 = b.fn(f'{MID}:SetScalarParameterValue', self=mid, ParameterName='Reveal', Value=rev)
        p2 = b.fn(f'{MID}:SetScalarParameterValue', self=mid, ParameterName='Shiver', Value=shv)
        p3 = b.fn(f'{MID}:SetScalarParameterValue', self=mid, ParameterName='Sweep', Value=swp)
        p4 = b.fn(f'{MID}:SetVectorParameterValue', self=mid, ParameterName='State',
                  Value=b.fn(f'{KML}:MakeColor', R=0.0, G=0.0, B=0.0, A=out))
        gone = b.node('branch', {'Condition': b.fn(f'{KML}:BooleanAND', A=b.get('bLeaving'),
                                                    B=b.fn(f'{KML}:GreaterEqual_DoubleDouble', A=b.get('OutT'), B=0.45))})
        hide = b.fn(f'{W}:SetVisibility', InVisibility='Collapsed')
        stop1 = b.fn(f'{KSL}:K2_ClearTimer', FunctionName='Step')
        rest = b.node('branch', {'Condition': b.fn(f'{KML}:BooleanAND', A=b.fn(f'{KML}:Not_PreBool', A=b.get('bLeaving')),
                                                    B=b.fn(f'{KML}:GreaterEqual_DoubleDouble', A=b.get('T'), B=1.7))})
        stop2 = b.fn(f'{KSL}:K2_ClearTimer', FunctionName='Step')
        b.chain(e, st, so, p1, p2, p3, p4, gone, hide, stop1)
        b.chain((gone, 'else'), rest, stop2)
        b.run()
    if is_empty(WBP, 'Dismiss'):
        e, _, _ = entry_of(WBP, 'Dismiss')
        b = B(WBP, 'Dismiss')
        up = b.node('branch', {'Condition': b.fn(f'{KML}:BooleanAND', A=b.fn(f'{W}:IsVisible'),
                                                  B=b.fn(f'{KML}:Not_PreBool', A=b.get('bLeaving')))})
        b.chain(e, up, b.set('bLeaving', True), b.set('OutT', 0.0), b.fn(f'{KSL}:K2_ClearTimer', FunctionName='Dismiss'),
                b.fn(f'{KSL}:K2_SetTimer', FunctionName='Step', Time=DT, bLooping=True))
        b.run()
    if is_empty(WBP, 'Play'):
        e, _, _ = entry_of(WBP, 'Play')
        b = B(WBP, 'Play')

        def mood(n):
            return b.fn(f'{KML}:EqualEqual_IntInt', A=(e, 'Mood'), B=n)
        span = b.fn(f'{KML}:SelectFloat', A=0.3, B=b.fn(f'{KML}:SelectFloat', A=0.35, B=0.8, bPickA=mood(3)), bPickA=mood(1))
        sweep_on = b.fn(f'{KML}:BooleanOR', A=mood(1), B=mood(2))
        mid = b.fn(f'{RB}:GetEffectMaterial', self=b.get(*ret))
        b.chain(e,
                b.fn(f'{TB}:SetText', self=b.get('Txt_Line'), InText=(e, 'Line')),
                b.set('Mood', (e, 'Mood')),
                b.set('FormSpan', span),
                b.set('ShiverAmt', b.fn(f'{KML}:SelectFloat', A=1.0, B=0.0, bPickA=mood(1))),
                b.set('SweepOn', b.fn(f'{KML}:SelectFloat', A=1.0, B=0.0, bPickA=sweep_on)),
                b.set('SweepAt', b.fn(f'{KML}:SelectFloat', A=0.12, B=0.7, bPickA=mood(1))),
                b.set('T', 0.0), b.set('OutT', 0.0), b.set('bLeaving', False),
                b.fn(f'{MID}:SetScalarParameterValue', self=mid, ParameterName='Scale', Value=b.get('Scale')),
                b.fn(f'{MID}:SetScalarParameterValue', self=mid, ParameterName='Reveal', Value=0.0),
                b.fn(f'{MID}:SetVectorParameterValue', self=mid, ParameterName='State', Value='(R=0,G=0,B=0,A=0)'),
                b.fn(f'{W}:SetVisibility', InVisibility='HitTestInvisible'),
                b.fn(f'{KSL}:K2_SetTimer', FunctionName='Dismiss', Time=(e, 'Hold'), bLooping=False),  # <= 0 clears it
                b.fn(f'{KSL}:K2_SetTimer', FunctionName='Step', Time=DT, bLooping=True))
        b.run()
    compile_bp(WBP, widget=True)
    print('graphs', save(WBP))


if __name__ == '__main__':
    assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    token = editor_lock.acquire('ui', wait_s=300, ttl=180, areas=[WBP])
    try:
        {'widget': widget, 'graphs': graphs}[STEP]()
    finally:
        if token:
            hc.release('ui', token)
            editor_lock.forget('ui', token)
