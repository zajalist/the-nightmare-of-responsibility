"""T10: he stops in the doorway when he walks out (QA plan C, main 2026-11-10). Past the frame there is no floor: behind the
fade and the "Day one." card the pawn free-fell to z -10434 m, and KillZ could destroy him mid-ending.
  CheckWalkedOut: when he is out, before ReportEvent(WalkedOut): StopMovementImmediately, CharacterMovement.DisableMovement
      (MOVE_None: no gravity), SetIgnoreMoveInput(true); bWalkOutHeld marks the input hold.
  ResetHouse: if held, SetIgnoreMoveInput(false), MOVE_Walking, unmark (the wake-up sets walking too; this keeps the
      ignore-move count balanced on every path back to a morning).
Hayba only; idempotent.  python Tools/Unreal/flow/patch_walkout_hold.py"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
GS = '/Script/Engine.GameplayStatics:'
CM = '/Script/Engine.CharacterMovementComponent:'
os.environ['HAYBA_AGENT_ID'] = 'story'


def next_of(es, node, pin='then'):
    hits = [x for x in es if x['from_node'] == node and x['from_pin'] == pin]
    return hits[0] if hits else None


def hold():
    ns, es = inspect(P, 'CheckWalkedOut')
    if any(n['title'] == 'Set bWalkOutHeld' for n in ns):
        return 'kept'
    report = next(n['node_id'] for n in ns if n['title'] == 'ReportEvent')
    before = next(x for x in es if x['to_node'] == report and x['to_pin'] == 'execute')
    b = Batch(P, 'CheckWalkedOut')
    b.cut(before['from_node'], before['from_pin'], report, 'execute')
    b.fn('who', GS + 'GetPlayerCharacter', 600, 500, PlayerIndex=0)
    b.get('move', 'CharacterMovement', 800, 500, '/Script/Engine.Character')
    b.link('who', 'ReturnValue', 'move', 'self')
    b.fn('stop', CM + 'StopMovementImmediately', 900, 300)
    b.link('move', 'CharacterMovement', 'stop', 'self')
    b.fn('nofall', CM + 'DisableMovement', 1150, 300)
    b.link('move', 'CharacterMovement', 'nofall', 'self')
    b.fn('pc', GS + 'GetPlayerController', 1150, 600, PlayerIndex=0)
    b.fn('noinput', '/Script/Engine.Controller:SetIgnoreMoveInput', 1400, 300, bNewMoveInput='true')
    b.link('pc', 'ReturnValue', 'noinput', 'self')
    b.set('held', 'bWalkOutHeld', 1650, 300)
    b.pin('held', 'bWalkOutHeld', 'true')
    b.link(before['from_node'], before['from_pin'], 'stop', 'execute')
    b.chain('stop', 'nofall', 'noinput', 'held')
    b.link('held', 'then', report, 'execute')
    b.comment('He stops in the doorway (no floor past it)', ['who', 'move', 'stop', 'nofall', 'pc', 'noinput', 'held'])
    b.run()
    return 'held before WalkedOut'


def release():
    ns, es = inspect(P, 'ResetHouse')
    if any(n['title'] == 'Set bWalkOutHeld' for n in ns):
        return 'kept'
    anchor = next(n['node_id'] for n in ns if n['title'] == 'Clear Timer by Function Name'
                  and any(p['name'] == 'FunctionName' and p.get('default_value') == 'CheckWalkedOut' for p in n['pins']))
    after = next_of(es, anchor)
    b = Batch(P, 'ResetHouse')
    b.get('was', 'bWalkOutHeld', 1500, 450)
    b.node('heldnow', 'branch', 1550, 300)
    b.link('was', 'bWalkOutHeld', 'heldnow', 'Condition')
    b.fn('pc', GS + 'GetPlayerController', 1600, 600, PlayerIndex=0)
    b.fn('input', '/Script/Engine.Controller:SetIgnoreMoveInput', 1650, 300, bNewMoveInput='false')
    b.link('pc', 'ReturnValue', 'input', 'self')
    b.fn('who', GS + 'GetPlayerCharacter', 1700, 600, PlayerIndex=0)
    b.get('move', 'CharacterMovement', 1800, 600, '/Script/Engine.Character')
    b.link('who', 'ReturnValue', 'move', 'self')
    b.fn('walk', CM + 'SetMovementMode', 1800, 300, NewMovementMode='MOVE_Walking')
    b.link('move', 'CharacterMovement', 'walk', 'self')
    b.set('free', 'bWalkOutHeld', 1950, 300)
    b.pin('free', 'bWalkOutHeld', 'false')
    b.cut(anchor, 'then', after['to_node'], after['to_pin'])
    b.link(anchor, 'then', 'heldnow', 'execute')
    b.link('heldnow', 'then', 'input', 'execute')
    b.chain('input', 'walk', 'free')
    b.link('free', 'then', after['to_node'], after['to_pin'])
    b.link('heldnow', 'else', after['to_node'], after['to_pin'])
    b.comment('Walking again next morning', ['was', 'heldnow', 'pc', 'input', 'who', 'move', 'walk', 'free'])
    b.run()
    return 'released in ResetHouse'


assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + P], ttl_s=180, wait_s=240)
try:
    r = h.call('blueprint_add_variable', dict(path=P, variable_name='bWalkOutHeld', variable_type='bool', category='Story|T10',
                                              update_existing=True), owner='story')
    assert r.get('ok'), r
    report = dict(Hold=hold(), Release=release())
    Path('P:/FoA/Saved/StoryShots/walkout_hold_patch.json').write_text(json.dumps(report, indent=1))
    print('walkout hold', report)
finally:
    h.release('story', token)
