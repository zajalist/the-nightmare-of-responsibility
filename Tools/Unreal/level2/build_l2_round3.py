"""Level 2, round 3 (level2 lane, 2026-11-18): the shifts react, the interview breathes, a hand the size of a building.

Shifts: every finished order eats into the stop's Lux3D sand object (the unpaid bills at Queen Market, the melting
  calendar at Night Dispatch, the necktie serpent at Northline) until the fourth order crumbles it; a mistake thickens it
  again with a sand burst and a small camera knock. A dry line from him forms out of sand above the board each time
  (WBP_SandLine in the stop overlay, StopLine).
Interview: a straight answer thins the room's sand objects and shakes grains off his double's hands; an inflated one
  thickens them, grows them 10 %, knocks the camera, pushes the lens in 2 deg and brings the double 8 cm closer.
  Retrying the interview resets the room.
Queen Street: a black-sand hand (Lux3D 4725644, 8 m) rises out of the road ahead and points down the street toward
  Queen Market; it crumbles with the crow as he gets into the car.
  python -B build_l2_round3.py selftest | card | declare | graphs | hooks
  python Tools/Unreal/ue_remote.py Tools/Unreal/level2/build_l2_round3.py FOA_R3_STEP=templates   (FOA_AREAS=asset:<Journey>)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = '/Game/FoA/Level2/Journey'
JOURNEY = ROOT + '/BP_L2Journey'
STOPSET = ROOT + '/BP_L2StopSet'
CARD = ROOT + '/WBP_L2ShiftTimeCard'
SANDLINE_C = '/Game/FoA/UI/Widgets/Common/WBP_SandLine.WBP_SandLine_C'
FONT = '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
SAND = '/Game/FoA/VFX/Sand/BPL_SandFX.BPL_SandFX_C:SpawnSandBurst'
SHAKE = '/Game/FoA/VFX/CS_SandHit.CS_SandHit_C'
HAND = (ROOT + '/Sand/SM_SandHand/SM_SandHand', ROOT + '/Sand/MI_SandHand')

# Lines he says as the shift goes (stop x order): dry, short, his voice. Accepted by order 1-4, missed by mistake 1-2.
ACCEPT = (('One crate. The bills get shorter.', 'Two. I could get used to this.', 'Three. My back has opinions.',
           'Four. The stack is gone.'),
          ('Bay three. Gone.', 'Another one out. The calendar drips.', 'I am good at bays now.',
           'Last parcel. The night is still young.'),
          ('Count matches. The tie loosens.', 'Two for two.', 'The shelf and I agree.', 'All posted. It is just a tie now.'))
MISSED = (('That was oat milk. Nobody ordered oat milk.', 'The crate disagrees.'),
          ('Wrong bay. The van left anyway.', 'That parcel is in Mississauga now.'),
          ('The shelf disagrees. Loudly.', 'I counted the same box twice.'))
SHIFT_STEP, SHIFT_BACK = .22, .25
ROOM = {'SandBills': 3.4, 'SandCrow': 1., 'SandBriefcase': .9}  # build_l2_sand_set.OBJECTS base scales
HONEST, LOOM_SCALE, LOOM_FOV, LOOM_STEP, LOOM_MAX = .15, .1, 2., 8., 3
# forward, right, sink (cm), roll, yaw, scale. Upright, palm to him, leaning 25 deg toward Queen Market; on the left so
# it stands against the bright facades (the street centre above eye level is black sky: run_20261118_0327 street).
HAND_POSE = (1800., -700., -100., 15., 90., 13.)  # 7.7 m; whole hand in frame, finger up (run_20261118_0354 cropped it)


def thin(sand, cost):
    """The room's dissolve after an answer: straight answers thin it, inflated ones thicken it (graph's math)."""
    return min(.75, sand + HONEST) if cost == 0 else max(0., sand - cost * .008)


def selftest():
    from build_l2_sand_set import OBJECTS
    assert {k: v[3] for k, v in OBJECTS.items()} == ROOM, 'room base scales out of step with build_l2_sand_set'
    assert all(len(a) == 4 for a in ACCEPT) and all(len(m) == 2 for m in MISSED) and len(ACCEPT) == len(MISSED) == 3
    for line in (*sum(ACCEPT, ()), *sum(MISSED, ())):
        assert len(line) <= 48 and not any(c in line for c in '\u00b7\u2022|/\u2014\u2013'), line
    s = 0.
    for cost in (0, 0, 15, 0, 35, 0):
        s = thin(s, cost)
    assert 0 <= s <= .75 and thin(.7, 0) == .75 and thin(.1, 35) == 0
    assert [min(1., n * SHIFT_STEP) if n < 4 else 1. for n in range(1, 5)][-1] == 1.
    print('round 3 selftest ok; six-answer sample ends at', round(s, 2))


# ---- editor steps -------------------------------------------------------------------------------------------------
def card():
    from build_drive import call
    have = str(call('ui_query', path=CARD).get('matches') or call('ui_query', path=CARD))
    for name, anchor, y, size in (('Line_Stop', [.5, 0], 150, 34), ('Line_End', [.5, 1], -128, 40)):
        if name not in have:
            call('ui_build_tree', widget_blueprint_path=CARD, parent_widget_name='RootCanvas', tree=[{
                'class': SANDLINE_C, 'name': name,
                'slot_props': dict(anchors_min=anchor, anchors_max=anchor, alignment=[.5, .5], position=[0, y], size=[900, 60],
                                   z_order=4)}])
            call('ui_set_variable', widget_blueprint_path=CARD, widget_name=name, is_variable=True)
        call('ui_set_widget_properties', widget_blueprint_path=CARD, widget_name=name,
             slot_props=dict(anchors_min=anchor, anchors_max=anchor, alignment=[.5, .5], position=[0, y], auto_size=True),
             properties={'Scale': round(size * .09, 1), 'bLineFont': True, 'Visibility': 'Collapsed',  # Play shows it
                         'LineFont': {'FontObject': FONT, 'TypefaceFontName': 'SemiBold', 'Size': size}})
    call('ui_compile_widget', widget_blueprint_path=CARD)
    call('ui_save_widget', widget_blueprint_path=CARD)


def declare():
    import build_drive as b
    from build_drive import call
    info = call('blueprint_get_info', path=JOURNEY)
    have = {v['name'] for v in info['variables']}
    for name, kind, default in (('StopLine', 'object:' + b.cls(CARD), ''), ('ShiftSand', 'float', '0'),
                                ('InterviewSand', 'float', '0'), ('InterviewLoom', 'int', '0')):
        if name not in have:
            call('blueprint_add_variable', path=JOURNEY, variable_name=name, variable_type=kind, default_value=default,
                 category='Round 3', update_existing=True)
    if 'StreetGiant' not in {c['name'] for c in info.get('components', [])}:
        call('blueprint_add_component', path=JOURNEY, component_name='StreetGiant',
             component_class_path='/Script/Engine.StaticMeshComponent')
    for name, inputs in (('OpenStopLine', []), ('CloseStopLine', []), ('ShiftReact', [dict(name='Accepted', type='bool')]),
                         ('InterviewReact', [dict(name='Cost', type='int')]), ('ResetInterviewRoom', []),
                         ('CrumbleStreetSand', [])):
        if not b.h.call('blueprint_inspect_graph', {'path': JOURNEY, 'graph_name': name}).get('ok'):
            call('blueprint_add_function', path=JOURNEY, function_name=name, inputs=inputs)
    call('blueprint_compile', path=JOURNEY, save=True)


def templates():
    import unreal as u
    assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world(), 'PIE running'
    from free_drive_setup import templates as read
    bp, sds, lib, gathered, handles, comps = read(JOURNEY)
    root = next(h for n, h in handles.items() if n in ('DefaultSceneRoot', 'Root'))
    assert 'StreetGiant' in handles, 'declare first'
    sds.attach_subobject(root, handles['StreetGiant'])
    c = comps['StreetGiant']
    c.set_static_mesh(u.load_asset(HAND[0]))
    c.set_material(0, u.load_asset(HAND[1]))
    c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    for prop, value in (('cast_shadow', False), ('visible', False), ('generate_overlap_events', False),
                        ('absolute_location', True), ('absolute_rotation', True), ('absolute_scale', True),
                        ('can_character_step_up_on', u.CanBeCharacterBase.ECB_NO)):
        c.set_editor_property(prop, value)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    assert u.EditorAssetLibrary.save_loaded_asset(bp, False)
    print('round 3 templates: StreetGiant', c.get_editor_property('static_mesh').get_name())


def _guard(g, condition):
    br = g.branch(condition)
    g.side(br)
    return br


def graphs():
    import build_drive as b
    from build_drive import G, cls, GS, SL, SC
    PRIM = '/Script/Engine.PrimitiveComponent:'
    UW = '/Script/UMG.Widget:'
    CAM = '/Script/Engine.PlayerCameraManager:'

    def sand_event(g, comp, frm, seconds, to, delay=0.):
        start = g.f(GS + 'GetTimeSeconds') if not delay else g.math('Add_DoubleDouble', A=g.f(GS + 'GetTimeSeconds'), B=delay)
        g.do(PRIM + 'SetVectorParameterForCustomPrimitiveData', self=comp, ParameterName='SandEvent',
             Value=g.math('MakeVector4', X=frm, Y=start, Z=seconds, W=to))

    def shake(g, scale):
        g.do(CAM + 'StartCameraShake', self=g.f(GS + 'GetPlayerCameraManager', PlayerIndex=0), ShakeClass=SHAKE, Scale=scale)

    def burst(g, comp, up, scale):
        at = g.math('Add_VectorVector', A=g.f(SC + 'K2_GetComponentLocation', self=comp), B=g.math('MakeVector', X=0, Y=0, Z=up))
        g.do(SAND, Location=at, Scale=scale)

    def line(g, text, mood):
        g.do(SANDLINE_C + ':Play', self=g.getv('Line_Stop', g.getv('StopLine'), CARD), Line=text, Mood=mood, Hold=1.8)

    def pick_text(g, rows, index_var, offset):
        out = None
        for s, row in enumerate(rows):
            for i, text in enumerate(row):
                hit = g.math('BooleanAND', A=g.math('EqualEqual_IntInt', A=g.getv('Stop'), B=s),
                             B=g.math('EqualEqual_IntInt', A=g.getv(index_var), B=i + offset))
                out = text if out is None else g.math('SelectString', A=text, B=out, bPickA=hit)
        return g.f('/Script/Engine.KismetTextLibrary:Conv_StringToText', InString=out)

    # the stop overlay: the card widget with its black, title and clock collapsed; only the sand line shows
    g = G(JOURNEY, 'OpenStopLine')
    g.setv('ShiftSand', 0.)
    have = g.branch(g.f(SL + 'IsValid', Object=g.getv('StopLine')))
    g.side(have, False)
    widget = g.ref()
    g.node(widget, 'create_widget', 0, 0, class_path=cls(CARD))
    g.put(widget, 'OwningPlayer', g.f(GS + 'GetPlayerController', PlayerIndex=0))
    g.chain(g.tail, widget)
    g.tail = widget
    g.setv('StopLine', (widget, 'ReturnValue'))
    for name in ('TimeBlack', 'TimeTitle', 'TimeClock'):
        g.do(UW + 'SetVisibility', self=g.getv(name, g.getv('StopLine'), CARD), InVisibility='Collapsed')
    g.do('/Script/UMG.UserWidget:AddToViewport', self=g.getv('StopLine'), ZOrder=70)
    g.finish()

    g = G(JOURNEY, 'CloseStopLine')
    _guard(g, g.f(SL + 'IsValid', Object=g.getv('StopLine')))
    g.do(UW + 'RemoveFromParent', self=g.getv('StopLine'))
    g.setv('StopLine', '')
    g.finish()

    g = G(JOURNEY, 'ShiftReact')
    _guard(g, g.math('Less_IntInt', A=g.getv('Stop'), B=3))
    _guard(g, g.f(SL + 'IsValid', Object=g.getv('StopLine')))
    accepted = g.branch(g.arg('Accepted'))
    g.side(accepted)
    done = g.math('GreaterEqual_IntInt', A=g.getv('JobOrder'), B=4)
    target = g.math('SelectFloat', A=1., B=g.math('FMin', A=1., B=g.math('Multiply_DoubleDouble', A=g.math(
        'Conv_IntToDouble', InInt=g.getv('JobOrder')), B=SHIFT_STEP)), bPickA=done)
    sand_event(g, g.getv('StopSandA'), g.getv('ShiftSand'), .8, target)
    g.setv('ShiftSand', target)
    burst(g, g.getv('StopSandA'), 140., .5)
    line(g, pick_text(g, ACCEPT, 'JobOrder', 1), 3)
    g.side(accepted, False)
    back = g.math('FMax', A=0., B=g.math('Subtract_DoubleDouble', A=g.getv('ShiftSand'), B=SHIFT_BACK))
    sand_event(g, g.getv('StopSandA'), g.getv('ShiftSand'), .45, back)
    g.setv('ShiftSand', back)
    burst(g, g.getv('StopSandB'), 120., 1.)
    shake(g, .35)
    line(g, pick_text(g, MISSED, 'JobMistakes', 1), 1)
    g.finish()

    def room(g, sand_to, seconds, scale_mult):
        stop = g.getv('StopSet')
        for name, base in ROOM.items():
            comp = g.getv(name, stop, STOPSET)
            sand_event(g, comp, g.getv('InterviewSand'), seconds, sand_to)
            s = g.math('Multiply_DoubleDouble', A=base, B=scale_mult)
            g.do(SC + 'SetRelativeScale3D', self=g.getv(name, g.getv('StopSet'), STOPSET), NewScale3D=g.math('MakeVector', X=s, Y=s, Z=s))

    g = G(JOURNEY, 'InterviewReact')
    _guard(g, g.f(SL + 'IsValid', Object=g.getv('StopSet')))
    honest = g.branch(g.math('EqualEqual_IntInt', A=g.arg('Cost'), B=0))
    g.side(honest)
    clear = g.math('FMin', A=.75, B=g.math('Add_DoubleDouble', A=g.getv('InterviewSand'), B=HONEST))
    back = g.math('SelectFloat', A=-LOOM_STEP, B=0., bPickA=g.math('Greater_IntInt', A=g.getv('InterviewLoom'), B=0))
    g.do(SC + 'K2_AddWorldOffset', self=g.getv('InterviewBody', g.getv('StopSet'), STOPSET),
         DeltaLocation=g.math('MakeVector', X=back, Y=0, Z=0), bSweep=False, bTeleport=True)  # the double steps back
    g.setv('InterviewLoom', g.math('Max', A=0, B=g.math('Subtract_IntInt', A=g.getv('InterviewLoom'), B=1)))
    room(g, clear, .9, g.math('Add_DoubleDouble', A=1., B=g.math('Multiply_DoubleDouble', A=g.math(
        'Conv_IntToDouble', InInt=g.getv('InterviewLoom')), B=LOOM_SCALE)))
    g.setv('InterviewSand', clear)
    g.do('/Script/Engine.CameraComponent:SetFieldOfView', self=g.getv('StageCamera', g.getv('StopSet'), STOPSET),
         InFieldOfView=g.math('Subtract_DoubleDouble', A=58., B=g.math('Multiply_DoubleDouble', A=g.math(
             'Conv_IntToDouble', InInt=g.getv('InterviewLoom')), B=LOOM_FOV)))  # the lens eases back with him
    burst(g, g.getv('InterviewBody', g.getv('StopSet'), STOPSET), 95., .35)
    g.side(honest, False)
    thick = g.math('FMax', A=0., B=g.math('Subtract_DoubleDouble', A=g.getv('InterviewSand'), B=g.math(
        'Multiply_DoubleDouble', A=g.math('Conv_IntToDouble', InInt=g.arg('Cost')), B=.008)))
    closer = g.branch(g.math('Less_IntInt', A=g.getv('InterviewLoom'), B=LOOM_MAX))
    g.side(closer)
    g.do(SC + 'K2_AddWorldOffset', self=g.getv('InterviewBody', g.getv('StopSet'), STOPSET),
         DeltaLocation=f'{LOOM_STEP},0,0', bSweep=False, bTeleport=True)
    joined = g.setv('InterviewLoom', g.math('Min', A=LOOM_MAX, B=g.math('Add_IntInt', A=g.getv('InterviewLoom'), B=1)))
    g.link(closer, 'else', joined[0], 'execute')
    room(g, thick, .5, g.math('Add_DoubleDouble', A=1., B=g.math('Multiply_DoubleDouble', A=g.math(
        'Conv_IntToDouble', InInt=g.getv('InterviewLoom')), B=LOOM_SCALE)))
    g.setv('InterviewSand', thick)
    g.do('/Script/Engine.CameraComponent:SetFieldOfView', self=g.getv('StageCamera', g.getv('StopSet'), STOPSET),
         InFieldOfView=g.math('Subtract_DoubleDouble', A=58., B=g.math('Multiply_DoubleDouble', A=g.math(
             'Conv_IntToDouble', InInt=g.getv('InterviewLoom')), B=LOOM_FOV)))
    burst(g, g.getv('InterviewBody', g.getv('StopSet'), STOPSET), 130., 1.)
    shake(g, .45)
    g.finish()

    g = G(JOURNEY, 'ResetInterviewRoom')
    _guard(g, g.f(SL + 'IsValid', Object=g.getv('StopSet')))
    back = g.math('Multiply_DoubleDouble', A=g.math('Conv_IntToDouble', InInt=g.getv('InterviewLoom')), B=-LOOM_STEP)
    g.do(SC + 'K2_AddWorldOffset', self=g.getv('InterviewBody', g.getv('StopSet'), STOPSET),
         DeltaLocation=g.math('MakeVector', X=back, Y=0, Z=0), bSweep=False, bTeleport=True)
    room(g, 0., .6, 1.)
    g.setv('InterviewSand', 0.)
    g.setv('InterviewLoom', 0)
    g.do('/Script/Engine.CameraComponent:SetFieldOfView', self=g.getv('StageCamera', g.getv('StopSet'), STOPSET),
         InFieldOfView=58.)
    g.finish()

    g = G(JOURNEY, 'CrumbleStreetSand')
    for name in ('StopSandA', 'StreetGiant'):
        sand_event(g, g.getv(name), 0., 1.8, 1.)
    g.finish()


def hooks():
    """The shared builders call the new functions; rebuild their graphs (BeginJob, ClearJob, EnterCar, Accept/Miss,
    ApplyDialogueAnswer, StartFinale) and the street/stop sand graphs (hand)."""
    import build_job_hunt as jobs
    import build_journey as j
    import build_interview as ui
    import shift_minigames
    import build_l2_stop_sand as stops
    jobs.begin()
    jobs.clear()
    j.enter_car()
    shift_minigames.accept_round()
    shift_minigames.miss_round()
    ui.apply_answer()
    ui.start_interview(True)
    stops.graphs()


def run(step):
    if step == 'selftest':
        return selftest()
    import build_drive as b
    import editor_lock
    owner = 'level2'
    os.environ.update(FOA_AGENT=owner, HAYBA_AGENT_ID=owner)
    areas = [CARD] if step == 'card' else [JOURNEY]
    token = editor_lock.acquire(owner, wait_s=1500, ttl=300, areas=areas)
    os.environ['FOA_LEASE'] = token or editor_lock.hayba_leases(owner)[0][0]
    try:
        assert not b.call('editor_get_state')['pie_running'], 'PIE is running'
        dict(card=card, declare=declare, graphs=graphs, hooks=hooks)[step]()
    finally:
        editor_lock.release(owner)


if __name__ == '__main__':
    if os.environ.get('FOA_R3_STEP') == 'templates':
        sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
        templates()
    else:
        for name in sys.argv[1:]:
            print('== step', name, flush=True)
            run(name)
