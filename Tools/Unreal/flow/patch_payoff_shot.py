"""T9 payoff as a sanctioned cinematic shot (QA B3, main 2026-11-09). Before: EndEncounter blended the battle camera into
the first-person head over 1 s (one blurred, headless frame), and the colour reveal played in first person facing the
empty fireplace corner. Now SuitUp cuts straight to a CineCameraActor (PayoffCam) that frames the hero low and
three-quarter (left front, 21 mm, no depth of field) while the suit lands and the colour floods in, holds 2.5 s, then
cuts back to first person under the same 0.2 s black dip as ExitTopDown. Hayba only; idempotent; build_director.py mirrors it.
  SuitUp:        ClearTimer FailDay, PayoffShot, EquipSuit, HideNightmare, PayoffLook(On), timer PayoffShotOut 2.5 s
                 (was: ... PayoffLook(On), timer PayoffDone 3 s).
  PayoffShot:    if the level's CineCameraActor tagged PayoffCam exists (place_payoff_cam.py): move it from the pawn's transform, view cut to it (blend 0, which also cancels EndEncounter's
                 pending 1 s blend to the pawn); PlayerCinematic(true) after the cut, so UpdateFirstPersonVisibility sees
                 a far view target and shows the face, hair and brows; move/look ignored.
  PayoffShotOut: fade to black 0.2 s (held), timer PayoffShotCut 0.2 s.
  PayoffShotCut: view cut to the pawn, PlayerCinematic(false) (face hidden again for first person), move/look back,
                 PayoffDone (colour drains, letterbox out, PayoffEnded), BP_FoAPlayer.HandoffFadeUp (plain 0.5 s fade
                 if the pawn is not the player class).
  ResetHouse:    also clears the PayoffShotOut and PayoffShotCut timers.
  The doubled banner ("You are dressed." over the victory subtitle) lives in WBP_Encounter, which is the UI lane's while
  they edit it: victory_banner() is the exact change, handed to them, and runs only with --banner.
  python Tools/Unreal/flow/patch_payoff_shot.py   (after place_payoff_cam.py)"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
C = P + '.BP_BeatDirector_C'
WBP = '/Game/FoA/Gameplay/Encounter/WBP_Encounter'
PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'
TAG = 'PayoffCam'  # the level's CineCameraActor (place_payoff_cam.py)
GS, KS, K = '/Script/Engine.GameplayStatics:', '/Script/Engine.KismetSystemLibrary:', '/Script/Engine.KismetMathLibrary:'
PCM = '/Script/Engine.PlayerCameraManager:StartCameraFade'
CTRL = '/Script/Engine.Controller:'
BLACK = '(R=0.0,G=0.0,B=0.0,A=1.0)'
HOLD, DIP = 2.5, 0.2
CAM = '(X=155.6,Y=-109.0,Z=-37.0)'  # pawn space: 1.9 m out, 35 deg to the hero's left, 55 cm off the floor
AIM = '(X=0.0,Y=0.0,Z=35.0)'        # look up at the collarbone (capsule centre 92 cm): knees to above the head at 21 mm
SETTLE = 0.5                        # PayoffDone (and so T10's phone) waits for the fade-up: the phone's blend starts in first person
VICTORY = 'You are dressed.'

os.environ['HAYBA_AGENT_ID'] = 'story'


def call(name, **args):
    r = h.call(name, args, owner='story', timeout=60)
    assert r.get('ok'), r
    return r.get('data', {})


def ensure_function(name):
    if not h.call('blueprint_inspect_graph', {'path': P, 'graph_name': name}).get('ok'):
        call('blueprint_add_function', path=P, function_name=name)


def payoff_shot():
    """The camera is the CineCameraActor tagged PayoffCam, placed once in L_Tutorial_Bedroom by place_payoff_cam.py
    (focus off, 21 mm), found by tag; no spawn or make-struct node (Hayba's spawn_actor_from_class asserted,
    EdGraphNode.h:586, 2026-11-09). No such camera: the payoff stays in first person (the dip still runs)."""
    ns, _ = inspect(P, 'PayoffShot')
    if any(n['title'] == 'SetViewTargetWithBlend' for n in ns):
        return 'kept'
    e = find(ns, 'PayoffShot')
    b = Batch(P, 'PayoffShot')
    b.fn('pawn', GS + 'GetPlayerPawn', 0, 400, PlayerIndex=0)
    b.fn('xf', '/Script/Engine.Actor:GetTransform', 250, 400)
    b.link('pawn', 'ReturnValue', 'xf', 'self')
    b.fn('camloc', K + 'TransformLocation', 500, 400, Location=CAM)
    b.link('xf', 'ReturnValue', 'camloc', 'T')
    b.fn('aimloc', K + 'TransformLocation', 500, 600, Location=AIM)
    b.link('xf', 'ReturnValue', 'aimloc', 'T')
    b.fn('rot', K + 'FindLookAtRotation', 800, 500)
    b.link('camloc', 'ReturnValue', 'rot', 'Start')
    b.link('aimloc', 'ReturnValue', 'rot', 'Target')
    b.fn('tagged', GS + 'GetAllActorsWithTag', 200, 0, Tag=TAG)
    b.fn('cam', GS + 'FindNearestActor', 500, 0)
    b.link('tagged', 'OutActors', 'cam', 'ActorsToCheck')
    b.fn('valid', KS + 'IsValid', 700, 200)
    b.link('cam', 'ReturnValue', 'valid', 'Object')
    b.node('have', 'branch', 800, 0)
    b.link('valid', 'ReturnValue', 'have', 'Condition')
    b.fn('place', '/Script/Engine.Actor:K2_SetActorLocationAndRotation', 1100, 0, bSweep='false', bTeleport='true')
    b.link('cam', 'ReturnValue', 'place', 'self')
    b.link('camloc', 'ReturnValue', 'place', 'NewLocation')
    b.link('rot', 'ReturnValue', 'place', 'NewRotation')
    b.fn('pc', GS + 'GetPlayerController', 1100, 400, PlayerIndex=0)
    b.fn('cut', '/Script/Engine.PlayerController:SetViewTargetWithBlend', 1400, 0, BlendTime=0)
    b.link('pc', 'ReturnValue', 'cut', 'self')
    b.link('cam', 'ReturnValue', 'cut', 'NewViewTarget')
    b.fn('cine', C + ':PlayerCinematic', 1700, 0, Enable='true')
    b.fn('nomove', CTRL + 'SetIgnoreMoveInput', 2000, 0, bNewMoveInput='true')
    b.link('pc', 'ReturnValue', 'nomove', 'self')
    b.fn('nolook', CTRL + 'SetIgnoreLookInput', 2300, 0, bNewLookInput='true')
    b.link('pc', 'ReturnValue', 'nolook', 'self')
    b.link(e, 'then', 'tagged', 'execute')
    b.chain('tagged', 'have')  # FindNearestActor is pure
    b.link('have', 'then', 'place', 'execute')
    b.chain('place', 'cut', 'cine', 'nomove', 'nolook')
    b.comment('Cut to the hero', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()
    return 'built'


def payoff_out():
    ns, _ = inspect(P, 'PayoffShotOut')
    if any(n['title'] == 'StartCameraFade' for n in ns):
        return 'kept'
    b = Batch(P, 'PayoffShotOut')
    b.fn('pcm', GS + 'GetPlayerCameraManager', 0, 300, PlayerIndex=0)
    b.fn('down', PCM, 300, 0, FromAlpha=0.0, ToAlpha=1.0, Duration=DIP, Color=BLACK, bHoldWhenFinished='true')
    b.link('pcm', 'ReturnValue', 'down', 'self')
    b.fn('later', KS + 'K2_SetTimer', 650, 0, FunctionName='PayoffShotCut', Time=DIP, bLooping='false')
    b.link(find(ns, 'PayoffShotOut'), 'then', 'down', 'execute')
    b.chain('down', 'later')
    b.comment('Dip out of the hero shot', ['pcm', 'down', 'later'])
    b.run()
    return 'built'


def payoff_cut():
    ns, _ = inspect(P, 'PayoffShotCut')
    if any(n['title'] == 'SetViewTargetWithBlend' for n in ns):
        return 'kept'
    b = Batch(P, 'PayoffShotCut')
    b.fn('pc', GS + 'GetPlayerController', 0, 300, PlayerIndex=0)
    b.fn('pawn', GS + 'GetPlayerPawn', 0, 450, PlayerIndex=0)
    b.fn('cut', '/Script/Engine.PlayerController:SetViewTargetWithBlend', 300, 0, BlendTime=0)
    b.link('pc', 'ReturnValue', 'cut', 'self')
    b.link('pawn', 'ReturnValue', 'cut', 'NewViewTarget')
    b.fn('cine', C + ':PlayerCinematic', 600, 0, Enable='false')
    b.fn('move', CTRL + 'SetIgnoreMoveInput', 900, 0, bNewMoveInput='false')
    b.link('pc', 'ReturnValue', 'move', 'self')
    b.fn('look', CTRL + 'SetIgnoreLookInput', 1200, 0, bNewLookInput='false')
    b.link('pc', 'ReturnValue', 'look', 'self')
    b.fn('done', C + ':PayoffDone', 1500, 0)
    b.node('player', 'cast', 1800, 0, class_path=PLAYER)
    b.link('pawn', 'ReturnValue', 'player', 'Object')
    b.fn('up', PLAYER + ':HandoffFadeUp', 2100, -120)
    b.link('player', 'AsBP Fo APlayer', 'up', 'self')
    b.fn('pcm', GS + 'GetPlayerCameraManager', 2100, 300, PlayerIndex=0)
    b.fn('plain', PCM, 2100, 160, FromAlpha=1.0, ToAlpha=0.0, Duration=0.5, Color=BLACK)
    b.link('pcm', 'ReturnValue', 'plain', 'self')
    b.link(find(ns, 'PayoffShotCut'), 'then', 'cut', 'execute')
    b.chain('cut', 'cine', 'move', 'look', 'done', 'player')
    b.link('player', 'then', 'up', 'execute')
    b.link('player', 'CastFailed', 'plain', 'execute')
    b.comment('Back to first person under black', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()
    return 'built'


def tune():
    """Proof 2026-11-09 (Saved/StoryShots/payoff_shot_strip.jpg): the head touched the top edge, and T10's phone opened in
    the same frame as the cut, so its 0.45 s blend started from the hero shot. Aim higher; PayoffDone after the fade-up."""
    done = []
    ns, _ = inspect(P, 'PayoffShot')
    aims = [n['node_id'] for n in ns if n['title'] == 'TransformLocation'
            and any(p['name'] == 'Location' and (p.get('default_value') or '').replace(' ', '').startswith('0,0,') or
                    p['name'] == 'Location' and 'X=0.0' in (p.get('default_value') or '') for p in n['pins'])]
    if len(aims) == 1:
        b = Batch(P, 'PayoffShot')
        b.pin(aims[0], 'Location', AIM)
        b.run()
        done.append('aim ' + AIM)
    ns, es = inspect(P, 'PayoffShotCut')
    direct = [n['node_id'] for n in ns if n['title'] == 'PayoffDone']
    if direct:
        nid = direct[0]
        before = next(x for x in es if x['to_node'] == nid and x['to_pin'] == 'execute')
        after = next(x for x in es if x['from_node'] == nid and x['from_pin'] == 'then')
        b = Batch(P, 'PayoffShotCut')
        b.ops.append(dict(op='remove', node_ids=[nid]))
        b.fn('later', KS + 'K2_SetTimer', 1500, 0, FunctionName='PayoffDone', Time=SETTLE, bLooping='false')
        b.link(before['from_node'], before['from_pin'], 'later', 'execute')
        b.link('later', 'then', after['to_node'], after['to_pin'])
        b.run()
        done.append('PayoffDone after %.1f s' % SETTLE)
    return done or 'kept'


def suit_up():
    ns, es = inspect(P, 'SuitUp')
    if any(n['title'] == 'PayoffShot' for n in ns):
        return 'kept'
    clear = next(n['node_id'] for n in ns if n['title'] == 'Clear Timer by Function Name')
    equip = find(ns, 'EquipSuit')
    look = find(ns, 'PayoffLook')
    old = next(n['node_id'] for n in ns if n['title'] == 'Set Timer by Function Name'
               and any(p['name'] == 'FunctionName' and p.get('default_value') == 'PayoffDone' for p in n['pins']))
    b = Batch(P, 'SuitUp')
    b.ops.append(dict(op='remove', node_ids=[old]))
    b.cut(clear, 'then', equip, 'execute')
    b.fn('shot', C + ':PayoffShot', 420, -200)
    b.link(clear, 'then', 'shot', 'execute')
    b.link('shot', 'then', equip, 'execute')
    b.fn('out', KS + 'K2_SetTimer', 1440, 0, FunctionName='PayoffShotOut', Time=HOLD, bLooping='false')
    b.link(look, 'then', 'out', 'execute')
    b.comment('Hero shot, then back', ['shot', 'out'])
    b.run()
    return 'built'


def reset_house():
    ns, es = inspect(P, 'ResetHouse')
    names = {p.get('default_value') for n in ns if n['title'] == 'Clear Timer by Function Name' for p in n['pins'] if p['name'] == 'FunctionName'}
    if 'PayoffShotOut' in names:
        return 'kept'
    c3 = next(n['node_id'] for n in ns if n['title'] == 'Clear Timer by Function Name'
              and any(p['name'] == 'FunctionName' and p.get('default_value') == 'PayoffDone' for p in n['pins']))
    after = next(x for x in es if x['from_node'] == c3 and x['from_pin'] == 'then')
    b = Batch(P, 'ResetHouse')
    b.cut(c3, 'then', after['to_node'], after['to_pin'])
    b.fn('c3a', KS + 'K2_ClearTimer', 1184, 220, FunctionName='PayoffShotOut')
    b.fn('c3b', KS + 'K2_ClearTimer', 1344, 220, FunctionName='PayoffShotCut')
    b.link(c3, 'then', 'c3a', 'execute')
    b.chain('c3a', 'c3b')
    b.link('c3b', 'then', after['to_node'], after['to_pin'])
    b.run()
    return 'built'


def victory_banner():
    ns, _ = inspect(WBP, 'RefreshBattlePresentation')
    hits = [n['node_id'] for n in ns for p in n['pins'] if p['name'] == 'A' and p.get('default_value') == VICTORY]
    if not hits:
        return 'kept'
    b = Batch(WBP, 'RefreshBattlePresentation')
    for nid in hits:
        b.pin(nid, 'A', '')
    b.run()
    return 'emptied %d' % len(hits)


assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
BANNER = '--banner' in sys.argv
token = h.lease_acquire('story', ['asset:' + P] + (['asset:' + WBP] if BANNER else []), ttl_s=240, wait_s=240)
try:
    for name in ('PayoffShot', 'PayoffShotOut', 'PayoffShotCut'):
        ensure_function(name)
    report = dict(PayoffShot=payoff_shot(), PayoffShotOut=payoff_out(), PayoffShotCut=payoff_cut(), SuitUp=suit_up(),
                  ResetHouse=reset_house(), Tune=tune(), VictoryBanner=victory_banner() if BANNER else 'UI lane')
    ns, _ = inspect(P, 'SuitUp')
    assert any(n['title'] == 'PayoffShot' for n in ns)
    assert not any(any(p['name'] == 'FunctionName' and p.get('default_value') == 'PayoffDone' for p in n['pins']) for n in ns)
    Path('P:/FoA/Saved/StoryShots/payoff_shot_patch.json').write_text(json.dumps(report, indent=1))
    print('payoff shot', report)
finally:
    h.release('story', token)
