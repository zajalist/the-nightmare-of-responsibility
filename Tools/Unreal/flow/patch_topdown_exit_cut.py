"""ExitTopDown cuts under a short fade instead of a 1.5 s camera blend (QA bug 4b: the blend swept from above into the
head and showed the player's own third-person body for about a second). Hayba only; idempotent; build_director.py matches.
  ExitTopDown:    guard, bTopDown false, the camera fades to black over 0.2 s (held), timer ExitTopDownCut 0.2 s.
  ExitTopDownCut: PlayerTopDown(false), HideNightmare, SetViewTargetWithBlend(pawn, 0), look input back, ShowCeiling,
                  then BP_FoAPlayer.HandoffFadeUp (the player's single-owner fade-up; a plain 0.5 s fade if the pawn is
                  not the player class).
  python Tools/Unreal/flow/patch_topdown_exit_cut.py"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
C = P + '.BP_BeatDirector_C'
PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'
GS, KS = '/Script/Engine.GameplayStatics:', '/Script/Engine.KismetSystemLibrary:'
PCM = '/Script/Engine.PlayerCameraManager:StartCameraFade'
DOWN = 0.2
BLACK = '(R=0.0,G=0.0,B=0.0,A=1.0)'

os.environ['HAYBA_AGENT_ID'] = 'story'
assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + P], ttl_s=150, wait_s=180)
report = {}
try:
    if not h.call('blueprint_inspect_graph', {'path': P, 'graph_name': 'ExitTopDownCut'}).get('ok'):
        r = h.call('blueprint_add_function', {'path': P, 'function_name': 'ExitTopDownCut'})
        assert r.get('ok'), r
    ns, _ = inspect(P, 'ExitTopDownCut')
    if not any(n['title'] == 'SetViewTargetWithBlend' for n in ns):
        entry = find(ns, 'ExitTopDownCut')
        b = Batch(P, 'ExitTopDownCut')
        b.fn('mode', C + ':PlayerTopDown', 250, 0, Enable='false')
        b.fn('hide', C + ':HideNightmare', 500, 0)
        b.fn('pc', GS + 'GetPlayerController', 500, 300, PlayerIndex=0)
        b.fn('pawn', GS + 'GetPlayerPawn', 500, 450, PlayerIndex=0)
        b.fn('cut', '/Script/Engine.PlayerController:SetViewTargetWithBlend', 800, 0, BlendTime=0)
        b.link('pc', 'ReturnValue', 'cut', 'self')
        b.link('pawn', 'ReturnValue', 'cut', 'NewViewTarget')
        b.fn('look', '/Script/Engine.Controller:SetIgnoreLookInput', 1100, 0, bNewLookInput='false')
        b.link('pc', 'ReturnValue', 'look', 'self')
        b.fn('ceiling', C + ':ShowCeiling', 1400, 0)
        b.node('player', 'cast', 1700, 0, class_path=PLAYER)
        b.link('pawn', 'ReturnValue', 'player', 'Object')
        b.fn('up', PLAYER + ':HandoffFadeUp', 2000, -120)
        b.link('player', 'AsBP Fo APlayer', 'up', 'self')
        b.fn('cam', GS + 'GetPlayerCameraManager', 2000, 300, PlayerIndex=0)
        b.fn('plain', PCM, 2000, 160, FromAlpha=1.0, ToAlpha=0.0, Duration=0.5, Color=BLACK)
        b.link('cam', 'ReturnValue', 'plain', 'self')
        b.link(entry, 'then', 'mode', 'execute')
        b.chain('mode', 'hide', 'cut', 'look', 'ceiling', 'player')
        b.link('player', 'then', 'up', 'execute')
        b.link('player', 'CastFailed', 'plain', 'execute')
        b.comment('Cut back under black', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
        b.run()
        report['ExitTopDownCut'] = 'built'
    ns, es = inspect(P, 'ExitTopDown')
    if any(n['title'] == 'SetViewTargetWithBlend' for n in ns):
        setter = find(ns, 'Set bTopDown')
        moved = [n['node_id'] for n in ns if n['title'] in ('PlayerTopDown', 'HideNightmare', 'GetPlayerController', 'GetPlayerPawn',
                                                            'Get TopDownBlend', 'SetViewTargetWithBlend', 'SetIgnoreLookInput',
                                                            'Set Timer by Function Name')]
        b = Batch(P, 'ExitTopDown')
        b.ops.append(dict(op='remove', node_ids=moved))
        b.fn('cam', GS + 'GetPlayerCameraManager', 800, 300, PlayerIndex=0)
        b.fn('down', PCM, 800, 0, FromAlpha=0.0, ToAlpha=1.0, Duration=DOWN, Color=BLACK, bHoldWhenFinished='true')
        b.link('cam', 'ReturnValue', 'down', 'self')
        b.fn('later', KS + 'K2_SetTimer', 1150, 0, FunctionName='ExitTopDownCut', Time=DOWN, bLooping='false')
        b.link(setter, 'then', 'down', 'execute')
        b.chain('down', 'later')
        b.comment('Fade, then cut', ['cam', 'down', 'later'])
        b.run()
        report['ExitTopDown'] = 'fade %.1f s, then ExitTopDownCut' % DOWN
    ns, _ = inspect(P, 'ExitTopDown')
    assert not any(n['title'] == 'SetViewTargetWithBlend' for n in ns)
    assert any(n['title'] == 'Set Timer by Function Name' for n in ns)
    Path('P:/FoA/Saved/StoryShots/topdown_exit_cut.json').write_text(json.dumps(report, indent=1))
    print('top-down exit cuts under black', report)
finally:
    h.release('story', token)
