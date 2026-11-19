"""Round 3, phone and rollover (in place, idempotent, compile and save in one lease each):
  python Tools/Unreal/ui/textfx/round3_cards.py phone      WBP_Phone: an opened message types itself out (45 characters
      a second, a self-stopping 30 Hz timer; Reduce Motion shows it whole). OpenMessage's three Level 1 thread
      branches end in TypeStart; the Level 2 path is untouched.
  python Tools/Unreal/ui/textfx/round3_cards.py rollover   WBP_DayRollover: the card breathes while it holds, render
      scale 1 +- 0.012 on a 5 s sine (the direction doc's breathe token), scaled to 0 by Reduce Motion."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, entry_of, graph, is_empty, ok, save  # noqa: E402

PHONE = '/Game/FoA/UI/Game/WBP_Phone'
ROLL = '/Game/FoA/UI/Game/WBP_DayRollover'
KML, KSL, KTL = '/Script/Engine.KismetMathLibrary', '/Script/Engine.KismetSystemLibrary', '/Script/Engine.KismetTextLibrary'
KSTR, TB, W = '/Script/Engine.KismetStringLibrary', '/Script/UMG.TextBlock', '/Script/UMG.Widget'
MPC, KMAT = '/Game/FoA/UI/Style/MPC_UI.MPC_UI', '/Script/Engine.KismetMaterialLibrary'
STEP = sys.argv[1] if len(sys.argv) > 1 else ''
DT = 0.033


def reduce_motion(b):
    return b.fn(f'{KMAT}:GetScalarParameterValue', Collection=MPC, ParameterName='ReduceMotion')


def step_phone():
    have = {v['name'] for v in hc.call('blueprint_get_info', {'path': PHONE})['data'].get('variables', [])}
    for name, typ, val in (('TypeFull', 'string', ''), ('TypeT', 'real', '0.0')):
        if name not in have:
            ok(hc.call('blueprint_add_variable', {'path': PHONE, 'variable_name': name, 'variable_type': typ, 'default_value': val,
                                                   'category': 'Phone|Motion'}), name)
    funcs = hc.call('blueprint_get_info', {'path': PHONE})['data']['functions']
    for f in ('TypeStart', 'TypeStep'):
        if f not in funcs:
            ok(hc.call('blueprint_add_function', {'path': PHONE, 'function_name': f}), f)
    compile_bp(PHONE, widget=True)
    if is_empty(PHONE, 'TypeStep'):
        e, _, _ = entry_of(PHONE, 'TypeStep')
        b = B(PHONE, 'TypeStep')
        st = b.set('TypeT', b.fn(f'{KML}:Add_DoubleDouble', A=b.get('TypeT'), B=DT))
        full = b.fn(f'{KSTR}:Len', S=b.get('TypeFull'))
        n = b.fn(f'{KML}:SelectInt', A=full, B=b.fn(f'{KML}:FTrunc', A=b.fn(f'{KML}:Multiply_DoubleDouble', A=b.get('TypeT'), B=45.0)),
                 bPickA=b.fn(f'{KML}:Greater_DoubleDouble', A=reduce_motion(b), B=0.5))
        show = b.fn(f'{TB}:SetText', self=b.get('Txt_Message'), InText=b.fn(f'{KTL}:Conv_StringToText', InString=b.fn(
            f'{KSTR}:Left', SourceString=b.get('TypeFull'), Count=n)))
        done = b.node('branch', {'Condition': b.fn(f'{KML}:GreaterEqual_IntInt', A=n, B=full)})
        b.chain(e, st, show, done, b.fn(f'{KSL}:K2_ClearTimer', FunctionName='TypeStep'))
        b.run()
    if is_empty(PHONE, 'TypeStart'):
        e, _, _ = entry_of(PHONE, 'TypeStart')
        b = B(PHONE, 'TypeStart')
        b.chain(e, b.set('TypeFull', b.fn(f'{KTL}:Conv_TextToString', InText=b.fn(f'{TB}:GetText', self=b.get('Txt_Message')))),
                b.set('TypeT', 0.0), b.fn(f'{TB}:SetText', self=b.get('Txt_Message'), InText=''),
                b.fn(f'{KSL}:K2_SetTimer', FunctionName='TypeStep', Time=DT, bLooping=True))
        b.run()
    nodes, edges = graph(PHONE, 'OpenMessage')
    if not any('TypeStart' in n['title'].replace(' ', '') for n in nodes):
        outs = {(x['from_node'], x['from_pin']) for x in edges}
        thread_sets = {x['to_node'] for x in edges if x['from_pin'] == 'Txt_ThreadName' and x['to_pin'] == 'self'}
        tails = [n['node_id'] for n in nodes if n['node_id'] in thread_sets and (n['node_id'], 'then') not in outs]
        assert len(tails) == 3, tails
        b = B(PHONE, 'OpenMessage')
        b.refs.update(tails)
        for t in tails:
            b.chain(t, b.fn(f'{PHONE}.WBP_Phone_C:TypeStart'))
        b.run()
    compile_bp(PHONE, widget=True)
    print('phone', save(PHONE))


def step_rollover():
    nodes, edges = graph(ROLL, 'StepRollover')
    if any(n['title'].startswith('SetRenderScale') and any(x['to_node'] == n['node_id'] and x['from_pin'] == 'VB_Card' for x in edges)
           for n in nodes):
        print('already breathing')
        return
    outs = {(x['from_node'], x['from_pin']) for x in edges}
    tails = [n['node_id'] for n in nodes if any(p['name'] == 'then' and p['direction'] == 'output' for p in n['pins'])
             and (n['node_id'], 'then') not in outs and not n['title'].startswith('Branch')]
    assert len(tails) == 1, tails
    b = B(ROLL, 'StepRollover')
    b.refs.add(tails[0])
    amp = b.fn(f'{KML}:Multiply_DoubleDouble', A=0.012, B=b.fn(f'{KML}:Subtract_DoubleDouble', A=1.0, B=reduce_motion(b)))
    s = b.fn(f'{KML}:Add_DoubleDouble', A=1.0, B=b.fn(f'{KML}:Multiply_DoubleDouble', A=amp, B=b.fn(
        f'{KML}:Sin', A=b.fn(f'{KML}:Multiply_DoubleDouble', A=b.get('Elapsed'), B=1.2566))))
    b.chain(tails[0], b.fn(f'{W}:SetRenderScale', self=b.get('VB_Card'), Scale=b.fn(f'{KML}:MakeVector2D', X=s, Y=s)))
    b.run()
    compile_bp(ROLL, widget=True)
    print('rollover', save(ROLL))


if __name__ == '__main__':
    target = {'phone': PHONE, 'rollover': ROLL}[STEP]
    token = editor_lock.acquire('ui', wait_s=900, ttl=180, areas=[target])
    try:
        assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
        {'phone': step_phone, 'rollover': step_rollover}[STEP]()
    finally:
        if token:
            hc.release('ui', token)
            editor_lock.forget('ui', token)
