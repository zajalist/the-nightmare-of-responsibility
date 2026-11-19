"""Bodies for build_door_tools.py. Only the door's own shipping components/functions are changed."""
K = '/Script/Engine.KismetMathLibrary:'
KS = '/Script/Engine.KismetSystemLibrary:'
SC = '/Script/Engine.SceneComponent:'
PC = '/Script/Engine.PlayerController:'
GS = '/Script/Engine.GameplayStatics:'
PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'
INTERACTOR = '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'
phase = os.environ['FOA_PHASE']
exec(open('P:/FoA/Tools/Unreal/gameplay/rusted_key_phases.py', encoding='utf-8').read())


def result_node(g):
    nodes = list(g.ed.list_nodes_of_class(unreal.K2Node_FunctionResult))
    return nodes[0] if nodes else g.ed.add_return_node()


def palette(g, *parts):
    norm = lambda s: str(s).replace(' ', '').replace('_', '').lower()
    found = [str(n) for n in g.ed.list_available_nodes([]) if all(norm(p) in norm(n) for p in parts)]
    assert found, parts
    return min(found, key=len)


def fn(name):
    g = Graph.function(DOOR, name)
    e = g.at(entry_node(g), 0, 0)
    return g, e


def own(g, name, x, y, **values):
    return g.call(DOOR + '.BP_Door_C:' + name, x, y, **values)


def get(g, name, x=0, y=200):
    return g.get(name, x, y)


def setv(g, name, x, y, value=None, source=None):
    n = g.set(name, x, y)
    if source:
        g.link(source[0], source[1], n, name)
    elif value is not None:
        g.default(n, name, value)
    return n


def result(g, n, pin='ReturnValue'):
    return n, pin


def calc(g, name, x, y, a=None, b=None, **values):
    n = g.call(K + name, x, y, **values)
    for pin, src in (('A', a), ('B', b)):
        if src:
            g.link(src[0], src[1], n, pin)
    return n


def block(g, title):
    c = g.ed.add_comment_to_nodes(title, list(g.ed.list_all_nodes()), 48)
    BEL.set_comment_color(c, C_VISUAL); house_comment_flags(c)


def brk(g, src, pin, x=0, y=250):
    n = g.node(palette(g, 'Break', 'S_Interaction'), x, y)
    g.link(src, pin, n, 'S_Interaction')
    return n


def field(n, name):
    return next(str(PIN.get_pin_name(p)) for p in BEL.list_output_pins(n) if str(PIN.get_pin_name(p)).split('_')[0] == name)


def components():
    bp = unreal.load_asset(DOOR)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    parts = {str(lib.get_variable_name(lib.get_data(h))): h for h in sub.k2_gather_subobject_data_for_blueprint(bp)}
    def ensure(name, kind, parent):
        if name not in parts:
            h, error = sub.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=parts[parent], new_class=kind, blueprint_context=bp))
            assert not str(error), error
            sub.rename_subobject(h, name); parts[name] = h
        return lib.get_object_for_blueprint(lib.get_data(parts[name]), bp)
    contact = ensure('ToolContact', unreal.SceneComponent, 'Pivot')
    contact.set_editor_property('relative_location', unreal.Vector(-0.7, -84, 87))
    pivot = ensure('ToolPivot', unreal.SceneComponent, 'ToolContact')
    mesh = ensure('ToolMesh', unreal.StaticMeshComponent, 'ToolPivot')
    mesh.set_collision_profile_name('NoCollision'); mesh.set_editor_property('visible', False)
    camera = ensure('ToolCamera', unreal.CameraComponent, 'Pivot')
    camera.set_editor_property('relative_location', unreal.Vector(-30, -144, 102))
    camera.set_editor_property('relative_rotation', unreal.MathLibrary.find_look_at_rotation(unreal.Vector(-30, -144, 102), unreal.Vector(-7, -84, 88)))
    camera.set_editor_property('field_of_view', 36.0)
    light = ensure('ToolTaskLight', unreal.PointLightComponent, 'Pivot')
    # world lane 2026-11-10: a soft key beside the camera, about 60 cm from the hand and 82 cm from the lock. At (-24,-79,100)
    # it sat 10-15 cm from the hand and blew the arm and the white door out (about 14 and 4.5 lux at EV -1).
    light.set_editor_property('relative_location', unreal.Vector(-40, -150, 125))
    light.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
    light.set_editor_property('intensity', 0.10)   # pending the PIE bracket (0.06 / 0.10 / 0.15) after anim's hand poses
    light.set_editor_property('attenuation_radius', 160.0)
    light.set_editor_property('source_radius', 15.0)
    light.set_editor_property('specular_scale', 0.5)
    light.set_editor_property('cast_shadows', False)
    light.set_editor_property('visible', False)
    plate = ensure('ToolPlate', unreal.StaticMeshComponent, 'Pivot')
    plate.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    plate.set_material(0, unreal.load_asset('/Game/FoA/Props/Door/MI_Door_Brass'))
    plate.set_editor_property('relative_location', unreal.Vector(-0.65, -84, 87))
    plate.set_editor_property('relative_scale3d', unreal.Vector(0.0035, 0.060, 0.118))
    plate.set_collision_profile_name('NoCollision')
    slot = ensure('ToolKeyhole', unreal.StaticMeshComponent, 'Pivot')
    slot.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    slot.set_material(0, unreal.load_asset('/Game/FoA/Materials/MI_DarkSand_Black'))
    slot.set_editor_property('relative_location', unreal.Vector(-0.88, -84, 87))
    slot.set_editor_property('relative_scale3d', unreal.Vector(0.0008, 0.007, 0.018))
    slot.set_collision_profile_name('NoCollision')
    for i, (y, z) in enumerate(((-86.1, 91.5), (-81.9, 91.5), (-86.1, 82.5), (-81.9, 82.5))):
        screw = ensure('ToolScrew' + str(i), unreal.StaticMeshComponent, 'Pivot')
        screw.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cylinder'))
        screw.set_material(0, unreal.load_asset('/Game/FoA/Materials/MI_Metal'))
        screw.set_editor_property('relative_location', unreal.Vector(-1.05, y, z))
        screw.set_editor_property('relative_rotation', unreal.Rotator(roll=0, pitch=90, yaw=0))
        screw.set_editor_property('relative_scale3d', unreal.Vector(0.010, 0.010, 0.0025))
        screw.set_collision_profile_name('NoCollision')
    compile_save(DOOR)


