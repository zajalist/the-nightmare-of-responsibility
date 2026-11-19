"""The first item inspect froze the game (the user's playtest, 11-19: finding the key in the boot). The first Open spawned
BP_ItemInspect and gave its ItemMesh (stencil 200, lighting channel 1, custom depth) an item for the first time, so its
render states were built at that moment. Now the front end's BeginPlay, under the splash, spawns the inspect actor hidden
and BP_ItemInspect.Prewarm sets each inspectable mesh on ItemMesh once (the engine precaches its pipeline states), then
clears it. RequestInspect finds the actor and reuses it. Idempotent, one lease, compiled and saved.
  python -B Tools/Unreal/ui/patch_inspect_prewarm.py"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
os.environ.update(FOA_AGENT='main', HAYBA_AGENT_ID='main')
import editor_lock  # noqa: E402
from hayba_call import call  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

BP = '/Game/FoA/UI/Game/BP_ItemInspect'
BPC = BP + '.BP_ItemInspect_C'
FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
SM = '/Script/Engine.StaticMeshComponent:SetStaticMesh'
MESHES = ('/Game/FoA/Lux3D/door_key/SM_Lux3D_DoorKey.SM_Lux3D_DoorKey',
          '/Game/FoA/Props/screwdriver/screwdriver_1k/StaticMeshes/screwdriver_1k.screwdriver_1k',
          '/Game/FoA/Lux3D/wire_hanger/SM_Lux3D_WireHanger.SM_Lux3D_WireHanger',
          '/Game/FoA/Lux3D/the_shirt_enemy/SM_Lux3D_ShirtEnemy.SM_Lux3D_ShirtEnemy',
          '/Game/FoA/Level2/Journey/Paper/SM_L2CVPaper/StaticMeshes/SM_L2CVPaper.SM_L2CVPaper')


def prewarm():
    if not call('blueprint_inspect_graph', dict(path=BP, graph_name='Prewarm')).get('ok'):
        call('blueprint_add_function', dict(path=BP, function_name='Prewarm'))
    nodes, _ = inspect(BP, 'Prewarm')
    if len(nodes) > 1:
        return 'prewarm kept'
    b = Batch(BP, 'Prewarm')
    b.fn('hide', '/Script/Engine.Actor:SetActorHiddenInGame', 250, 0, bNewHidden='true')
    chain = ['hide']
    for i, mesh in enumerate(MESHES + ('',)):
        ref = f'm{i}'
        b.fn(ref, SM, 500 + i * 280, 0)
        if mesh:
            b.pin(ref, 'NewMesh', mesh)
        b.get(f'c{i}', 'ItemMesh', 500 + i * 280, 220)
        b.link(f'c{i}', 'ItemMesh', ref, 'self')
        chain.append(ref)
    b.chain(find(nodes, 'Prewarm'), *chain)
    b.comment('Prepare every inspect mesh', chain + [f'c{i}' for i in range(len(MESHES) + 1)])
    b.run()
    return 'prewarm built'


def caller():
    nodes, edges = inspect(FE, 'EventGraph')
    if any(n['title'].startswith('Prewarm') for n in nodes):
        return 'caller kept'
    begin = next(n['node_id'] for n in nodes if n['title'].startswith('Event BeginPlay'))
    first = [e for e in edges if e['from_node'] == begin and e['from_pin'] == 'then']
    assert len(first) == 1, first
    x = next(n for n in nodes if n['node_id'] == begin)
    b = Batch(FE, 'EventGraph')
    b.cut(begin, 'then', first[0]['to_node'], first[0]['to_pin'])
    b.fn('xf', '/Script/Engine.KismetMathLibrary:MakeTransform', 0, 0)
    b.node('spawn', 'spawn_actor_from_class', 0, 0)
    b.pin('spawn', 'Class', BPC)
    b.link('xf', 'ReturnValue', 'spawn', 'SpawnTransform')
    b.fn('warm', BPC + ':Prewarm', 0, 0)
    b.link('spawn', 'ReturnValue', 'warm', 'self')
    b.link(begin, 'then', 'spawn', 'execute')
    b.chain('spawn', 'warm')
    b.link('warm', 'then', first[0]['to_node'], first[0]['to_pin'])
    b.comment('Prepare the item inspect', ['xf', 'spawn', 'warm'])
    b.run()
    return 'caller inserted'


if __name__ == '__main__':
    token = editor_lock.acquire('main', wait_s=600, ttl=240, areas=[BP, FE])
    os.environ['FOA_LEASE'] = token or editor_lock.hayba_leases('main')[0][0]
    try:
        assert not call('editor_get_state')['data']['pie_running'], 'PIE is running'
        print(prewarm())
        print(caller())
        print('dirty', call('editor_get_state')['data']['dirty_packages'])
    finally:
        editor_lock.release('main')
