"""Compose continuous garment flight in actor space with existing body-relative attack animations.
Run declare then body via hayba_replay under a BP_Garment lease; no new content assets.
"""
import os
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())

BP = '/Game/FoA/Gameplay/Encounter/BP_Garment'
KML = '/Script/Engine.KismetMathLibrary'
KSL = '/Script/Engine.KismetSystemLibrary'
GS = '/Script/Engine.GameplayStatics'
ACTOR = '/Script/Engine.Actor'
MPC = '/Game/FoA/PostProcess/MPC_Dream.MPC_Dream'
FUNCTIONS = ('StartBattleMotion', 'StepBattleMotion', 'StopBattleMotion', 'KickBattleMotion')


def wave(g, clock, phase, speed, amplitude, x, y):
    rate = g.call(KML + ':Multiply_DoubleDouble', x, y, B=speed)
    offset = g.call(KML + ':Add_DoubleDouble', x + 260, y)
    sine = g.call(KML + ':Sin', x + 520, y)
    scale = g.call(KML + ':Multiply_DoubleDouble', x + 780, y, B=amplitude)
    g.link(clock, 'ReturnValue', rate, 'A'); g.link(phase, 'MotionPhase', offset, 'B')
    g.link(rate, 'ReturnValue', offset, 'A'); g.link(offset, 'ReturnValue', sine, 'A')
    g.link(sine, 'ReturnValue', scale, 'A')
    return scale


def hook(event, function):
    g = Graph(BP)
    nodes = g.ed.list_nodes_of_class(unreal.K2Node_CustomEvent)
    match = [n for n in nodes if BEL.get_node_title(n).split('\n')[0].replace(' ', '') == event]
    assert len(match) == 1, event
    then = BEL.find_then_pin(match[0]); connected = PIN.list_connected_pins(then)
    assert len(connected) == 1, event
    target = PIN.get_owning_node(connected[0])
    if BEL.get_node_title(target).replace(' ', '').startswith(function):
        return
    old = connected[0]; PIN.break_pin_links(then)
    pos = BEL.get_node_pos(match[0])
    call = g.call(self_call(BP, function), pos.x + 180, pos.y - 180)
    assert PIN.try_create_connection(then, g.pin(call, 'execute', 'in'))
    assert PIN.try_create_connection(BEL.find_then_pin(call), old)
    g.comment('Flight motion', '', [call], C_VISUAL)


if os.environ.get('FOA_MOTION_PHASE') == 'declare':
    ensure_vars(BP, [
        ('bMotionActive', ptype('bool'), 'false', 'Flight', False),
        ('MotionHome', ptype(unreal.Transform), '', 'Flight', False),
        ('MotionPhase', ptype('real'), '0.0', 'Flight', False),
        ('MotionAttackAt', ptype('real'), '-100.0', 'Flight', False),
    ])
    names = {str(n) for n in BEL.list_graph_names(unreal.load_asset(BP))}
    for name in FUNCTIONS:
        if name not in names:
            Graph.function(BP, name)
    compile_save(BP)
