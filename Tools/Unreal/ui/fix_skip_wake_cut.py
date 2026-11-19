"""ui lane: the wake-up skip cuts under black (intro_bugs.md B9).
BP_BeatDirector.SkipWakeUp did GoToEndAndStop, WakeUpDone, then StartCameraFade 1 -> 0 over 0.5 s. At a 50 ms frame the
first faded frame is already 0.9, and the pawn camera settles a frame late, so one dim frame from the wrong angle showed
(sweep_r3_skip f0305). Now the fade HOLDS black on the cut frame and a SkipFadeUp timer fades up 0.15 s later.
Edits only the skip chain (beat logic untouched). Editor Python because Hayba's blueprint_inspect_graph truncates this
149-node graph at 50 nodes, so the skip nodes have no reachable GUIDs. Idempotent: reruns reuse SkipFadeUp and its timer.
  python Tools/Unreal/ue_remote.py Tools/Unreal/ui/fix_skip_wake_cut.py   (FOA_AREAS=Gameplay, editor closed on the BP)"""
import unreal

exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())
BD = '/Game/FoA/Gameplay/BP_BeatDirector'
KSL = '/Script/Engine.KismetSystemLibrary'
CAM = '/Script/Engine.PlayerCameraManager:StartCameraFade'
HOLD_S = 0.15


def title(n):
    return str(BEL.get_node_title(n)).replace('\n', ' ')


def exec_next(n):
    """Nodes on n's outgoing exec pins."""
    out = []
    for p in BEL.list_all_pins(n):
        if PIN.get_pin_direction(p) == unreal.EdGraphPinDirection.EGPD_OUTPUT and 'exec' in str(PIN.get_pin_type_display_string(p)).lower():
            out += [PIN.get_owning_node(lp) for lp in PIN.list_connected_pins(p)]
    return out


def run():
    asset = unreal.load_asset(BD)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(asset)
    g = Graph(BD, 'EventGraph')
    nodes = list(g.ed.list_all_nodes())
    skip = [n for n in nodes if title(n) == 'SkipWakeUp' and n.get_class().get_name() == 'K2Node_CustomEvent']
    assert len(skip) == 1, [title(n) for n in skip]
    chain, q = [], [skip[0]]
    while q:  # the skip's exec chain, in order
        n = q.pop(0)
        if n in chain:
            continue
        chain.append(n)
        q += exec_next(n)
    fades = [n for n in chain if title(n) == 'StartCameraFade']
    assert len(fades) == 1, [title(n) for n in chain]
    fade = fades[0]
    # 1. the cut frame is black: hold at 1 (timers tick before the camera update, so this frame already uses it)
    # Duration > 0: PlayerCameraManager::UpdateCamera only recomputes FadeAmount when FadeTime > 0 (0 never reaches black)
    g.default(fade, 'FromAlpha', 1.0); g.default(fade, 'ToAlpha', 1.0); g.default(fade, 'Duration', 0.01)
    g.default(fade, 'bHoldWhenFinished', 'true')
    fpos = BEL.get_node_pos(fade)
    # 2. after the hold, fade up (timer on the fade's then pin; reuse one already there)
    nxt = exec_next(fade)
    tmr = nxt[0] if nxt and title(nxt[0]).startswith('Set Timer by Function Name') else None
    if tmr is None:
        tmr = g.call(f'{KSL}:K2_SetTimer', fpos.x + 320, fpos.y)
        g.link(fade, 'then', tmr, 'execute')
    g.default(tmr, 'FunctionName', 'SkipFadeUp'); g.default(tmr, 'Time', HOLD_S); g.default(tmr, 'bLooping', 'false')
    # 3. SkipFadeUp: 1 -> 0 over 0.5 s, the fade the skip always had
    ev = [n for n in nodes if title(n) == 'SkipFadeUp' and n.get_class().get_name() == 'K2Node_CustomEvent']
    if not ev:
        x, y = fpos.x, fpos.y + 640
        e = g.custom_event('SkipFadeUp', x, y)
        cam = g.call('/Script/Engine.GameplayStatics:GetPlayerCameraManager', x + 64, y + 224, PlayerIndex=0)
        up = g.call(CAM, x + 320, y, FromAlpha=1.0, ToAlpha=0.0, Duration=0.5)
        g.default(up, 'Color', '(R=0.0,G=0.0,B=0.0,A=1.0)')
        g.link(e, 'then', up, 'execute'); g.link(cam, 'ReturnValue', up, 'self')
        g.comment('Fade up after skip', 'The skip cut happened under black; now fade the room up', [e, cam, up], C_EVENT)
    print('skip chain:', ' -> '.join(title(n) for n in chain + [tmr]))
    print('saved', unreal.EditorAssetLibrary.save_asset(BD, only_if_is_dirty=False))


run()
