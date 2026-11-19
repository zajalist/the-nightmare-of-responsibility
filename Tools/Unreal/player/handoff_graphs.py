"""Wake-up hand-off into first person (anim lane, Hayba graph batch).
LS_WakeUp ends on a 6-frame blink to black (Fade, Keep State) and keys BP_FoAPlayer.bHandoffFadeIn true.
SetCinematic(false) then clears the flag and fades the head camera up from black over 0.6 s, after the director has
moved the pawn (SafeWakeExit) and set the control rotation, and after UpdateFirstPersonVisibility has hidden the head.
So the camera never travels into his head and no culled head is ever on screen. Other SetCinematic(false) callers
(door tools, story moments) leave the flag false and get no fade.
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/handoff_graphs.py        (variable + graph, compiled, saved)
  then FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/handoff_graphs.py   (inside the editor:
  the Expose to Cinematics flag, which Hayba's blueprint_add_variable can't set)"""
import sys

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
VAR = 'bHandoffFadeIn'


def expose():
    import unreal
    bp = unreal.load_asset(P)
    unreal.BlueprintEditorLibrary.set_blueprint_variable_expose_to_cinematics(bp, VAR, True)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    print('EXPOSED', VAR)


def graph():
    sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
    import hayba_call as h
    from held_tool_graphs import Batch, inspect, find
    assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
    r = h.call('blueprint_add_variable', dict(path=P, variable_name=VAR, variable_type='bool', default_value='false',
                                              instance_editable=False, update_existing=True, category='Cinematic'))
    assert r.get('ok'), r
    nodes, edges = inspect(P, 'SetCinematic')
    if any(n['title'] == 'Set ' + VAR for n in nodes):
        print('SetCinematic already has the hand-off fade')
        return
    tail = find(nodes, 'SetSuspended')
    assert not any(e['from_node'] == tail and e['from_pin'] == 'then' for e in edges), 'SetCinematic tail moved'
    entry = find(nodes, 'SetCinematic')
    K = '/Script/Engine.KismetMathLibrary:'
    b = Batch(P, 'SetCinematic')
    b.get('flag', VAR, 3300, 300)
    b.fn('off', K + 'Not_PreBool', 3300, 450); b.link(entry, 'bEnable', 'off', 'A')
    b.fn('both', K + 'BooleanAND', 3600, 300); b.link('flag', VAR, 'both', 'A'); b.link('off', 'ReturnValue', 'both', 'B')
    b.node('ifhand', 'branch', 3900, 0); b.link('both', 'ReturnValue', 'ifhand', 'Condition')
    b.set('clear', VAR, 4200, 0); b.pin('clear', VAR, 'false')
    b.fn('pcm', '/Script/Engine.GameplayStatics:GetPlayerCameraManager', 4200, 300, PlayerIndex=0)
    b.fn('fade', '/Script/Engine.PlayerCameraManager:StartCameraFade', 4500, 0, FromAlpha=1.0, ToAlpha=0.0,
         Duration=0.6, Color='(R=0.000000,G=0.000000,B=0.000000,A=1.000000)', bShouldFadeAudio='false',
         bHoldWhenFinished='false')
    b.link('pcm', 'ReturnValue', 'fade', 'self')
    b.link(tail, 'then', 'ifhand', 'execute'); b.link('ifhand', 'then', 'clear', 'execute'); b.chain('clear', 'fade')
    b.comment('Wake hand-off fade', ['flag', 'off', 'both', 'ifhand', 'clear', 'pcm', 'fade'])
    b.run()


if __name__ == '__main__':
    try:
        import unreal  # noqa: F401  inside the editor (ue_remote)
    except ImportError:
        graph()
    else:
        expose()
