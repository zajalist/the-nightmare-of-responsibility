"""Round 3: the Settings Quality row previews the preset live. Changing Quality lifts the dark scrim (Img_Scrim render
opacity 1 -> 0.25 in 0.2 s) for 2 s so the room behind (the menu camera's bedroom, or the frozen game under Pause)
shows the new level, then the scrim settles back over 0.35 s. Driven from the screen's own Tick (it runs while the
game is paused; world timers do not). In place, idempotent, compile and save in one lease:
  python Tools/Unreal/ui/textfx/settings_preview.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, entry_of, graph, is_empty, ok, save  # noqa: E402

P = '/Game/FoA/UI/Widgets/Menus/WBP_Settings'
PC_ = P + '.WBP_Settings_C'
KML, W = '/Script/Engine.KismetMathLibrary', '/Script/UMG.Widget'
HOLD, IN, OUT = 2.0, 0.2, 0.35


def build():
    if 'PreviewT' not in {v['name'] for v in hc.call('blueprint_get_info', {'path': P})['data'].get('variables', [])}:
        ok(hc.call('blueprint_add_variable', {'path': P, 'variable_name': 'PreviewT', 'variable_type': 'real', 'default_value': '0.0',
                                               'category': 'Settings|Motion'}), 'var')
    if 'PreviewStep' not in hc.call('blueprint_get_info', {'path': P})['data']['functions']:
        ok(hc.call('blueprint_add_function', {'path': P, 'function_name': 'PreviewStep', 'inputs': [{'name': 'Delta', 'type': 'real'}]}), 'fn')
    compile_bp(P, widget=True)
    if is_empty(P, 'PreviewStep'):
        e, _, _ = entry_of(P, 'PreviewStep')
        b = B(P, 'PreviewStep')
        live = b.node('branch', {'Condition': b.fn(f'{KML}:Greater_DoubleDouble', A=b.get('PreviewT'), B=0.0)})
        left = b.set('PreviewT', b.fn(f'{KML}:FMax', A=b.fn(f'{KML}:Subtract_DoubleDouble', A=b.get('PreviewT'), B=(e, 'Delta')), B=0.0))
        t = b.get('PreviewT')
        # lift: 1 - clamp((HOLD + OUT + IN - t) / IN) in, clamp(t / OUT) out; opacity = lerp(1, 0.25, min of the two)
        lift_in = b.fn(f'{KML}:FClamp', Value=b.fn(f'{KML}:Divide_DoubleDouble', A=b.fn(
            f'{KML}:Subtract_DoubleDouble', A=HOLD + OUT + IN, B=t), B=IN), Min=0.0, Max=1.0)
        lift_out = b.fn(f'{KML}:FClamp', Value=b.fn(f'{KML}:Divide_DoubleDouble', A=b.get('PreviewT'), B=OUT), Min=0.0, Max=1.0)
        lift = b.fn(f'{KML}:Ease', A=0.0, B=1.0, EasingFunc='EaseInOut', BlendExp=2.0, Alpha=b.fn(f'{KML}:FMin', A=lift_in, B=lift_out))
        op = b.fn(f'{W}:SetRenderOpacity', self=b.get('Img_Scrim'), InOpacity=b.fn(f'{KML}:Lerp', A=1.0, B=0.25, Alpha=lift))
        b.chain(e, live, left, op)
        b.run()
    nodes, edges = graph(P, 'EventGraph')
    if not any('PreviewStep' in n['title'].replace(' ', '') for n in nodes):
        tick = next(n['node_id'] for n in nodes if n['title'].startswith('Event Tick'))
        setlast = next(n['node_id'] for n in nodes if n['title'].startswith('Set LastTick'))
        nxt = next(x['to_node'] for x in edges if x['from_node'] == setlast and x['from_pin'] == 'then')
        b = B(P, 'EventGraph')
        b.refs.update({tick, setlast, nxt})
        step = b.fn(f'{PC_}:PreviewStep', Delta=(tick, 'InDeltaTime'))
        b.ops.append(dict(op='disconnect', node_id=setlast, pin_name='then'))
        b.chain(setlast, step, nxt)
        b.run()
    nodes, edges = graph(P, 'OnQualityChanged')
    if not any(n['title'].startswith('Set PreviewT') for n in nodes):
        outs = {(x['from_node'], x['from_pin']) for x in edges}
        tail = next(n['node_id'] for n in nodes if any(p['name'] == 'then' and p['direction'] == 'output' for p in n['pins'])
                    and (n['node_id'], 'then') not in outs)
        b = B(P, 'OnQualityChanged')
        b.refs.add(tail)
        b.chain(tail, b.set('PreviewT', HOLD + OUT + IN))
        b.run()
    compile_bp(P, widget=True)
    print('saved', save(P))


if __name__ == '__main__':
    token = editor_lock.acquire('ui', wait_s=900, ttl=180, areas=[P])
    try:
        assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
        build()
    finally:
        if token:
            hc.release('ui', token)
            editor_lock.forget('ui', token)