def key_resistance(g, choose, dt, turn):
    # Reuse the door-owned step index, reset by BeginDoorTool. No elapsed-time
    # completion: the player must reverse at the bind before the retry can move.
    previous = choose
    for i, (minimum, maximum, speed, easing) in enumerate(KEY_PHASES):
        y = -1800 - i * 1700
        stage = get(g, 'ToolStepIndex', 1200, y + 350)
        match = calc(g, 'EqualEqual_IntInt', 1500, y + 350, (stage, 'ToolStepIndex'), B=i)
        gate = g.branch(1800, y); g.link(match, 'ReturnValue', gate, 'Condition')
        g.link(previous, 'then' if i == 0 else 'else', gate, 'execute')
        previous = gate
        direction = result(g, turn)
        if easing:
            reverse = calc(g, 'FMin', 1800, y + 550, direction, B=0.0)
            direction = result(g, reverse)
        delta = calc(g, 'Multiply_DoubleDouble', 2100, y + 350, result(g, dt), direction)
        scaled = calc(g, 'Multiply_DoubleDouble', 2400, y + 350, result(g, delta), B=speed)
        angle = get(g, 'ToolAngle', 2400, y + 550)
        added = calc(g, 'Add_DoubleDouble', 2700, y + 350, (angle, 'ToolAngle'), result(g, scaled))
        clamp = g.call(K + 'FClamp', 3000, y + 350, Min=minimum, Max=maximum)
        g.link(added, 'ReturnValue', clamp, 'Value')
        store = setv(g, 'ToolAngle', 3300, y, source=result(g, clamp)); g.exec_chain(gate, store)
        stored = get(g, 'ToolAngle', 3300, y + 500)
        done = calc(g, 'LessEqual_DoubleDouble' if easing else 'GreaterEqual_DoubleDouble',
                    3600, y + 500, (stored, 'ToolAngle'), B=minimum if easing else maximum)
        arrived = g.branch(3900, y); g.link(done, 'ReturnValue', arrived, 'Condition'); g.exec_chain(store, arrived)
        refreshnode = own(g, 'RefreshDoorTool', 4500, y + 200)
        g.link(arrived, 'else', refreshnode, 'execute')
        if i == len(KEY_PHASES) - 1:
            finish = own(g, 'FinishDoorTool', 4200, y); g.exec_chain(arrived, finish)
        else:
            advance = setv(g, 'ToolStepIndex', 4200, y, i + 1)
            contact = get(g, 'ToolContact', 4200, y + 800)
            point = g.call(SC + 'K2_GetComponentLocation', 4500, y + 800); g.link(contact, 'ToolContact', point, 'self')
            soundname = ('KeyInsert', 'KeyJiggle', 'KeyTurn')[i]
            sound = g.call(GS + 'PlaySoundAtLocation', 4500, y - 250,
                           Sound='/Game/FoA/Audio/MetaSounds/Door/S_Door_' + soundname + '.S_Door_' + soundname,
                           VolumeMultiplier=0.65)
            g.link(point, 'ReturnValue', sound, 'Location')
            g.exec_chain(arrived, advance, sound, refreshnode)


def mode_and_advance():
    g, e = fn('GetDoorToolMode'); b = brk(g, e, 'Row')
    pairs = []
    for i, (item, nxt, mode) in enumerate((('Key', 'KeyJammed', 'Key'), ('Screwdriver', 'PlateOff', 'Screwdriver'))):
        y = 300 + i * 400
        a = g.call(K + 'EqualEqual_NameName', 300, y, B=item); g.link(b, field(b, 'Item'), a, 'A')
        n = g.call(K + 'EqualEqual_NameName', 300, y + 160, B=nxt); g.link(b, field(b, 'NextState'), n, 'A')
        both = calc(g, 'BooleanAND', 600, y, result(g, a), result(g, n))
        pairs.append(both)
    second = g.call(K + 'SelectName', 900, 700, A='Screwdriver', B='None'); g.link(pairs[1], 'ReturnValue', second, 'bPickA')
    first = g.call(K + 'SelectName', 1200, 300, A='Key'); g.link(second, 'ReturnValue', first, 'B')
    g.link(pairs[0], 'ReturnValue', first, 'bPickA')
    ret = g.at(result_node(g), 1500, 0); g.exec_chain(e, ret); g.link(first, 'ReturnValue', ret, 'Mode')
    block(g, 'Choose the tool')

    g, e = fn('AdvanceDoorTool')
    active, ready = get(g, 'bToolActive'), get(g, 'bToolReady', 0, 350)
    both = calc(g, 'BooleanAND', 300, 250, (active, 'bToolActive'), (ready, 'bToolReady'))
    guard = g.branch(600, 0); g.link(both, 'ReturnValue', guard, 'Condition'); g.exec_chain(e, guard)
    mode = get(g, 'ToolMode', 600, 250)
    key = calc(g, 'EqualEqual_NameName', 900, 250, (mode, 'ToolMode'), B='Key')
    choose = g.branch(1200, 0); g.link(key, 'ReturnValue', choose, 'Condition'); g.exec_chain(guard, choose)
    dt = g.call(K + 'FClamp', 300, 650, Min=0.0, Max=0.1); g.link(e, 'DeltaSeconds', dt, 'Value')
    turn = g.call(K + 'FClamp', 300, 850, Min=-1.0, Max=1.0); g.link(e, 'Turn', turn, 'Value')
    key_resistance(g, choose, dt, turn)
    delta = calc(g, 'Multiply_DoubleDouble', 600, 650, result(g, dt), result(g, turn))
    y = 1100
    old = get(g, 'ToolAngle', 900, y + 450)
    scaled = calc(g, 'Multiply_DoubleDouble', 1200, y + 450, result(g, delta), B=300.0)
    added = calc(g, 'Add_DoubleDouble', 1500, y + 450, (old, 'ToolAngle'), result(g, scaled))
    clamp = g.call(K + 'FClamp', 1800, y + 450, Min=0.0, Max=720.0); g.link(added, 'ReturnValue', clamp, 'Value')
    store = setv(g, 'ToolAngle', 2100, y, source=result(g, clamp))
    # Read the stored angle: reusing the pure clamp here would double this frame's turn.
    stored = get(g, 'ToolAngle', 2400, y + 700)
    g.link(choose, 'else', store, 'execute')
    done = calc(g, 'GreaterEqual_DoubleDouble', 2400, y + 450, (stored, 'ToolAngle'), B=720.0)
    branch = g.branch(2700, y); g.link(done, 'ReturnValue', branch, 'Condition'); g.exec_chain(store, branch)
    refreshnode = own(g, 'RefreshDoorTool', 3000, y + 240); g.link(branch, 'else', refreshnode, 'execute')
    zero = setv(g, 'ToolAngle', 3000, y, 0.0)
    index = get(g, 'ToolStepIndex', 3000, y + 500)
    add = calc(g, 'Add_IntInt', 3300, y + 500, (index, 'ToolStepIndex'), B=1)
    advance = setv(g, 'ToolStepIndex', 3300, y, source=result(g, add)); g.exec_chain(branch, zero, advance)
    all_done = calc(g, 'GreaterEqual_IntInt', 3600, y + 500, (index, 'ToolStepIndex'), B=4)
    gate = g.branch(3600, y); g.link(all_done, 'ReturnValue', gate, 'Condition'); g.exec_chain(advance, gate)
    finish = own(g, 'FinishDoorTool', 3900, y); g.exec_chain(gate, finish)
    g.link(gate, 'else', refreshnode, 'execute')
    block(g, 'Turn against the resistance')
    compile_save(DOOR)


