"""The ending's real bedroom is the room as the game began (main, 2026-11-19, the user's request): the door closed in
its own frame and the wardrobe standing where it stood before it fell.
BP_DreamThreshold.RestoreWakeRoom: the director's ResetWardrobeTransition (door shown, old-doorway wall and wardrobe
blockers off) and RestoreDoor (frame and door back home), then ResetForNewDay on the Door and the Wardrobe (morning
state and pose, instant). EndingColour calls it first, under the black fade, before the player is placed.
Idempotent: skips what is already there. One lease, Hayba graph batches, compiled and saved.
  python -B Tools/Unreal/level2/patch_wake_room.py"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
os.environ.update(FOA_AGENT='main', HAYBA_AGENT_ID='main')
import editor_lock  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402
from hayba_call import call  # noqa: E402

BP = '/Game/FoA/Level2/Transition/BP_DreamThreshold'
DIR = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
BPI = '/Game/FoA/Gameplay/BPI_Interactable.BPI_Interactable_C'
FN = 'RestoreWakeRoom'


def body():
    nodes, _ = inspect(BP, FN)
    if len(nodes) > 1:
        return 'body kept'
    entry = find(nodes, FN)
    b = Batch(BP, FN)
    b.get('story', 'Story', 0, 220)
    b.fn('valid', '/Script/Engine.KismetSystemLibrary:IsValid', 220, 220)
    b.node('br', 'branch', 450, 0)
    b.fn('wardrobe_fx', DIR + ':ResetWardrobeTransition', 700, 0)
    b.fn('door_home', DIR + ':RestoreDoor', 1000, 0)
    b.get('door', 'Door', 1000, 260, cls=DIR)
    b.node('door_reset', 'message', 1300, 0, function_name='ResetForNewDay', class_path=BPI)
    b.get('wardrobe', 'Wardrobe', 1300, 260, cls=DIR)
    b.node('wardrobe_reset', 'message', 1600, 0, function_name='ResetForNewDay', class_path=BPI)
    b.link('story', 'Story', 'valid', 'Object')
    b.link('valid', 'ReturnValue', 'br', 'Condition')
    for ref in ('wardrobe_fx', 'door_home', 'door', 'wardrobe'):
        b.link('story', 'Story', ref, 'self')
    b.link('door', 'Door', 'door_reset', 'self')
    b.link('wardrobe', 'Wardrobe', 'wardrobe_reset', 'self')
    b.chain(entry, 'br', 'wardrobe_fx', 'door_home', 'door_reset', 'wardrobe_reset')
    b.comment('Room as the game began', ['story', 'valid', 'br', 'wardrobe_fx', 'door_home', 'door', 'door_reset',
                                         'wardrobe', 'wardrobe_reset'])
    b.run()
    return 'body built'


def door_closed():
    """The door's morning state (Locked) has no pose (Poses holds only Open), so ResetForNewDay leaves the pivot swung:
    put the pivot back to its closed identity transform after the reset."""
    nodes, edges = inspect(BP, FN)
    if any(n['title'].startswith('Cast To BP_Interactable') for n in nodes):
        return 'door pivot kept'
    resets = [n['node_id'] for n in nodes if n['title'].replace('\n', ' ').startswith('ResetForNewDay')]
    last = [r for r in resets if not any(e['from_node'] == r and e['from_pin'] == 'then' for e in edges)]
    door = [n['node_id'] for n in nodes if n['title'] == 'Get Door']
    assert len(last) == 1 and len(door) == 1, (resets, last, door)
    b = Batch(BP, FN)
    b.node('cast', 'cast', 1900, 0, class_path='/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C')
    b.get('pivot', 'Pivot', 2150, 260, cls='/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C')
    b.fn('shut', '/Script/Engine.SceneComponent:K2_SetRelativeTransform', 2400, 0, bTeleport='true')
    b.fn('closed', '/Script/Engine.KismetMathLibrary:MakeTransform', 2150, 420)  # identity: the closed pose
    b.link('closed', 'ReturnValue', 'shut', 'NewTransform')
    b.link(door[0], 'Door', 'cast', 'Object')
    b.link('cast', 'AsBP Interactable', 'pivot', 'self')
    b.link('pivot', 'Pivot', 'shut', 'self')
    b.chain(last[0], 'cast', 'shut')
    b.run()
    return 'door pivot built'


def caller():
    nodes, edges = inspect(BP, 'EndingColour')
    if any(n['title'] == FN for n in nodes):
        return 'call kept'
    entry = find(nodes, 'EndingColour')
    first = [e for e in edges if e['from_node'] == entry and e['from_pin'] == 'then']
    assert len(first) == 1, first
    b = Batch(BP, 'EndingColour')
    b.cut(entry, 'then', first[0]['to_node'], first[0]['to_pin'])
    b.fn('room', BP + '.BP_DreamThreshold_C:' + FN, 150, -260)
    b.link(entry, 'then', 'room', 'execute')
    b.link('room', 'then', first[0]['to_node'], first[0]['to_pin'])
    b.run()
    return 'call inserted'


if __name__ == '__main__':
    token = editor_lock.acquire('main', wait_s=600, ttl=180, areas=[BP])
    os.environ['FOA_LEASE'] = token or editor_lock.hayba_leases('main')[0][0]
    try:
        assert not call('editor_get_state')['data']['pie_running'], 'PIE is running: no graph edits now'
        if not call('blueprint_inspect_graph', dict(path=BP, graph_name=FN)).get('ok'):
            print('add', call('blueprint_add_function', dict(path=BP, function_name=FN)).get('ok'))
        print(body())
        print(door_closed())
        print(caller())
        print('dirty', call('editor_get_state')['data']['dirty_packages'])
    finally:
        editor_lock.release('main')
