"""One owner for the post-wake fade (main, 2026-11-09): BP_FoAPlayer.
SetCinematic(false) with bHandoffFadeIn set (LS_WakeUp keys it at its last frame, which the skip's GoToEndAndStop also
evaluates) now HOLDS black (StartCameraFade 1->1, 0.01 s, held) and sets a 0.15 s timer; HandoffFadeUp then fades the
head camera up from black over 0.5 s. Normal end: the film's 6-frame blink, 0.15 s black, 0.5 s up. Skip: 0.15 s black,
0.5 s up. These match the director's current skip numbers exactly, so until story removes its own skip fade
(StartCameraFade hold + SkipFadeUp timer in SkipWakeUp) both fire on the same frames and nothing flickers.
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/handoff_fade_owner.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
F = 'HandoffFadeUp'
BLACK = '(R=0.000000,G=0.000000,B=0.000000,A=1.000000)'
HOLD_S, UP_S = 0.15, 0.5

assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
# HandoffFadeUp(): the fade up, called by the timer
if not h.call('blueprint_inspect_graph', dict(path=P, graph_name=F)).get('ok'):
    assert h.call('blueprint_add_function', dict(path=P, function_name=F))['ok']
nodes, _ = inspect(P, F)
if len(nodes) <= 1:
    entry = find(nodes, F)
    b = Batch(P, F)
    b.fn('pcm', '/Script/Engine.GameplayStatics:GetPlayerCameraManager', 0, 300, PlayerIndex=0)
    b.fn('up', '/Script/Engine.PlayerCameraManager:StartCameraFade', 300, 0, FromAlpha=1.0, ToAlpha=0.0, Duration=UP_S,
         Color=BLACK, bShouldFadeAudio='false', bHoldWhenFinished='false')
    b.link('pcm', 'ReturnValue', 'up', 'self'); b.link(entry, 'then', 'up', 'execute')
    b.comment('Fade the head camera up', ['pcm', 'up'])
    b.run()
# SetCinematic: the existing fade becomes a held black plus the timer
nodes, edges = inspect(P, 'SetCinematic')
if any(n['title'] in ('Set Timer by Function Name', 'K2_SetTimer') for n in nodes):
    sys.exit('hand-off hold already built')
fade = find(nodes, 'StartCameraFade')
b = Batch(P, 'SetCinematic')
for pin, v in (('FromAlpha', 1.0), ('ToAlpha', 1.0), ('Duration', 0.01), ('bHoldWhenFinished', 'true')):
    b.pin(fade, pin, v)
b.fn('timer', '/Script/Engine.KismetSystemLibrary:K2_SetTimer', 4800, 0, FunctionName=F, Time=HOLD_S, bLooping='false')
b.node('me', 'self', 4800, 300); b.link('me', 'self', 'timer', 'Object')
b.link(fade, 'then', 'timer', 'execute')
b.comment('Hold black, then fade up', ['timer', 'me'])
b.run()