def input_step():
    g, e = fn('StepDoorTool')
    active = get(g, 'bToolActive'); guard = g.branch(300, 0)
    g.link(active, 'bToolActive', guard, 'Condition'); g.exec_chain(e, guard)
    pc = get(g, 'ToolController', 0, 500)
    nodes = {}
    for i, key in enumerate(('D', 'A', 'Q', 'Gamepad_FaceButton_Right')):
        n = g.call(PC + 'IsInputKeyDown', 300, 400 + i * 180, Key=key)
        g.link(pc, 'ToolController', n, 'self'); nodes[key] = n
    cancelkey = calc(g, 'BooleanOR', 600, 900, result(g, nodes['Q']), result(g, nodes['Gamepad_FaceButton_Right']))
    cancel = g.branch(900, 0); g.link(cancelkey, 'ReturnValue', cancel, 'Condition'); g.exec_chain(guard, cancel)
    end = own(g, 'CancelDoorTool', 1200, -240); g.exec_chain(cancel, end)
    positive = g.call(K + 'SelectFloat', 600, 400, A=1.0, B=0.0); g.link(nodes['D'], 'ReturnValue', positive, 'bPickA')
    negative = g.call(K + 'SelectFloat', 600, 580, A=1.0, B=0.0); g.link(nodes['A'], 'ReturnValue', negative, 'bPickA')
    keys = calc(g, 'Subtract_DoubleDouble', 900, 400, result(g, positive), result(g, negative))
    axis = g.call(PC + 'GetInputAnalogKeyState', 900, 650, Key='Gamepad_RightX'); g.link(pc, 'ToolController', axis, 'self')
    analog = calc(g, 'Add_DoubleDouble', 1200, 400, result(g, keys), result(g, axis))
    mouse = g.call(PC + 'GetInputMouseDelta', 900, 900); g.link(pc, 'ToolController', mouse, 'self')
    mx = calc(g, 'Multiply_DoubleDouble', 1200, 900, result(g, mouse, 'DeltaX'), B=0.06)
    combined = calc(g, 'Add_DoubleDouble', 1500, 400, result(g, analog), result(g, mx))
    now = g.call(GS + 'GetTimeSeconds', 1200, 1150)
    before = get(g, 'ToolLastTime', 1200, 1300)
    dt = calc(g, 'Subtract_DoubleDouble', 1500, 1150, result(g, now), (before, 'ToolLastTime'))
    advance = own(g, 'AdvanceDoorTool', 1800, 0); g.link(combined, 'ReturnValue', advance, 'Turn')
    g.link(dt, 'ReturnValue', advance, 'DeltaSeconds'); g.link(cancel, 'else', advance, 'execute')
    last = setv(g, 'ToolLastTime', 2100, 0, source=result(g, now)); g.exec_chain(advance, last)
    block(g, 'Read the real controls'); compile_save(DOOR)


def refresh():
    g, e = fn('RefreshDoorTool')
    active = get(g, 'bToolActive'); guard = g.branch(300, 0)
    g.link(active, 'bToolActive', guard, 'Condition'); g.exec_chain(e, guard)
    mode = get(g, 'ToolMode', 0, 400)
    key = calc(g, 'EqualEqual_NameName', 300, 400, (mode, 'ToolMode'), B='Key')
    index = get(g, 'ToolStepIndex', 0, 800)
    # Physical four-corner screw positions measured against the shipped door's keyhole atY=-84,Z=87cm.
    side = calc(g, 'Percent_IntInt', 300, 800, (index, 'ToolStepIndex'), B=2)
    top = calc(g, 'Less_IntInt', 300, 1000, (index, 'ToolStepIndex'), B=2)
    ys = g.call(K + 'SelectFloat', 600, 800, A=-86.1, B=-81.9)
    left = calc(g, 'EqualEqual_IntInt', 300, 1200, result(g, side), B=0); g.link(left, 'ReturnValue', ys, 'bPickA')
    zs = g.call(K + 'SelectFloat', 600, 1000, A=91.5, B=82.5); g.link(top, 'ReturnValue', zs, 'bPickA')
    screw = g.call(K + 'MakeVector', 900, 800, X=-1.17)
    g.link(ys, 'ReturnValue', screw, 'Y'); g.link(zs, 'ReturnValue', screw, 'Z')
    keypos = g.call(K + 'MakeVector', 900, 450, X=-0.65, Y=-84, Z=87)
    position = g.call(K + 'SelectVector', 1200, 600)
    g.link(keypos, 'ReturnValue', position, 'A'); g.link(screw, 'ReturnValue', position, 'B')
    g.link(key, 'ReturnValue', position, 'bPickA')
    contact = get(g, 'ToolContact', 1200, 1050)
    move = g.call(SC + 'K2_SetRelativeLocation', 1500, 0)
    g.link(contact, 'ToolContact', move, 'self'); g.link(position, 'ReturnValue', move, 'NewLocation')
    pivot = get(g, 'ToolPivot', 1500, 800)
    angle = get(g, 'ToolAngle', 1500, 1050)
    rotation = g.call(K + 'MakeRotator', 1800, 600); g.link(angle, 'ToolAngle', rotation, 'Roll')
    rotate = g.call(SC + 'K2_SetRelativeRotation', 2100, 0)
    g.link(pivot, 'ToolPivot', rotate, 'self'); g.link(rotation, 'ReturnValue', rotate, 'NewRotation')
    g.exec_chain(guard, move, rotate)
    prev = rotate
    for i in range(4):
        screwcomp = get(g, 'ToolScrew' + str(i), 2400 + i * 300, 600)
        remains = calc(g, 'LessEqual_IntInt', 2400 + i * 300, 850, (index, 'ToolStepIndex'), B=i)
        visible = calc(g, 'BooleanOR', 2400 + i * 300, 1100, result(g, key), result(g, remains))
        show = g.call(SC + 'SetVisibility', 2400 + i * 300, 0)
        g.link(screwcomp, 'ToolScrew' + str(i), show, 'self'); g.link(visible, 'ReturnValue', show, 'bNewVisibility')
        g.exec_chain(prev, show); prev = show
    player_bp = unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
    if 'SetToolHandTarget' in [str(n) for n in BEL.list_graph_names(player_bp)]:
        pawn = get(g, 'ToolPlayer', 3600, 1600)
        cast = g.node(palette(g, 'CastToBP_FoAPlayer'), 3600, 0); g.link(pawn, 'ToolPlayer', cast, 'Object')
        worldpoint = g.call(SC + 'K2_GetComponentLocation', 3600, 1000); g.link(contact, 'ToolContact', worldpoint, 'self')
        normal = g.call('/Script/Engine.Actor:GetActorForwardVector', 3900, 1000)
        # Actual key bow front edge: 3.31 mm thick, matching the Teen's 3.37 mm pinch.
        grip = g.call(K + 'SelectFloat', 3900, 1250, A=-5.6590909091, B=-16.0); g.link(key, 'ReturnValue', grip, 'bPickA')
        back = calc(g, 'Multiply_VectorFloat', 4200, 1000, result(g, normal), result(g, grip))
        hand = calc(g, 'Add_VectorVector', 4500, 1000, result(g, worldpoint), result(g, back))
        ready = get(g, 'bToolReady', 4200, 1500)
        weight = g.call(K + 'SelectFloat', 4500, 1500, A=1.0, B=0.0); g.link(ready, 'bToolReady', weight, 'bPickA')
        push = g.call(PLAYER + ':SetToolHandTarget', 4800, 0)
        g.link(cast, 'AsBP_FoAPlayer', push, 'self'); g.link(hand, 'ReturnValue', push, 'TargetWorld')
        g.link(weight, 'ReturnValue', push, 'Weight'); g.exec_chain(prev, cast, push); prev = push
        if 'SetToolHandRotation' in [str(n) for n in BEL.list_graph_names(player_bp)]:
            wrist = g.call(K + 'RotatorFromAxisAndAngle', 4800, 1250)
            # FQuat axis-angle uses the opposite sign to Unreal Rotator.Roll about X.
            # ToolPivot uses Roll directly, so negate the axis angle to match its motion.
            clockwise = calc(g, 'Multiply_DoubleDouble', 4500, 1800, (angle, 'ToolAngle'), B=-1.0)
            g.link(normal, 'ReturnValue', wrist, 'Axis'); g.link(clockwise, 'ReturnValue', wrist, 'Angle')
            rotatehand = g.call(PLAYER + ':SetToolHandRotation', 5100, 0)
            g.link(cast, 'AsBP_FoAPlayer', rotatehand, 'self'); g.link(wrist, 'ReturnValue', rotatehand, 'DeltaWorld')
            g.exec_chain(prev, rotatehand); prev = rotatehand
    # HUD is provided by the UI lane. Its bottom prompt is protected from normal focus clears while a tool owns it.
    front = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
    hud = '/Game/FoA/UI/Game/WBP_HUD.WBP_HUD_C'
    bp_hud = unreal.load_asset('/Game/FoA/UI/Game/WBP_HUD')
    if bp_hud and 'ShowToolStatus' in [str(n) for n in BEL.list_graph_names(bp_hud)]:
        compact_hud = 'SetToolFeedback' in [str(n) for n in BEL.list_graph_names(bp_hud)]
        fe = g.call(GS + 'GetActorOfClass', 3600, 0, ActorClass=front)
        widget = g.get('HUD', 3600, 500, class_path=front); g.link(fe, 'ReturnValue', widget, 'self')
        hudcast = g.node(palette(g, 'CastToWBP_HUD'), 3900, -300); g.link(widget, 'HUD', hudcast, 'Object')
        fmt = g.node(palette(g, 'Format Text'), 3900, 600)
        g.default(fmt, 'Format', 'Loosen screw {N} of 4' if compact_hud else
            'Screw {N} of 4 ({Progress}%)\nD Turn   A Reverse   Q Cancel\nGamepad: right stick turns, B cancels.')
        count = calc(g, 'Add_IntInt', 3600, 850, (index, 'ToolStepIndex'), B=1); g.link(count, 'ReturnValue', fmt, 'N')
        percent = calc(g, 'Multiply_DoubleDouble', 3900, 2200, (angle, 'ToolAngle'), B=100.0 / 720.0)
        rounded = g.call(K + 'Round', 4200, 2200); g.link(percent, 'ReturnValue', rounded, 'A')
        if not compact_hud:g.link(rounded, 'ReturnValue', fmt, 'Progress')
        keycopy = None
        hints = ('Find the catch','Keep gentle pressure','Ease back','Turn again') if compact_hud else KEY_HINTS
        for stage in reversed(range(3)):
            y = 2500 + stage * 350
            isstage = calc(g, 'EqualEqual_IntInt', 3900, y, (index, 'ToolStepIndex'), B=stage)
            copy = g.call(K + 'SelectString', 4200, y, A=hints[stage], B=hints[3])
            g.link(isstage, 'ReturnValue', copy, 'bPickA')
            if keycopy:g.link(keycopy, 'ReturnValue', copy, 'B')
            keycopy = copy
        keytext = g.call('/Script/Engine.KismetTextLibrary:Conv_StringToText', 4500, 2500)
        g.link(keycopy, 'ReturnValue', keytext, 'InString')
        keyformat = g.node(palette(g, 'Format Text'), 4800, 2900)
        g.default(keyformat, 'Format', '{Hint}' if compact_hud else
            '{Hint}\nTension {Tension}%\nD Turn   A Ease back   Q Cancel\nGamepad: right stick turns, B cancels.')
        g.link(keytext, 'ReturnValue', keyformat, 'Hint')
        load = calc(g, 'Subtract_DoubleDouble', 4200, 3900, (angle, 'ToolAngle'), B=18.0)
        pressure = calc(g, 'Multiply_DoubleDouble', 4500, 3900, result(g, load), B=100.0 / 24.0)
        tension = g.call(K + 'FClamp', 4800, 3900, Min=0.0, Max=100.0); g.link(pressure, 'ReturnValue', tension, 'Value')
        tensionpct = g.call(K + 'Round', 5100, 3900); g.link(tension, 'ReturnValue', tensionpct, 'A')
        if not compact_hud:g.link(tensionpct, 'ReturnValue', keyformat, 'Tension')
        choose = g.branch(3900, 0); g.link(key, 'ReturnValue', choose, 'Condition')
        keyline = g.call(hud + ':ShowToolStatus', 4200, 0)
        g.link(keyformat, 'Result', keyline, 'LineText')
        screwline = g.call(hud + ':ShowToolStatus', 4200, 300)
        g.link(hudcast, 'AsWBP_HUD', keyline, 'self'); g.link(hudcast, 'AsWBP_HUD', screwline, 'self')
        g.link(fmt, 'Result', screwline, 'LineText')
        g.exec_chain(prev, fe, hudcast, choose, keyline); g.link(choose, 'else', screwline, 'execute')
        if compact_hud:
            span=g.call(K+'SelectFloat',5400,4500,A=55.,B=720.);g.link(key,'ReturnValue',span,'bPickA')
            progress=calc(g,'Divide_DoubleDouble',5700,4500,(angle,'ToolAngle'),result(g,span))
            progress_clamp=g.call(K+'FClamp',6000,4500,Min=0.,Max=1.);g.link(progress,'ReturnValue',progress_clamp,'Value')
            bound_stage=calc(g,'EqualEqual_IntInt',5400,4800,(index,'ToolStepIndex'),B=2)
            bound=calc(g,'BooleanAND',5700,4800,result(g,key),result(g,bound_stage))
            feedback=g.call(hud+':SetToolFeedback',6300,0)
            g.link(hudcast,'AsWBP_HUD',feedback,'self');g.link(progress_clamp,'ReturnValue',feedback,'Progress');g.link(bound,'ReturnValue',feedback,'bBound')
            g.exec_chain(keyline,feedback);g.exec_chain(screwline,feedback)
    block(g, 'Keep the tool in contact'); compile_save(DOOR)


