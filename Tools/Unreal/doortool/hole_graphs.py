"""Door-tool lane: the emptied screw holes go dark (BP_Door, after hole_component.py).
- DropToolScrew: ToolScrewHoles.AddInstance(disc at the screw's home Y/Z, X = HOLE_X just proud of the plate face,
  axis along the door normal, 0.9 cm across, 0.05 cm thick), in the same call that starts the drop.
- HomeToolScrews: ToolScrewHoles.ClearInstances (new day, every BeginDoorTool).
- RestoreDoorTool: ToolScrewHoles follows the plate's visibility (gone with the plate at PlateOff).
Idempotent per step. Hayba batches, compiled 0/0, saved.
  $env:HAYBA_AGENT_ID='doortool'; python Tools/Unreal/doortool/hole_graphs.py [HOLE_X=-1.20]"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
from hayba_call import call  # noqa: E402
from held_tool_graphs import Batch, inspect, find, K, SC  # noqa: E402

DOOR = '/Game/FoA/Gameplay/BP_Door'
ISM = '/Script/Engine.InstancedStaticMeshComponent:'
args = dict(a.split('=', 1) for a in sys.argv[1:])
HOLE_X = float(args.get('HOLE_X', -1.20))


def graph(g):
    nodes, edges = inspect(DOOR, g)
    return nodes, edges, {n['node_id']: n for n in nodes}


def drop():
    nodes, edges, by = graph('DropToolScrew')
    if any(n['title'] == 'Add Instance' or n['title'] == 'AddInstance' for n in nodes):
        return print('DropToolScrew has the hole')
    timer = [n['node_id'] for n in nodes if n['title'] in ('Set Timer by Function Name', 'K2_SetTimer')]
    assert len(timer) == 1, [n['title'] for n in nodes]
    b = Batch(DOOR, 'DropToolScrew')
    b.get('home', 'ToolScrewSelHome', 1750, 300)
    b.fn('homeparts', K + 'BreakTransform', 2000, 300); b.link('home', 'ToolScrewSelHome', 'homeparts', 'InTransform')
    b.fn('homexyz', K + 'BreakVector', 2250, 300); b.link('homeparts', 'Location', 'homexyz', 'InVec')
    b.fn('at', K + 'MakeVector', 2500, 300, X=HOLE_X); b.link('homexyz', 'Y', 'at', 'Y'); b.link('homexyz', 'Z', 'at', 'Z')
    b.fn('facing', K + 'MakeRotator', 2500, 500, Pitch=90.0)
    b.fn('disc', K + 'MakeTransform', 2750, 300, Scale='0.009,0.009,0.0005')
    b.link('at', 'ReturnValue', 'disc', 'Location'); b.link('facing', 'ReturnValue', 'disc', 'Rotation')
    b.get('holes', 'ToolScrewHoles', 2750, 150)
    b.fn('dark', ISM + 'AddInstance', 3050, 0, bWorldSpace='false')
    b.link('holes', 'ToolScrewHoles', 'dark', 'self'); b.link('disc', 'ReturnValue', 'dark', 'InstanceTransform')
    b.link(timer[0], 'then', 'dark', 'execute')
    b.comment('Darken the empty hole', ['home', 'homeparts', 'homexyz', 'at', 'facing', 'disc', 'holes', 'dark'])
    b.run()


def home():
    nodes, edges, by = graph('HomeToolScrews')
    if any(n['title'] in ('Clear Instances', 'ClearInstances') for n in nodes):
        return print('HomeToolScrews clears the holes')
    stop = [n['node_id'] for n in nodes if n['title'] in ('Clear Timer by Function Name', 'K2_ClearTimer')]
    assert len(stop) == 1, stop
    nxt = [e for e in edges if e['from_node'] == stop[0] and e['from_pin'] == 'then']
    assert len(nxt) == 1, nxt
    b = Batch(DOOR, 'HomeToolScrews')
    b.cut(stop[0], 'then', nxt[0]['to_node'], nxt[0]['to_pin'])
    b.get('holes', 'ToolScrewHoles', 250, -350)
    b.fn('clear', ISM + 'ClearInstances', 400, -200); b.link('holes', 'ToolScrewHoles', 'clear', 'self')
    b.link(stop[0], 'then', 'clear', 'execute'); b.link('clear', 'then', nxt[0]['to_node'], nxt[0]['to_pin'])
    b.run()


def restore():
    nodes, edges, by = graph('RestoreDoorTool')
    if any(n['title'] == 'Get ToolScrewHoles' for n in nodes):
        return print('RestoreDoorTool hides the holes')
    key = [n['node_id'] for n in nodes if n['title'] == 'SetVisibility' and any(
        e['to_node'] == n['node_id'] and e['to_pin'] == 'self' and by[e['from_node']]['title'] == 'Get ToolKeyhole' for e in edges)]
    assert len(key) == 1, key
    show = next(e for e in edges if e['to_node'] == key[0] and e['to_pin'] == 'bNewVisibility')
    nxt = [e for e in edges if e['from_node'] == key[0] and e['from_pin'] == 'then']
    assert len(nxt) == 1, nxt
    b = Batch(DOOR, 'RestoreDoorTool')
    b.cut(key[0], 'then', nxt[0]['to_node'], nxt[0]['to_pin'])
    b.get('holes', 'ToolScrewHoles', 4500, 1500)
    b.fn('vis', SC + 'SetVisibility', 4500, 1200); b.link('holes', 'ToolScrewHoles', 'vis', 'self')
    b.link(show['from_node'], show['from_pin'], 'vis', 'bNewVisibility')
    b.link(key[0], 'then', 'vis', 'execute'); b.link('vis', 'then', nxt[0]['to_node'], nxt[0]['to_pin'])
    b.run()


if __name__ == '__main__':
    assert not call('editor_get_state', {})['data']['pie_running'], 'PIE is running: wait'
    drop()
    home()
    restore()