else:
    g = Graph.function(BP, 'StartBattleMotion'); e = g.at(entry_node(g), 0, 0)
    active = g.get('bMotionActive', 0, 220); br = g.branch(260, 0)
    home = g.call(ACTOR + ':GetTransform', 520, 220); save = g.set('MotionHome', 800, 100)
    random = g.call(KML + ':RandomFloatInRange', 800, 420, Min=0.0, Max=6.283185)
    phase = g.set('MotionPhase', 1100, 100); enable = g.set('bMotionActive', 1400, 100)
    g.default(enable, 'bMotionActive', 'true')
    timer = g.call(KSL + ':K2_SetTimer', 1700, 100, FunctionName='StepBattleMotion', Time=0.0333, bLooping='true')
    g.link(active, 'bMotionActive', br, 'Condition'); g.exec_chain(e, br)
    g.link(br, 'False', save, 'execute'); g.link(home, 'ReturnValue', save, 'MotionHome')
    g.link(random, 'ReturnValue', phase, 'MotionPhase'); g.exec_chain(save, phase, enable, timer)
    g.comment('Begin garment flight', '', g.ed.list_all_nodes(), C_VISUAL)

    g = Graph.function(BP, 'StopBattleMotion'); e = g.at(entry_node(g), 0, 0)
    active = g.get('bMotionActive', 0, 200); br = g.branch(280, 0)
    clear = g.call(KSL + ':K2_ClearTimer', 560, 0, FunctionName='StepBattleMotion')
    disable = g.set('bMotionActive', 840, 0); g.default(disable, 'bMotionActive', 'false')
    home = g.get('MotionHome', 840, 220)
    restore = g.call(ACTOR + ':K2_SetActorTransform', 1140, 0, bSweep='false', bTeleport='true')
    g.exec_chain(e, br); g.link(active, 'bMotionActive', br, 'Condition')
    g.link(br, 'True', clear, 'execute'); g.exec_chain(clear, disable, restore)
    g.link(home, 'MotionHome', restore, 'NewTransform')
    g.comment('Stop garment flight', '', g.ed.list_all_nodes(), C_VISUAL)

    g = Graph.function(BP, 'KickBattleMotion'); e = g.at(entry_node(g), 0, 0)
    time = g.call(GS + ':GetTimeSeconds', 0, 200); save = g.set('MotionAttackAt', 280, 0)
    loc = g.call(ACTOR + ':K2_GetActorLocation', 280, 220)
    burst = g.call('/Game/FoA/VFX/Sand/BPL_SandFX.BPL_SandFX_C:SpawnSandBurst', 580, 0, Scale=0.35)
    g.link(time, 'ReturnValue', save, 'MotionAttackAt'); g.link(loc, 'ReturnValue', burst, 'Location')
    g.exec_chain(e, save, burst)
    g.comment('Attack flight accent', '', g.ed.list_all_nodes(), C_VISUAL)

    g = Graph.function(BP, 'StepBattleMotion'); e = g.at(entry_node(g), 0, 0)
    active = g.get('bMotionActive', 0, 200); br = g.branch(280, 0)
    state = g.get('State', 0, 400)
    alive = g.call(KML + ':NotEqual_NameName', 280, 400, B='Defeated'); alive_br = g.branch(560, 0)
    stop = g.call(self_call(BP, 'StopBattleMotion'), 840, 1100)
    g.exec_chain(e, br); g.link(active, 'bMotionActive', br, 'Condition')
    g.link(state, 'State', alive, 'A'); g.link(alive, 'ReturnValue', alive_br, 'Condition')
    g.link(br, 'True', alive_br, 'execute'); g.link(alive_br, 'False', stop, 'execute')
    time = g.call(GS + ':GetTimeSeconds', 560, 240); phase = g.get('MotionPhase', 560, 420)
    attack = g.get('MotionAttackAt', 560, 600)
    elapsed = g.call(KML + ':Subtract_DoubleDouble', 840, 600)
    decay = g.call(KML + ':Divide_DoubleDouble', 1100, 600, B=0.7)
    invert = g.call(KML + ':Subtract_DoubleDouble', 1360, 600, A=1.0)
    envelope = g.call(KML + ':FClamp', 1620, 600, Min=0.0, Max=1.0)
    extra = g.call(KML + ':Multiply_DoubleDouble', 1880, 600, B=1.8)
    gain = g.call(KML + ':Add_DoubleDouble', 2140, 600, B=1.0)
    rm = g.call('/Script/Engine.KismetMaterialLibrary:GetScalarParameterValue', 1360, 850,
                Collection=MPC, ParameterName='ReduceMotion')
    rm_scale = g.call(KML + ':Multiply_DoubleDouble', 1620, 850, B=0.9)
    calm = g.call(KML + ':Subtract_DoubleDouble', 1880, 850, A=1.0)
    amplitude = g.call(KML + ':Multiply_DoubleDouble', 2400, 600)
    g.link(time, 'ReturnValue', elapsed, 'A'); g.link(attack, 'MotionAttackAt', elapsed, 'B')
    for a, b, pin in ((elapsed, decay, 'A'), (decay, invert, 'B'), (invert, envelope, 'Value'),
                      (envelope, extra, 'A'), (extra, gain, 'A'), (rm, rm_scale, 'A'), (rm_scale, calm, 'B')):
        g.link(a, 'ReturnValue', b, pin)
    g.link(gain, 'ReturnValue', amplitude, 'A'); g.link(calm, 'ReturnValue', amplitude, 'B')
    axes = [wave(g, time, phase, rate, size, 840, -900 + i * 300)
            for i, (rate, size) in enumerate(((0.95, 26.0), (1.37, 22.0), (1.65, 20.0)))]
    vector = g.call(KML + ':MakeVector', 2140, -600)
    for i, (node, pin) in enumerate(zip(axes, ('X', 'Y', 'Z'))):
        scaled = g.call(KML + ':Multiply_DoubleDouble', 1880, -1100 - i * 180)
        g.link(node, 'ReturnValue', scaled, 'A'); g.link(amplitude, 'ReturnValue', scaled, 'B')
        g.link(scaled, 'ReturnValue', vector, pin)
    home = g.get('MotionHome', 2140, 100)
    parts = g.call(KML + ':BreakTransform', 2400, 100)
    add = g.call(KML + ':Add_VectorVector', 2920, -200)
    move = g.call(ACTOR + ':K2_SetActorLocation', 3180, 0, bSweep='false', bTeleport='true')
    g.link(home, 'MotionHome', parts, 'InTransform')
    g.link(parts, 'Location', add, 'A'); g.link(vector, 'ReturnValue', add, 'B')
    g.link(add, 'ReturnValue', move, 'NewLocation'); g.link(alive_br, 'True', rm, 'execute')
    g.exec_chain(rm, move)
    roll = wave(g, time, phase, 1.21, 8.0, 840, 1400)
    yaw = wave(g, time, phase, 0.78, 12.0, 840, 1700)
    rscale = g.call(KML + ':Multiply_DoubleDouble', 2140, 1400)
    yscale = g.call(KML + ':Multiply_DoubleDouble', 2140, 1700)
    rot = g.call(KML + ':MakeRotator', 2660, 1400)
    compose = g.call(KML + ':ComposeRotators', 2920, 1400)
    turn = g.call(ACTOR + ':K2_SetActorRotation', 3460, 0, bTeleportPhysics='true')
    for node, out in ((roll, rscale), (yaw, yscale)):
        g.link(node, 'ReturnValue', out, 'A'); g.link(amplitude, 'ReturnValue', out, 'B')
    g.link(rscale, 'ReturnValue', rot, 'Roll'); g.link(yscale, 'ReturnValue', rot, 'Yaw')
    g.link(parts, 'Rotation', compose, 'A'); g.link(rot, 'ReturnValue', compose, 'B')
    g.link(compose, 'ReturnValue', turn, 'NewRotation'); g.exec_chain(move, turn)
    g.comment('Living garment flight', '', g.ed.list_all_nodes(), C_VISUAL)
    for event, fn in (('Rise', 'StartBattleMotion'), ('Lunge', 'KickBattleMotion'), ('Equip', 'StopBattleMotion')):
        hook(event, fn)
    compile_save(BP)
