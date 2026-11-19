"""Ship blocker (coordinator 13:20, perf lane's Shipping_20261118_1257): F9 opened "Playtest diagnostics" in Shipping.
Every debug or QA hotkey is now gated where its input arrives, on GetBuildConfiguration() != "Shipping" (pure, so
the cook keeps it; IsPackagedForDistribution did not gate in the perf lane's build), so nothing is created there:
  BP_FoAFrontEnd   F9 ToggleDebugPanel (WBP_Debug), F6 DebugNextStep (Pressed and Released)
  BP_BeatDirector  F10 FailDay (its IsPackagedForDistribution branch now reads the build configuration)
  BP_Encounter     F8 StartEncounter
Found by scanning every Blueprint package for K2Node_InputKey with an F-key name (no others; F7 is not bound).
In place, idempotent, compile and save per asset:  python Tools/Unreal/ui/gate_debug_keys.py"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, graph, save  # noqa: E402

KSL, KSTR = '/Script/Engine.KismetSystemLibrary', '/Script/Engine.KismetStringLibrary'
TARGETS = {'/Game/FoA/UI/Framework/BP_FoAFrontEnd': ('F9', 'F6'),
           '/Game/FoA/Gameplay/Encounter/BP_Encounter': ('F8',),
           '/Game/FoA/Gameplay/BP_BeatDirector': ('F10',)}


def not_shipping(b):
    return b.fn(f'{KSTR}:NotEqual_StrStr', A=b.fn(f'{KSL}:GetBuildConfiguration'), B='Shipping')


def gate(path, keys):
    nodes, edges = graph(path, 'EventGraph')
    by = {n['node_id']: n for n in nodes}
    t = lambda i: by[i]['title'].replace('\n', ' ')  # noqa: E731
    b = B(path, 'EventGraph')
    changed = False
    for key in keys:
        k = next(n['node_id'] for n in nodes if t(n['node_id']) == key and any(p['name'] == 'Pressed' for p in n['pins']))
        for pin in ('Pressed', 'Released'):
            outs = [x for x in edges if x['from_node'] == k and x['from_pin'] == pin]
            for x in outs:
                tgt = x['to_node']
                if t(tgt) == 'Branch':
                    cond = next((y for y in edges if y['to_node'] == tgt and y['to_pin'] == 'Condition'), None)
                    src = t(cond['from_node']) if cond else ''
                    if src.startswith('IsPackagedForDistribution'):  # F10: then = blocked, else = the debug action
                        b.refs.add(tgt)
                        b.ops.append(dict(op='disconnect', node_id=tgt, pin_name='Condition'))
                        ship = b.fn(f'{KSTR}:EqualEqual_StrStr', A=b.fn(f'{KSL}:GetBuildConfiguration'), B='Shipping')
                        b.link(ship, 'ReturnValue', tgt, 'Condition')
                        changed = True
                        continue
                    if src.startswith(('Not Equal', '!=')) or 'NotEqual' in src:
                        continue  # already gated
                b.refs.update({k, tgt})
                br = b.node('branch', {'Condition': not_shipping(b)})
                b.ops.append(dict(op='disconnect', node_id=k, pin_name=pin))
                b.link(k, pin, br, 'execute')
                b.link(br, 'then', tgt, x['to_pin'])
                changed = True
    if changed:
        b.run()
        compile_bp(path)
        print(path.rsplit('/', 1)[1], 'saved', save(path))
    else:
        print(path.rsplit('/', 1)[1], 'already gated')


if __name__ == '__main__':
    for path, keys in TARGETS.items():
        token = editor_lock.acquire('ui', wait_s=900, ttl=150, areas=[path])
        try:
            assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
            gate(path, keys)
        finally:
            if token:
                hc.release('ui', token)
                editor_lock.forget('ui', token)
