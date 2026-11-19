"""Gate template jump inputs with the same controller lock used by movement."""
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import hayba_call as hc
from held_tool_graphs import Batch, inspect

P = '/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'

def main():
    assert not hc.call('editor_get_state', {})['data']['pie_running']
    owner = hc.agent_id()
    lease = hc.lease_acquire(owner, ['asset:' + P], ttl_s=60, wait_s=30)
    try:
        nodes, edges = inspect(P, 'EventGraph')
        graph = dict(nodes=nodes, edges=edges)
        b = Batch(P, 'EventGraph')
        jumps = [n for n in graph['nodes'] if n['title'] == 'Jump']
        assert jumps, 'Keep native Jump and its normal jump limits'
        if any(n['title'] == 'IsMoveInputIgnored' for n in graph['nodes']):
            print('Jump input already respects movement locks'); return
        b.fn('controller', '/Script/Engine.Pawn:GetController', 400, 1100)
        b.fn('locked', '/Script/Engine.Controller:IsMoveInputIgnored', 650, 1100)
        b.link('controller', 'ReturnValue', 'locked', 'self')
        for i, jump in enumerate(jumps):
            gate = 'jump_gate' + str(i)
            b.node(gate, 'branch', 1000, 1100 + i * 220)
            b.link('locked', 'ReturnValue', gate, 'Condition')
            edges = [e for e in graph['edges'] if e['to_node'] == jump['node_id'] and e['to_pin'] == 'execute']
            assert edges
            for edge in edges:
                b.cut(edge['from_node'], edge['from_pin'], jump['node_id'], 'execute')
                b.link(edge['from_node'], edge['from_pin'], gate, 'execute')
            b.link(gate, 'else', jump['node_id'], 'execute')
        b.comment('Respect movement locks', ['controller', 'locked'] + ['jump_gate' + str(i) for i in range(len(jumps))])
        b.run()
        nodes, edges = inspect(P, 'EventGraph')
        after = dict(nodes=nodes, edges=edges)
        for jump in jumps:
            incoming = [e for e in after['edges'] if e['to_node'] == jump['node_id'] and e['to_pin'] == 'execute']
            assert incoming and all(e['from_pin'] == 'else' for e in incoming)
    finally:
        hc.release(owner, lease)

if __name__ == '__main__':
    main()
