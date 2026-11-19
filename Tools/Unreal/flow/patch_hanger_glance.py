"""The dropped hanger gets a glance (user playtest 2026-11-10: "i cant find the hangar which i need to grab that shirt";
the line alone was not enough, they chose "the camera glancing at it"). When SayHangerFell fires (0.6 s after the
T7 top-down hands him back, only if the fall knocked the hanger down and it still lies there, once per drop) his view
eases down onto the hanger's visible top, holds while the line plays, and eases back to where he was looking.
  StartHangerGlance: from = control rotation; to = look-at from the camera to the hanger's bounds top, pitch clamped to
      the camera manager's ViewPitchMin/Max; input held (move and look); TickHangerGlance at 60 Hz.
  TickHangerGlance: weight = ease(t/0.6) - ease((t-1.4)/0.6) (0.6 s in, 0.8 s hold, 0.6 s back), control rotation =
      RLerp(from, to, weight); at 2.0 s EndHangerGlance. The first-person view already follows the control rotation
      (ClearClothingHanger and WakeUpDone face him the same way), so it is a smooth turn of his head, never a cut.
  EndHangerGlance: if glancing: stop the tick, input back, unmark. ResetHouse calls it too, so a Restart Day in the
      middle of the 2 s never leaves input held.
  SayHangerFell: StartHangerGlance right after the once-per-drop mark, before the line.
Not through BP_FoAPlayer's InteractLook: that path only runs inside the interaction lock (capsule turn, EndInteraction)
and has no way back, so the glance drives the same control rotation it hands off to, with the same clamp source.
Hayba only; idempotent.  python Tools/Unreal/flow/patch_hanger_glance.py"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal/flow']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
C = P + '.BP_BeatDirector_C'
GS, KS, K = '/Script/Engine.GameplayStatics:', '/Script/Engine.KismetSystemLibrary:', '/Script/Engine.KismetMathLibrary:'
CTRL, CAM = '/Script/Engine.Controller:', '/Script/Engine.PlayerCameraManager'
IN_S, HOLD_S, OUT_S = 0.6, 0.8, 0.6
os.environ['HAYBA_AGENT_ID'] = 'story'


def call(name, **args):
    r = h.call(name, args, owner='story', timeout=60)
    assert r.get('ok'), r
    return r.get('data', {})


def next_of(es, node, pin='then'):
    hits = [x for x in es if x['from_node'] == node and x['from_pin'] == pin]
    return hits[0] if hits else None


def start():
    ns, _ = inspect(P, 'StartHangerGlance')
    if any(n['title'] == 'K2_SetTimer' or n['title'] == 'Set Timer by Function Name' for n in ns):
        return 'kept'
    e = find(ns, 'StartHangerGlance')
    b = Batch(P, 'StartHangerGlance')
    b.fn('pc', GS + 'GetPlayerController', 0, 300, PlayerIndex=0)
    b.fn('was', CTRL + 'GetControlRotation', 250, 300)
    b.link('pc', 'ReturnValue', 'was', 'self')
    b.set('from', 'HangerGlanceFrom', 300, 0)
    b.link('was', 'ReturnValue', 'from', 'HangerGlanceFrom')
    b.fn('cm', GS + 'GetPlayerCameraManager', 0, 500, PlayerIndex=0)
    b.fn('eye', CAM + ':GetCameraLocation', 250, 500)
    b.link('cm', 'ReturnValue', 'eye', 'self')
    b.get('hanger', 'DroppedHanger', 0, 700)
    b.fn('bounds', '/Script/Engine.Actor:GetActorBounds', 250, 700, bOnlyCollidingComponents='false')
    b.link('hanger', 'DroppedHanger', 'bounds', 'self')
    b.fn('ext', K + 'BreakVector', 500, 800)
    b.link('bounds', 'BoxExtent', 'ext', 'InVec')
    b.fn('up', K + 'MakeVector', 700, 800, X=0.0, Y=0.0)
    b.link('ext', 'Z', 'up', 'Z')
    b.fn('top', K + 'Add_VectorVector', 900, 700)  # its visible top, not the middle of the wire
    b.link('bounds', 'Origin', 'top', 'A')
    b.link('up', 'ReturnValue', 'top', 'B')
    b.fn('aim', K + 'FindLookAtRotation', 1100, 500)
    b.link('eye', 'ReturnValue', 'aim', 'Start')
    b.link('top', 'ReturnValue', 'aim', 'Target')
    b.fn('parts', K + 'BreakRotator', 1300, 500)
    b.link('aim', 'ReturnValue', 'parts', 'InRot')
    b.get('lo', 'ViewPitchMin', 1300, 700, CAM)
    b.link('cm', 'ReturnValue', 'lo', 'self')
    b.get('hi', 'ViewPitchMax', 1300, 850, CAM)
    b.link('cm', 'ReturnValue', 'hi', 'self')
    b.fn('pitch', K + 'FClamp', 1550, 600)
    b.link('parts', 'Pitch', 'pitch', 'Value')
    b.link('lo', 'ViewPitchMin', 'pitch', 'Min')
    b.link('hi', 'ViewPitchMax', 'pitch', 'Max')
    b.fn('to', K + 'MakeRotator', 1750, 500, Roll=0.0)
    b.link('pitch', 'ReturnValue', 'to', 'Pitch')
    b.link('parts', 'Yaw', 'to', 'Yaw')
    b.set('keepto', 'HangerGlanceTo', 1950, 0)
    b.link('to', 'ReturnValue', 'keepto', 'HangerGlanceTo')
    b.fn('now', GS + 'GetTimeSeconds', 2000, 300)
    b.set('t0', 'HangerGlanceStart', 2200, 0)
    b.link('now', 'ReturnValue', 't0', 'HangerGlanceStart')
    b.set('mark', 'bHangerGlancing', 2450, 0)
    b.pin('mark', 'bHangerGlancing', 'true')
    b.fn('nomove', CTRL + 'SetIgnoreMoveInput', 2700, 0, bNewMoveInput='true')
    b.link('pc', 'ReturnValue', 'nomove', 'self')
    b.fn('nolook', CTRL + 'SetIgnoreLookInput', 2950, 0, bNewLookInput='true')
    b.link('pc', 'ReturnValue', 'nolook', 'self')
    b.fn('tick', KS + 'K2_SetTimer', 3200, 0, FunctionName='TickHangerGlance', Time=1.0 / 60, bLooping='true')
    b.link(e, 'then', 'from', 'execute')
    b.chain('from', 'keepto', 't0', 'mark', 'nomove', 'nolook', 'tick')
    b.comment('Glance down at the hanger', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()
    return 'built'


def ease(b, ref, t_ref, offset, span, x, y):
    """eased 0..1 over [offset, offset + span] of the glance clock"""
    b.fn(ref + 'off', K + 'Subtract_DoubleDouble', x, y, B=offset)
    b.link(t_ref, 'ReturnValue', ref + 'off', 'A')
    b.fn(ref + 'frac', K + 'Divide_DoubleDouble', x + 200, y, B=span)
    b.link(ref + 'off', 'ReturnValue', ref + 'frac', 'A')
    b.fn(ref + 'clamp', K + 'FClamp', x + 400, y, Min=0.0, Max=1.0)
    b.link(ref + 'frac', 'ReturnValue', ref + 'clamp', 'Value')
    b.fn(ref, K + 'FInterpEaseInOut', x + 600, y, A=0.0, B=1.0, Exponent=2.0)
    b.link(ref + 'clamp', 'ReturnValue', ref, 'Alpha')


def tick():
    ns, _ = inspect(P, 'TickHangerGlance')
    if any(n['title'] == 'SetControlRotation' for n in ns):
        return 'kept'
    e = find(ns, 'TickHangerGlance')
    b = Batch(P, 'TickHangerGlance')
    b.fn('now', GS + 'GetTimeSeconds', 0, 300)
    b.get('t0', 'HangerGlanceStart', 0, 450)
    b.fn('t', K + 'Subtract_DoubleDouble', 250, 300)
    b.link('now', 'ReturnValue', 't', 'A')
    b.link('t0', 'HangerGlanceStart', 't', 'B')
    ease(b, 'in', 't', 0.0, IN_S, 450, 300)
    ease(b, 'out', 't', IN_S + HOLD_S, OUT_S, 450, 500)
    b.fn('w', K + 'Subtract_DoubleDouble', 1300, 400)
    b.link('in', 'ReturnValue', 'w', 'A')
    b.link('out', 'ReturnValue', 'w', 'B')
    b.get('from', 'HangerGlanceFrom', 1300, 600)
    b.get('to', 'HangerGlanceTo', 1300, 750)
    b.fn('rot', K + 'RLerp', 1550, 500, bShortestPath='true')
    b.link('from', 'HangerGlanceFrom', 'rot', 'A')
    b.link('to', 'HangerGlanceTo', 'rot', 'B')
    b.link('w', 'ReturnValue', 'rot', 'Alpha')
    b.fn('pc', GS + 'GetPlayerController', 1550, 250, PlayerIndex=0)
    b.fn('face', CTRL + 'SetControlRotation', 1800, 0)
    b.link('pc', 'ReturnValue', 'face', 'self')
    b.link('rot', 'ReturnValue', 'face', 'NewRotation')
    b.fn('over', K + 'GreaterEqual_DoubleDouble', 1800, 300, B=IN_S + HOLD_S + OUT_S)
    b.link('t', 'ReturnValue', 'over', 'A')
    b.node('done', 'branch', 2050, 0)
    b.link('over', 'ReturnValue', 'done', 'Condition')
    b.fn('end', C + ':EndHangerGlance', 2300, 0)
    b.link(e, 'then', 'face', 'execute')
    b.chain('face', 'done')
    b.link('done', 'then', 'end', 'execute')
    b.comment('In, hold, back', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()
    return 'built'


def end():
    ns, _ = inspect(P, 'EndHangerGlance')
    if any(n['title'] == 'SetIgnoreMoveInput' for n in ns):
        return 'kept'
    e = find(ns, 'EndHangerGlance')
    b = Batch(P, 'EndHangerGlance')
    b.get('on', 'bHangerGlancing', 0, 300)
    b.node('was', 'branch', 250, 0)
    b.link('on', 'bHangerGlancing', 'was', 'Condition')
    b.fn('stop', KS + 'K2_ClearTimer', 500, 0, FunctionName='TickHangerGlance')
    b.fn('pc', GS + 'GetPlayerController', 700, 300, PlayerIndex=0)
    b.fn('move', CTRL + 'SetIgnoreMoveInput', 800, 0, bNewMoveInput='false')
    b.link('pc', 'ReturnValue', 'move', 'self')
    b.fn('look', CTRL + 'SetIgnoreLookInput', 1100, 0, bNewLookInput='false')
    b.link('pc', 'ReturnValue', 'look', 'self')
    b.set('unmark', 'bHangerGlancing', 1400, 0)
    b.pin('unmark', 'bHangerGlancing', 'false')
    b.link(e, 'then', 'was', 'execute')
    b.link('was', 'then', 'stop', 'execute')
    b.chain('stop', 'move', 'look', 'unmark')
    b.comment('Hand the view back', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()
    return 'built'


def hook_say():
    ns, es = inspect(P, 'SayHangerFell')
    if any(n['title'] == 'StartHangerGlance' for n in ns):
        return 'kept'
    mark = find(ns, 'Set bHangerLineSaid')
    after = next_of(es, mark)
    b = Batch(P, 'SayHangerFell')
    b.fn('glance', C + ':StartHangerGlance', 1300, -200)
    b.cut(mark, 'then', after['to_node'], after['to_pin'])
    b.link(mark, 'then', 'glance', 'execute')
    b.link('glance', 'then', after['to_node'], after['to_pin'])
    b.run()
    return 'the glance starts with the line'


def hook_reset():
    ns, es = inspect(P, 'ResetHouse')
    if any(n['title'] == 'EndHangerGlance' for n in ns):
        return 'kept'
    anchor = next(n['node_id'] for n in ns if n['title'] == 'Clear Timer by Function Name'
                  and any(p['name'] == 'FunctionName' and p.get('default_value') == 'PayoffShotCut' for p in n['pins']))
    after = next_of(es, anchor)
    b = Batch(P, 'ResetHouse')
    b.fn('release', C + ':EndHangerGlance', 1350, 150)
    b.cut(anchor, 'then', after['to_node'], after['to_pin'])
    b.link(anchor, 'then', 'release', 'execute')
    b.link('release', 'then', after['to_node'], after['to_pin'])
    b.run()
    return 'ResetHouse ends a glance in progress'


if __name__ == '__main__':
    assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    token = h.lease_acquire('story', ['asset:' + P], ttl_s=300, wait_s=240)
    try:
        for name, t in (('HangerGlanceFrom', 'rotator'), ('HangerGlanceTo', 'rotator'), ('HangerGlanceStart', 'float'),
                        ('bHangerGlancing', 'bool')):
            call('blueprint_add_variable', path=P, variable_name=name, variable_type=t, category='Story|T7 hanger',
                 update_existing=True)
        for fn in ('StartHangerGlance', 'TickHangerGlance', 'EndHangerGlance'):
            if not h.call('blueprint_inspect_graph', {'path': P, 'graph_name': fn}).get('ok'):
                call('blueprint_add_function', path=P, function_name=fn)
        # End first: Tick calls it, then Start (Tick by name only), then the two hooks
        report = dict(End=end(), Tick=tick(), Start=start(), Say=hook_say(), Reset=hook_reset())
        Path('P:/FoA/Saved/StoryShots/hanger_glance_patch.json').write_text(json.dumps(report, indent=1))
        print('hanger glance', report)
    finally:
        h.release('story', token)
