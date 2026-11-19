"""Round 3: the HUD objective changes as sand. When a beat brings a new objective and an old one is on screen, the old
line blows away to the right (0.4 s, State.A, ease-in) and the new one then gathers as before (Reveal, 0.8 s). In
place, idempotent, compile and save in one lease:  python Tools/Unreal/ui/textfx/objective_swap.py
  HandleBeatChanged  old text on screen and different -> PendingObjective, bObjSwap, ObjT = -0.4 (scatter first);
                     otherwise SetText and ObjT = 0 exactly as before
  ObjectiveSwap      (new, called by ObjectiveStep after it advances ObjT) State.A from the scatter ramp; on the first
                     tick at ObjT >= 0 it swaps the text in
  ObjectiveStep      Reveal holds at 1 while ObjT < 0, so the old words scatter whole"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, entry_of, graph, is_empty, ok, save  # noqa: E402

HUD = '/Game/FoA/UI/Game/WBP_HUD'
HUDC = HUD + '.WBP_HUD_C'
KML, KSL, KTL = '/Script/Engine.KismetMathLibrary', '/Script/Engine.KismetSystemLibrary', '/Script/Engine.KismetTextLibrary'
KSTR, TB, RB = '/Script/Engine.KismetStringLibrary', '/Script/UMG.TextBlock', '/Script/UMG.RetainerBox'
MID = '/Script/Engine.MaterialInstanceDynamic'
SCATTER = 0.4


def build():
    have = {v['name'] for v in hc.call('blueprint_get_info', {'path': HUD})['data'].get('variables', [])}
    for name, typ, val in (('PendingObjective', 'text', ''), ('bObjSwap', 'bool', 'false')):
        if name not in have:
            ok(hc.call('blueprint_add_variable', {'path': HUD, 'variable_name': name, 'variable_type': typ, 'default_value': val,
                                                   'category': 'HUD|Motion'}), name)
    if 'ObjectiveSwap' not in hc.call('blueprint_get_info', {'path': HUD})['data']['functions']:
        ok(hc.call('blueprint_add_function', {'path': HUD, 'function_name': 'ObjectiveSwap'}), 'fn')
    compile_bp(HUD, widget=True)

    if is_empty(HUD, 'ObjectiveSwap'):
        e, _, _ = entry_of(HUD, 'ObjectiveSwap')
        b = B(HUD, 'ObjectiveSwap')
        mid = b.fn(f'{RB}:GetEffectMaterial', self=b.get('Ret_Objective'))
        has = b.node('branch', {'Condition': b.fn(f'{KSL}:IsValid', Object=mid)})
        out = b.fn(f'{KML}:SelectFloat', B=0.0, bPickA=b.fn(f'{KML}:Less_DoubleDouble', A=b.get('ObjT'), B=0.0),
                   A=b.fn(f'{KML}:Ease', A=0.0, B=1.0, EasingFunc='EaseIn', BlendExp=2.0, Alpha=b.fn(
                       f'{KML}:FClamp', Value=b.fn(f'{KML}:Divide_DoubleDouble', A=b.fn(f'{KML}:Add_DoubleDouble', A=b.get('ObjT'), B=SCATTER),
                                                   B=SCATTER), Min=0.0, Max=1.0)))
        st = b.fn(f'{MID}:SetVectorParameterValue', self=mid, ParameterName='State', Value=b.fn(f'{KML}:MakeColor', R=0.0, G=0.0, B=0.0, A=out))
        due = b.node('branch', {'Condition': b.fn(f'{KML}:BooleanAND', A=b.get('bObjSwap'),
                                                   B=b.fn(f'{KML}:GreaterEqual_DoubleDouble', A=b.get('ObjT'), B=0.0))})
        b.chain(e, has, st, due, b.fn(f'{TB}:SetText', self=b.get('Txt_Objective'), InText=b.get('PendingObjective')),
                b.set('bObjSwap', False))
        b.run()

    nodes, edges = graph(HUD, 'ObjectiveStep')
    by = {n['node_id']: n for n in nodes}
    if not any('ObjectiveSwap' in n['title'].replace(' ', '') for n in nodes):
        set_t = next(n['node_id'] for n in nodes if n['title'].startswith('Set ObjT'))
        nxt = next(x['to_node'] for x in edges if x['from_node'] == set_t and x['from_pin'] == 'then')
        reveal = next(n['node_id'] for n in nodes if n['title'].startswith('SetScalarParameterValue')
                      and any(p['name'] == 'ParameterName' and p.get('default_value') == 'Reveal' for p in n['pins']))
        ease = next(x['from_node'] for x in edges if x['to_node'] == reveal and x['to_pin'] == 'Value')
        b = B(HUD, 'ObjectiveStep')
        b.refs.update({set_t, nxt, reveal, ease})
        swap = b.fn(f'{HUDC}:ObjectiveSwap')
        hold = b.fn(f'{KML}:SelectFloat', A=1.0, B=(ease, 'ReturnValue'), bPickA=b.fn(f'{KML}:Less_DoubleDouble', A=b.get('ObjT'), B=0.0))
        b.ops += [dict(op='disconnect', node_id=set_t, pin_name='then'), dict(op='disconnect', node_id=reveal, pin_name='Value')]
        b.chain(set_t, swap, nxt)
        b.link(hold, 'ReturnValue', reveal, 'Value')
        b.run()

    nodes, edges = graph(HUD, 'HandleBeatChanged')
    if not any(n['title'].startswith('Set PendingObjective') for n in nodes):
        e = next(n['node_id'] for n in nodes if n['title'] == 'HandleBeatChanged')
        settext = next(n['node_id'] for n in nodes if n['title'].startswith('SetText'))
        timer = next(n['node_id'] for n in nodes if n['title'].startswith('Set Timer') and any(
            p['name'] == 'FunctionName' and p.get('default_value') == 'ObjectiveStep' for p in n['pins']))
        b = B(HUD, 'HandleBeatChanged')
        b.refs.update({e, settext, timer})
        old = b.fn(f'{KTL}:Conv_TextToString', InText=b.fn(f'{TB}:GetText', self=b.get('Txt_Objective')))
        new = b.fn(f'{KTL}:Conv_TextToString', InText=(e, 'Objective'))
        swap = b.node('branch', {'Condition': b.fn(f'{KML}:BooleanAND', A=b.fn(f'{KML}:Greater_IntInt', A=b.fn(f'{KSTR}:Len', S=old), B=0),
                                                    B=b.fn(f'{KSTR}:NotEqual_StrStr', A=old, B=new))})
        b.ops.append(dict(op='disconnect', node_id=e, pin_name='then'))
        b.chain(e, swap, b.set('PendingObjective', (e, 'Objective')), b.set('bObjSwap', True), b.set('ObjT', -SCATTER), timer)
        b.link(swap, 'else', settext, 'execute')
        b.run()
    compile_bp(HUD, widget=True)
    print('saved', save(HUD))


if __name__ == '__main__':
    token = editor_lock.acquire('ui', wait_s=900, ttl=180, areas=[HUD])
    try:
        assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
        build()
    finally:
        if token:
            hc.release('ui', token)
            editor_lock.forget('ui', token)