def start_and_hold():
    g, e = fn('BeginDoorTool')
    row = setv(g, 'ToolRow', 300, 0, source=(e, 'Row'))
    mode = own(g, 'GetDoorToolMode', 0, 400); g.link(e, 'Row', mode, 'Row')
    setmode = setv(g, 'ToolMode', 600, 0, source=result(g, mode, 'Mode'))
    pc = g.call(GS + 'GetPlayerController', 600, 400, PlayerIndex=0)
    setpc = setv(g, 'ToolController', 900, 0, source=result(g, pc))
    pawn = g.call(GS + 'GetPlayerCharacter', 900, 500, PlayerIndex=0)
    setpawn = setv(g, 'ToolPlayer', 1200, 0, source=result(g, pawn))
    previous = g.call(PC + 'GetViewTarget', 1200, 500); g.link(pc, 'ReturnValue', previous, 'self')
    cache = setv(g, 'ToolPreviousView', 1500, 0, source=result(g, previous))
    active = setv(g, 'bToolActive', 1800, 0, True)
    ready = setv(g, 'bToolReady', 2100, 0, False)
    angle = setv(g, 'ToolAngle', 2400, 0, 0.0)
    inputangle = setv(g, 'ToolInputAngle', 2700, 0, 0.0)
    index = setv(g, 'ToolStepIndex', 3000, 0, 0)
    lasttime = g.call(GS + 'GetTimeSeconds', 3000, 600)
    last = setv(g, 'ToolLastTime', 3300, 0, source=result(g, lasttime))
    iskey = g.call(K + 'EqualEqual_NameName', 3000, 900, B='Key'); g.link(mode, 'Mode', iskey, 'A')
    choosemesh = g.branch(3600, -300); g.link(iskey, 'ReturnValue', choosemesh, 'Condition')
    toolmesh = get(g, 'ToolMesh', 3600, 600)
    keymesh = get(g, 'ToolKeyMesh', 3900, 600); drivermesh = get(g, 'ToolDriverMesh', 3900, 900)
    showkey = g.call('/Script/Engine.StaticMeshComponent:SetStaticMesh', 3900, -300)
    showdriver = g.call('/Script/Engine.StaticMeshComponent:SetStaticMesh', 3900, -600)
    for node, value, pin in ((showkey, keymesh, 'ToolKeyMesh'), (showdriver, drivermesh, 'ToolDriverMesh')):
        g.link(toolmesh, 'ToolMesh', node, 'self'); g.link(value, pin, node, 'NewMesh')
    transform = g.call(K + 'SelectTransform', 4200, 900)
    keytransform, drivertransform = get(g, 'ToolKeyTransform', 3900, 1200), get(g, 'ToolDriverTransform', 3900, 1500)
    g.link(keytransform, 'ToolKeyTransform', transform, 'A'); g.link(drivertransform, 'ToolDriverTransform', transform, 'B')
    g.link(iskey, 'ReturnValue', transform, 'bPickA')
    fit = g.call(SC + 'K2_SetRelativeTransform', 4200, -300)
    g.link(toolmesh, 'ToolMesh', fit, 'self'); g.link(transform, 'ReturnValue', fit, 'NewTransform')
    visible = g.call(SC + 'SetVisibility', 4500, -300, bNewVisibility=True); g.link(toolmesh, 'ToolMesh', visible, 'self')
    show = own(g, 'SetDoorToolPresentation', 3600, 0, Enabled=True)
    started = get(g, 'bToolActive', 3600, 1600)
    stillactive = g.branch(3900, -900); g.link(started, 'bToolActive', stillactive, 'Condition')
    refreshnode = own(g, 'RefreshDoorTool', 3900, 0)
    b = brk(g, e, 'Row', 3300, 1000)
    # Both tasks happen at this low lock. The authored settled kneel keeps the grip
    # reachable without stretching a standing arm down through the door hardware.
    load = g.call(KS + 'LoadAsset_Blocking', 4200, 0,
        Asset='/Game/FoA/Characters/Player/Montages/AM_FoA_KneelScrewdriver.AM_FoA_KneelScrewdriver')
    cast = g.node(palette(g, 'CastToAnimMontage'), 4500, 0); g.link(load, 'ReturnValue', cast, 'Object')
    montage = setv(g, 'ToolMontage', 4800, 0, source=result(g, cast, 'AsAnimMontage'))
    play = g.call('/Script/Engine.Character:PlayAnimMontage', 5100, 0)
    g.link(pawn, 'ReturnValue', play, 'self'); g.link(cast, 'AsAnimMontage', play, 'AnimMontage')
    now = g.call(KS + 'GetObjectName', 4800, 700); g.link(cast, 'AsAnimMontage', now, 'Object')
    name = g.call('/Script/Engine.KismetStringLibrary:Conv_StringToName', 5100, 700); g.link(now, 'ReturnValue', name, 'InString')
    times = get(g, 'ToolContactTimes', 5100, 1000)
    contacttime = g.call('/Script/Engine.BlueprintMapLibrary:Map_Find', 5400, 700)
    g.link(times, 'ToolContactTimes', contacttime, 'TargetMap'); g.link(name, 'ReturnValue', contacttime, 'Key')
    timer = g.call(KS + 'K2_SetTimer', 5700, 0, FunctionName='HoldDoorToolPose', bLooping=False)
    g.link(contacttime, 'Value', timer, 'Time')
    step = g.call(KS + 'K2_SetTimer', 6000, 0, FunctionName='StepDoorTool', Time=1 / 30, bLooping=True)
    cancel = own(g, 'CancelDoorTool', 4800, -300); g.link(cast, 'CastFailed', cancel, 'execute')
    g.exec_chain(e, row, setmode, setpc, setpawn, cache, active, ready, angle, inputangle, index, last, choosemesh, showkey)
    g.link(choosemesh, 'else', showdriver, 'execute'); g.exec_chain(showkey, fit); g.exec_chain(showdriver, fit)
    g.exec_chain(fit, visible, show, stillactive, refreshnode, load, cast, montage, play, timer, step)
    block(g, 'Settle the hand first')

    g, e = fn('HoldDoorToolPose')
    active = get(g, 'bToolActive'); guard = g.branch(300, 0)
    g.link(active, 'bToolActive', guard, 'Condition'); g.exec_chain(e, guard)
    pawn = get(g, 'ToolPlayer', 300, 400)
    mesh = g.get('Mesh', 600, 400, class_path='/Script/Engine.Character'); g.link(pawn, 'ToolPlayer', mesh, 'self')
    anim = g.call('/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 900, 400); g.link(mesh, 'Mesh', anim, 'self')
    montage = get(g, 'ToolMontage', 900, 650)
    pause = g.call('/Script/Engine.AnimInstance:Montage_Pause', 1200, 0)
    g.link(anim, 'ReturnValue', pause, 'self'); g.link(montage, 'ToolMontage', pause, 'Montage')
    ready = setv(g, 'bToolReady', 1500, 0, True)
    contact = own(g, 'RefreshDoorTool', 1800, 0)
    wait = setv(g, 'bToolReady', 2100, 0, False)
    settled = g.call(KS + 'K2_SetTimer', 2400, 0, FunctionName='MarkDoorToolReady', Time=0.75, bLooping=False)
    g.exec_chain(guard, pause, ready, contact, wait, settled)
    block(g, 'Settle the actual hand before accepting a turn')

    g, e = fn('MarkDoorToolReady')
    active = get(g, 'bToolActive'); guard = g.branch(300, 0)
    g.link(active, 'bToolActive', guard, 'Condition'); g.exec_chain(e, guard)
    ready = setv(g, 'bToolReady', 600, 0, True)
    refreshnode = own(g, 'RefreshDoorTool', 900, 0)
    g.exec_chain(guard, ready, refreshnode)
    block(g, 'The grip is now seated'); compile_save(DOOR)


def presentation():
    g, e = fn('SetDoorToolPresentation')
    pc, pawn = get(g, 'ToolController', 0, 300), get(g, 'ToolPlayer', 0, 500)
    tasklight = get(g, 'ToolTaskLight', 0, 750)
    lighting = g.call(SC + 'SetVisibility', 0, 0)
    g.link(tasklight, 'ToolTaskLight', lighting, 'self'); g.link(e, 'Enabled', lighting, 'bNewVisibility')
    choose = g.branch(300, 0); g.link(e, 'Enabled', choose, 'Condition'); g.exec_chain(e, lighting, choose)
    cursor = g.get('bShowMouseCursor', 300, 400, class_path='/Script/Engine.PlayerController')
    g.link(pc, 'ToolController', cursor, 'self')
    savecursor = setv(g, 'bToolPreviousCursor', 600, 0, source=(cursor, 'bShowMouseCursor'))
    control = g.call('/Script/Engine.Controller:GetControlRotation', 300, 650); g.link(pc, 'ToolController', control, 'self')
    savecontrol = setv(g, 'ToolPreviousControl', 900, 0, source=result(g, control))
    interactor = g.call(INTERACT + ':GetInteractor', 600, 900)
    lookmode = g.get('bLookMode', 900, 900, class_path=INTERACTOR); g.link(interactor, 'Interactor', lookmode, 'self')
    cachelook = setv(g, 'bToolPreviousLookMode', 1100, -250, source=(lookmode, 'bLookMode'))
    cast = g.node(palette(g, 'CastToBP_FoAPlayer'), 1200, 0); g.link(pawn, 'ToolPlayer', cast, 'Object')
    clear = g.call(PLAYER + ':EndInteraction', 1500, 0); g.link(cast, 'AsBP_FoAPlayer', clear, 'self')
    cine = g.call(PLAYER + ':SetCinematic', 1800, 0, bEnable=True); g.link(cast, 'AsBP_FoAPlayer', cine, 'self')
    # The door owns one movement and one look hold, independently of UI/pause and montage timers.
    lockmove = g.call('/Script/Engine.Controller:SetIgnoreMoveInput', 2100, 0, bNewMoveInput=True)
    locklook = g.call('/Script/Engine.Controller:SetIgnoreLookInput', 2400, 0, bNewLookInput=True)
    g.link(pc, 'ToolController', lockmove, 'self'); g.link(pc, 'ToolController', locklook, 'self')
    ownlocks = setv(g, 'bToolOwnsLocks', 2700, 0, True)
    game = g.call('/Script/UMG.WidgetBlueprintLibrary:SetInputMode_GameOnly', 3000, 0)
    g.link(pc, 'ToolController', game, 'PlayerController')
    hidecursor = g.call(PC + 'SetShowMouseCursor', 3300, 0, bShowMouseCursor=False); g.link(pc, 'ToolController', hidecursor, 'self')
    actortransform = g.call('/Script/Engine.Actor:GetTransform', 3000, 600)
    stand = g.call(K + 'MakeVector', 3300, 650, X=-50.0, Y=-84.0, Z=92.2)
    toolmode = get(g, 'ToolMode', 2700, 1250)
    driver = calc(g, 'EqualEqual_NameName', 3000, 1250, (toolmode, 'ToolMode'), B='Screwdriver')
    # Actual Teen arm sample: 128.26-degree folded elbow at X=-50. A 25.90cm
    # setback targets 60-degree flex while the existing hand solver holds the screw.
    setback = g.call(K + 'SelectFloat', 3300, 1250, A=-75.902385, B=-50.0)
    g.link(driver, 'ReturnValue', setback, 'bPickA'); g.link(setback, 'ReturnValue', stand, 'X')
    position = g.call(K + 'TransformLocation', 3600, 600)
    g.link(actortransform, 'ReturnValue', position, 'T'); g.link(stand, 'ReturnValue', position, 'Location')
    target = get(g, 'ToolContact', 3300, 1050)
    contact = g.call(SC + 'K2_GetComponentLocation', 3600, 1000); g.link(target, 'ToolContact', contact, 'self')
    look = g.call(K + 'FindLookAtRotation', 3900, 600)
    g.link(position, 'ReturnValue', look, 'Start'); g.link(contact, 'ReturnValue', look, 'Target')
    breakrot = g.call(K + 'BreakRotator', 4200, 600); g.link(look, 'ReturnValue', breakrot, 'InRot')
    face = g.call(K + 'MakeRotator', 4500, 600); g.link(breakrot, 'Yaw', face, 'Yaw')
    teleport = g.call('/Script/Engine.Actor:K2_TeleportTo', 4800, 0); g.link(pawn, 'ToolPlayer', teleport, 'self')
    g.link(position, 'ReturnValue', teleport, 'DestLocation'); g.link(face, 'ReturnValue', teleport, 'DestRotation')
    reached = g.branch(5100, 0); g.link(teleport, 'ReturnValue', reached, 'Condition')
    view = g.call(PC + 'SetViewTargetWithBlend', 5400, 0, BlendTime=0.35)
    g.link(pc, 'ToolController', view, 'self')
    selfnode = g.node(palette(g, 'Get a reference to self'), 5100, 600)
    out = next(str(PIN.get_pin_name(p)) for p in BEL.list_output_pins(selfnode)); g.link(selfnode, out, view, 'NewViewTarget')
    cancel = own(g, 'CancelDoorTool', 5400, -300); g.link(reached, 'else', cancel, 'execute')
    camera = get(g, 'ToolCamera', 4500, 1550)
    frame_pos = g.call(K + 'SelectVector', 4800, 1550, A='-48,-144,108', B='-30,-144,102')
    frame_aim = g.call(K + 'SelectVector', 4800, 1800, A='-12,-84,91', B='-7,-84,88')
    frame_fov = g.call(K + 'SelectFloat', 4800, 2050, A=44.0, B=36.0)
    for selected in (frame_pos, frame_aim, frame_fov):g.link(driver, 'ReturnValue', selected, 'bPickA')
    frame_rot = g.call(K + 'FindLookAtRotation', 5100, 1800)
    g.link(frame_pos, 'ReturnValue', frame_rot, 'Start');g.link(frame_aim, 'ReturnValue', frame_rot, 'Target')
    frame = g.call(SC + 'K2_SetRelativeLocationAndRotation', 5400, 1550, bSweep=False, bTeleport=True)
    g.link(camera, 'ToolCamera', frame, 'self');g.link(frame_pos, 'ReturnValue', frame, 'NewLocation');g.link(frame_rot, 'ReturnValue', frame, 'NewRotation')
    lens = g.call('/Script/Engine.CameraComponent:SetFieldOfView', 5700, 1550)
    g.link(camera, 'ToolCamera', lens, 'self');g.link(frame_fov, 'ReturnValue', lens, 'InFieldOfView')
    g.exec_chain(choose, savecursor, savecontrol, cachelook, cast, clear, cine, lockmove, locklook, ownlocks, game, hidecursor, teleport, reached, frame, lens, view)
    # Release exactly this session's counters; repeated cancel/reset is harmless.
    ownvar = get(g, 'bToolOwnsLocks', 300, 1600)
    held = g.branch(600, 1400); g.link(ownvar, 'bToolOwnsLocks', held, 'Condition'); g.link(choose, 'else', held, 'execute')
    unlockmove = g.call('/Script/Engine.Controller:SetIgnoreMoveInput', 900, 1400, bNewMoveInput=False)
    unlocklook = g.call('/Script/Engine.Controller:SetIgnoreLookInput', 1200, 1400, bNewLookInput=False)
    g.link(pc, 'ToolController', unlockmove, 'self'); g.link(pc, 'ToolController', unlocklook, 'self')
    unown = setv(g, 'bToolOwnsLocks', 1500, 1400, False)
    previous = get(g, 'ToolPreviousView', 1500, 1900)
    restoreview = g.call(PC + 'SetViewTargetWithBlend', 1800, 1400, BlendTime=0.3)
    g.link(pc, 'ToolController', restoreview, 'self'); g.link(previous, 'ToolPreviousView', restoreview, 'NewViewTarget')
    prevrot = get(g, 'ToolPreviousControl', 1800, 1900)
    restorecontrol = g.call('/Script/Engine.Controller:SetControlRotation', 2100, 1400)
    g.link(pc, 'ToolController', restorecontrol, 'self'); g.link(prevrot, 'ToolPreviousControl', restorecontrol, 'NewRotation')
    previouscursor = get(g, 'bToolPreviousCursor', 2100, 1900)
    restorecursor = g.call(PC + 'SetShowMouseCursor', 2400, 1400)
    g.link(pc, 'ToolController', restorecursor, 'self'); g.link(previouscursor, 'bToolPreviousCursor', restorecursor, 'bShowMouseCursor')
    asplayer = g.node(palette(g, 'CastToBP_FoAPlayer'), 2700, 1400); g.link(pawn, 'ToolPlayer', asplayer, 'Object')
    uncine = g.call(PLAYER + ':SetCinematic', 3000, 1400, bEnable=False); g.link(asplayer, 'AsBP_FoAPlayer', uncine, 'self')
    savedlook = get(g, 'bToolPreviousLookMode', 2700, 2100)
    restorelook = g.set('bLookMode', 3000, 1800, class_path=INTERACTOR)
    g.link(interactor, 'Interactor', restorelook, 'self'); g.link(savedlook, 'bToolPreviousLookMode', restorelook, 'bLookMode')
    g.exec_chain(held, unlockmove, unlocklook, unown, restoreview, restorecontrol, restorecursor, asplayer, restorelook, uncine)
    block(g, 'Own and restore the interaction'); compile_save(DOOR)


def finish_and_cancel():
    g, e = fn('DoorRowWithoutMontage')
    b = brk(g, e, 'Row')
    make = g.node(palette(g, 'Make', 'S_Interaction'), 500, 300)
    for p in BEL.list_input_pins(make):
        name = str(PIN.get_pin_name(p)).split('_')[0]
        if name != 'Montage':
            g.link(b, field(b, name), make, str(PIN.get_pin_name(p)))
    ret = g.at(result_node(g), 900, 0); g.exec_chain(e, ret)
    output = next(str(PIN.get_pin_name(p)) for p in BEL.list_output_pins(make)); g.link(make, output, ret, 'Result')
    block(g, 'The montage already played')

    g, e = fn('FinishDoorTool')
    active = get(g, 'bToolActive'); guard = g.branch(300, 0); g.link(active, 'bToolActive', guard, 'Condition'); g.exec_chain(e, guard)
    stop = g.call(KS + 'K2_ClearTimer', 600, 0, FunctionName='StepDoorTool')
    off = setv(g, 'bToolActive', 900, 0, False)
    commitflag = setv(g, 'bToolCommitting', 1200, 0, True)
    cached = get(g, 'ToolRow', 1200, 600)
    strip = own(g, 'DoorRowWithoutMontage', 1500, 600); g.link(cached, 'ToolRow', strip, 'Row')
    apply = own(g, 'ApplyRow', 1800, 0); g.link(strip, 'Result', apply, 'Row')
    committed = setv(g, 'bToolCommitting', 2100, 0, False)
    releasing = setv(g, 'bToolReleasing', 2400, 0, True)
    pawn = get(g, 'ToolPlayer', 2100, 800)
    mesh = g.get('Mesh', 2400, 800, class_path='/Script/Engine.Character'); g.link(pawn, 'ToolPlayer', mesh, 'self')
    anim = g.call('/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 2700, 800); g.link(mesh, 'Mesh', anim, 'self')
    montage = get(g, 'ToolMontage', 2700, 1050)
    name = g.call(KS + 'GetObjectName', 3000, 1050); g.link(montage, 'ToolMontage', name, 'Object')
    asname = g.call('/Script/Engine.KismetStringLibrary:Conv_StringToName', 3300, 1050); g.link(name, 'ReturnValue', asname, 'InString')
    times = get(g, 'ToolReleaseTimes', 3300, 1450)
    releaseat = g.call('/Script/Engine.BlueprintMapLibrary:Map_Find', 3600, 1050)
    g.link(times, 'ToolReleaseTimes', releaseat, 'TargetMap'); g.link(asname, 'ReturnValue', releaseat, 'Key')
    seek = g.call('/Script/Engine.AnimInstance:Montage_SetPosition', 3900, 0)
    g.link(anim, 'ReturnValue', seek, 'self'); g.link(montage, 'ToolMontage', seek, 'Montage'); g.link(releaseat, 'Value', seek, 'NewPosition')
    resume = g.call('/Script/Engine.AnimInstance:Montage_Resume', 4200, 0)
    g.link(anim, 'ReturnValue', resume, 'self'); g.link(montage, 'ToolMontage', resume, 'Montage')
    restore = g.call(KS + 'K2_SetTimer', 4500, 0, FunctionName='RestoreDoorTool', Time=1.2, bLooping=False)
    g.exec_chain(guard, stop, off)
    player_bp = unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
    if 'SetToolHandTarget' in [str(n) for n in BEL.list_graph_names(player_bp)]:
        releasecast = g.node(palette(g, 'CastToBP_FoAPlayer'), 900, -350)
        g.link(pawn, 'ToolPlayer', releasecast, 'Object')
        ungrip = g.call(PLAYER + ':SetToolHandTarget', 1200, -350, Weight=0.0)
        g.link(releasecast, 'AsBP_FoAPlayer', ungrip, 'self')
        g.exec_chain(off, releasecast, ungrip, commitflag)
        g.link(releasecast, 'CastFailed', commitflag, 'execute')
    else:
        g.exec_chain(off, commitflag)
    g.exec_chain(commitflag, apply, committed, releasing, seek, resume, restore)
    block(g, 'Finish before spending the item')

    g, e = fn('RestoreDoorTool')
    last = e
    for i, function in enumerate(('StepDoorTool', 'HoldDoorToolPose', 'RestoreDoorTool', 'MarkDoorToolReady')):
        clear = g.call(KS + 'K2_ClearTimer', 300 + i * 300, 0, FunctionName=function)
        g.exec_chain(last, clear); last = clear
    for i, var in enumerate(('bToolActive', 'bToolReady', 'bToolReleasing')):
        off = setv(g, var, 1200 + i * 300, 0, False); g.exec_chain(last, off); last = off
    hide = g.call(SC + 'SetVisibility', 2100, 0, bNewVisibility=False)
    mesh = get(g, 'ToolMesh', 1800, 600); g.link(mesh, 'ToolMesh', hide, 'self')
    restore = own(g, 'SetDoorToolPresentation', 2400, 0, Enabled=False)
    g.exec_chain(last, hide, restore)
    last = restore
    state = get(g, 'State', 2100, 900)
    locked = calc(g, 'EqualEqual_NameName', 2400, 900, (state, 'State'), B='Locked')
    jammed = calc(g, 'EqualEqual_NameName', 2400, 1150, (state, 'State'), B='KeyJammed')
    showplate = calc(g, 'BooleanOR', 2700, 900, result(g, locked), result(g, jammed))
    for i, name in enumerate(('ToolPlate', 'ToolScrew0', 'ToolScrew1', 'ToolScrew2', 'ToolScrew3', 'ToolKeyhole')):
        part = get(g, name, 2700 + i * 300, 1500)
        show = g.call(SC + 'SetVisibility', 2700 + i * 300, 0)
        g.link(part, name, show, 'self'); g.link(showplate, 'ReturnValue', show, 'bNewVisibility')
        g.exec_chain(last, show); last = show
    player_bp = unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
    if 'SetToolHandTarget' in [str(n) for n in BEL.list_graph_names(player_bp)]:
        pawn = get(g, 'ToolPlayer', 4200, 800)
        cast = g.node(palette(g, 'CastToBP_FoAPlayer'), 4200, 0); g.link(pawn, 'ToolPlayer', cast, 'Object')
        clear = g.call(PLAYER + ':SetToolHandTarget', 4500, 0, Weight=0.0)
        g.link(cast, 'AsBP_FoAPlayer', clear, 'self'); g.exec_chain(last, cast, clear); last = clear
    front = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
    fe = g.call(GS + 'GetActorOfClass', 4800, 0, ActorClass=front)
    widget = g.get('HUD', 4800, 600, class_path=front); g.link(fe, 'ReturnValue', widget, 'self')
    hudcast = g.node(palette(g, 'CastToWBP_HUD'), 5100, -300); g.link(widget, 'HUD', hudcast, 'Object')
    clearstatus = g.call('/Game/FoA/UI/Game/WBP_HUD.WBP_HUD_C:HideToolStatus', 5100, 0)
    g.link(hudcast, 'AsWBP_HUD', clearstatus, 'self'); g.exec_chain(last, fe, hudcast, clearstatus)
    block(g, 'Give the controls back')

    g, e = fn('CancelDoorTool')
    active = get(g, 'bToolActive'); releasing = get(g, 'bToolReleasing', 0, 400)
    owned = calc(g, 'BooleanOR', 300, 300, (active, 'bToolActive'), (releasing, 'bToolReleasing'))
    guard = g.branch(600, 0); g.link(owned, 'ReturnValue', guard, 'Condition'); g.exec_chain(e, guard)
    pawn = get(g, 'ToolPlayer', 600, 500); montage = get(g, 'ToolMontage', 600, 750)
    stop = g.call('/Script/Engine.Character:StopAnimMontage', 900, 0)
    g.link(pawn, 'ToolPlayer', stop, 'self'); g.link(montage, 'ToolMontage', stop, 'AnimMontage')
    restore = own(g, 'RestoreDoorTool', 1200, 0); g.exec_chain(guard, stop, restore)
    block(g, 'Cancel without a transaction'); compile_save(DOOR)


def wire():
    bp = unreal.load_asset(DOOR)
    for name in SIGNATURES:
        g = Graph(DOOR, name)
        assert len([n for n in g.ed.list_all_nodes() if n.get_class().get_name() != 'EdGraphNode_Comment']) > 2, name
    # Keep the actual CallParentFunction emitted by the engine; normal rows retain parent behavior.
    g = Graph(DOOR, 'ApplyRow')
    e = entry_node(g)
    parent = list(g.ed.list_nodes_of_class(unreal.K2Node_CallParentFunction))
    assert len(parent) == 1
    parent = g.at(parent[0], 2100, -300)
    for c in list(g.ed.list_comment_nodes()):
        g.ed.remove_comment_node(c)
    for n in list(g.ed.list_all_nodes()):
        if n not in (e, parent):
            g.ed.remove_nodes([n])
    PIN.break_pin_links(BEL.find_then_pin(e))
    committing = get(g, 'bToolCommitting', 0, 250)
    transaction = g.branch(300, 0); g.link(committing, 'bToolCommitting', transaction, 'Condition')
    g.exec_chain(e, transaction); g.link(transaction, 'then', parent, 'execute')
    mode = own(g, 'GetDoorToolMode', 300, 400); g.link(e, 'Row', mode, 'Row')
    tool = calc(g, 'NotEqual_NameName', 600, 400, result(g, mode, 'Mode'), B='None')
    classify = g.branch(900, 0); g.link(tool, 'ReturnValue', classify, 'Condition')
    g.link(classify, 'else', parent, 'execute')
    active = get(g, 'bToolActive', 900, 400)
    # The tool owns the action until its release timer restores camera/input.
    # Reject all new rows during that period; only the tool's own commit bypasses it.
    releasing = get(g, 'bToolReleasing', 900, 1250)
    busy = calc(g, 'BooleanOR', 1200, 1150, (active, 'bToolActive'), (releasing, 'bToolReleasing'))
    busyguard = g.branch(1500, 1000); g.link(busy, 'ReturnValue', busyguard, 'Condition')
    g.link(transaction, 'else', busyguard, 'execute'); g.link(busyguard, 'else', classify, 'execute')
    free = calc(g, 'Not_PreBool', 1200, 400, (active, 'bToolActive'))
    gate = g.call(INTERACT + ':CanApplyProgressionRow', 900, 650); g.link(e, 'Row', gate, 'Row')
    allowed = calc(g, 'BooleanAND', 1500, 400, result(g, free), result(g, gate, 'Allowed'))
    permit = g.branch(1800, 0); g.link(allowed, 'ReturnValue', permit, 'Condition'); g.exec_chain(classify, permit)
    begin = own(g, 'BeginDoorTool', 2100, 0); g.link(e, 'Row', begin, 'Row'); g.exec_chain(permit, begin)
    block(g, 'Let the player do it')

    # Base ResetForNewDay now calls this virtual function before its existing wardrobe reset hooks.
    g = Graph(DOOR, 'CancelPendingRow'); e = entry_node(g)
    parent = list(g.ed.list_nodes_of_class(unreal.K2Node_CallParentFunction)); assert len(parent) == 1
    parent = g.at(parent[0], 600, 0)
    for c in list(g.ed.list_comment_nodes()):
        g.ed.remove_comment_node(c)
    for n in list(g.ed.list_all_nodes()):
        if n not in (e, parent):
            g.ed.remove_nodes([n])
    PIN.break_pin_links(BEL.find_then_pin(e))
    cancel = own(g, 'CancelDoorTool', 300, 0); g.exec_chain(e, cancel, parent)
    # Base reset passes false before restoring State. Recreate the physical plate even
    # when a completed session has no active tool/counters left to cancel.
    reset = g.branch(900, 0); g.link(e, 'bRestoreScan', reset, 'Condition'); g.exec_chain(parent, reset)
    last = reset
    for i, name in enumerate(('ToolPlate', 'ToolScrew0', 'ToolScrew1', 'ToolScrew2', 'ToolScrew3', 'ToolKeyhole')):
        part = get(g, name, 1200 + i * 300, 500)
        show = g.call(SC + 'SetVisibility', 1200 + i * 300, 0, bNewVisibility=True)
        g.link(part, name, show, 'self')
        if last == reset:
            g.link(reset, 'else', show, 'execute')
        else:
            g.exec_chain(last, show)
        last = show
    block(g, 'Reset also cancels the tool'); compile_save(DOOR)


def defaults():
    # Data-only after native compilation. Same vertices/materials as the actual pickups, normalized around their tips.
    bp = unreal.load_asset(DOOR); cdo = unreal.get_default_object(bp.generated_class())
    for meshvar, transformvar, length in (('ToolKeyMesh', 'ToolKeyTransform', 7.5), ('ToolDriverMesh', 'ToolDriverTransform', 23.0)):
        mesh = cdo.get_editor_property(meshvar); assert mesh, meshvar
        box = mesh.get_bounding_box()
        lo, hi = box.min, box.max
        size = [hi.x - lo.x, hi.y - lo.y, hi.z - lo.z]
        axis = max(range(3), key=lambda i: size[i]); assert size[axis] > 0.01
        basis = [unreal.Vector(1, 0, 0), unreal.Vector(0, 1, 0), unreal.Vector(0, 0, 1)][axis]
        q = unreal.MathLibrary.make_rot_from_x(basis).quaternion()
        inverse = unreal.Quat(-q.x, -q.y, -q.z, q.w)
        scale = length / size[axis]
        center = (lo + hi) * 0.5
        tip = center + basis * (size[axis] * 0.5)
        transform = unreal.Transform(location=inverse.rotate_vector(tip * scale) * -1,
                                     rotation=inverse.rotator(), scale=unreal.Vector(scale, scale, scale))
        cdo.set_editor_property(transformvar, transform)
        print('TOOL_NORMALIZED', mesh.get_path_name(), size, axis, transform)
    contacts, releases = {}, {}
    for name, hold, release in (('AM_FoA_TryLockedHandle', 'Rattle', None),
                                ('AM_FoA_KneelScrewdriver', 'KneelDown', 'WorkDone')):
        montage = unreal.load_asset('/Game/FoA/Characters/Player/Montages/' + name); assert montage, name
        for event in unreal.AnimationLibrary.get_animation_notify_events(montage):
            notify = event.get_editor_property('notify')
            if isinstance(notify,unreal.AnimNotify_PlayMontageNotify):
                n = str(notify.get_editor_property('notify_name'))
                t = unreal.AnimationLibrary.get_anim_notify_event_trigger_time(event)
                if n == hold:
                    contacts[unreal.Name(name)] = t
                if n == release:
                    releases[unreal.Name(name)] = t
        if release is None:
            releases[unreal.Name(name)] = max(0.0, montage.get_play_length() - 1.0)
    assert len(contacts) == 2 and all(t > 0 for t in contacts.values()) and len(releases) == 2
    cdo.set_editor_property('ToolContactTimes', contacts); cdo.set_editor_property('ToolReleaseTimes', releases)
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    print('Door pose/tip defaults saved; native visual fit still requires verification')


if phase == 'components':
    components()
elif phase == 'motion':
    mode_and_advance()
elif phase == 'input':
    input_step()
elif phase == 'refresh':
    refresh()
elif phase == 'start':
    start_and_hold()
elif phase == 'presentation':
    presentation()
elif phase == 'finish':
    finish_and_cancel()
elif phase == 'wire':
    wire()
elif phase == 'defaults':
    defaults()
else:
    raise ValueError('Door phase still awaiting presentation/transaction wiring: ' + phase)
