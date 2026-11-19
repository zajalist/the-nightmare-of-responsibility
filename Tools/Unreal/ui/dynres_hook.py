"""Dynamic resolution hook (perf lane's request, approved by the coordinator 14:45): a GTX 1060-class card holds 60 fps in
the fight on Low, Medium and High, not Epic. UE 5.9 ignores r.ScreenPercentage while dynamic resolution is on, and no
r.DynamicRes.* cvar is ECVF_Scalability, so the maximum follows the preset from here:
  BPFL_FoASettings.ApplyDynamicResolution(WorldContext)
      SP = GetConsoleVariableFloatValue("sg.ResolutionQuality")   (impure in 5.9: it sits on the exec path)
      SP >= 100: r.DynamicRes.OperationMode 0
      else:      r.DynamicRes.MaxScreenPercentage SP, then r.DynamicRes.OperationMode 2
Called at the end of LoadAndApplySettings (boot: after LoadSettings, the first-run auto-detect and ApplySettings) and
of WBP_Settings OnQualityChanged and OnResScaleChanged (the two settings that move sg.ResolutionQuality). The fixed
min and frame budget are the perf lane's, in DefaultEngine.ini. In place, idempotent, compile and save per asset:
  python Tools/Unreal/ui/dynres_hook.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, entry_of, graph, is_empty, ok, save  # noqa: E402

LIB = '/Game/FoA/UI/Framework/BPFL_FoASettings'
LIB_C = LIB + '.BPFL_FoASettings_C'
SET = '/Game/FoA/UI/Widgets/Menus/WBP_Settings'
KML, KSL, KSTR = '/Script/Engine.KismetMathLibrary', '/Script/Engine.KismetSystemLibrary', '/Script/Engine.KismetStringLibrary'


def library():
    if 'ApplyDynamicResolution' not in hc.call('blueprint_get_info', {'path': LIB})['data']['functions']:
        ok(hc.call('blueprint_add_function', {'path': LIB, 'function_name': 'ApplyDynamicResolution'}), 'fn')
        compile_bp(LIB)
    if is_empty(LIB, 'ApplyDynamicResolution'):
        e, nodes, _ = entry_of(LIB, 'ApplyDynamicResolution')
        ret = [n['node_id'] for n in nodes if n['title'].startswith('Return')]
        b = B(LIB, 'ApplyDynamicResolution')
        sp = b.fn(f'{KSL}:GetConsoleVariableFloatValue', VariableName='sg.ResolutionQuality')
        full = b.node('branch', {'Condition': b.fn(f'{KML}:GreaterEqual_DoubleDouble', A=(sp, 'ReturnValue'), B=100.0)})
        off = b.fn(f'{KSL}:ExecuteConsoleCommand', Command='r.DynamicRes.OperationMode 0')
        cap = b.fn(f'{KSL}:ExecuteConsoleCommand', Command=b.fn(f'{KSTR}:Concat_StrStr', A='r.DynamicRes.MaxScreenPercentage ',
                                                                   B=b.fn(f'{KSTR}:Conv_DoubleToString', InDouble=(sp, 'ReturnValue'))))
        on = b.fn(f'{KSL}:ExecuteConsoleCommand', Command='r.DynamicRes.OperationMode 2')
        b.chain(e, sp, full, off)
        b.chain((full, 'else'), cap, on)
        if ret:
            b.refs.add(ret[0])
            b.link(off, 'then', ret[0], 'execute')
            b.link(on, 'then', ret[0], 'execute')
        b.run()
    compile_bp(LIB)
    nodes, edges = graph(LIB, 'LoadAndApplySettings')
    if not any('ApplyDynamicResolution' in n['title'].replace(' ', '') for n in nodes):
        ret = next(n['node_id'] for n in nodes if n['title'].startswith('Return'))
        prev = next(x['from_node'] for x in edges if x['to_node'] == ret and x['to_pin'] == 'execute')
        b = B(LIB, 'LoadAndApplySettings')
        b.refs.update({ret, prev})
        b.ops.append(dict(op='disconnect', node_id=prev, pin_name='then'))
        b.chain(prev, b.fn(f'{LIB_C}:ApplyDynamicResolution'), ret)
        b.run()
    compile_bp(LIB)
    print('library', save(LIB))


def settings():
    for g in ('OnQualityChanged', 'OnResScaleChanged'):
        nodes, edges = graph(SET, g)
        if any('ApplyDynamicResolution' in n['title'].replace(' ', '') for n in nodes):
            continue
        outs = {(x['from_node'], x['from_pin']) for x in edges}
        tails = [n['node_id'] for n in nodes if any(p['name'] == 'then' and p['direction'] == 'output' for p in n['pins'])
                 and (n['node_id'], 'then') not in outs and not n['title'].startswith('Branch')]
        assert len(tails) == 1, (g, tails)
        b = B(SET, g)
        b.refs.add(tails[0])
        b.chain(tails[0], b.fn(f'{LIB_C}:ApplyDynamicResolution'))
        b.run()
    compile_bp(SET, widget=True)
    print('settings', save(SET))


if __name__ == '__main__':
    for path, step in ((LIB, library), (SET, settings)):
        token = editor_lock.acquire('ui', wait_s=900, ttl=150, areas=[path])
        try:
            assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
            step()
        finally:
            if token:
                hc.release('ui', token)
                editor_lock.forget('ui', token)
