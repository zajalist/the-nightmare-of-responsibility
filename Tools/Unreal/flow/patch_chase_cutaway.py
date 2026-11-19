"""The clothing chase cutaways as proper cinematics (QA B2, main 2026-11-10). The inspection camera (BP_BeatDirector's
TopDownCamera: the clue shots, the hanger toss, the escapes, the vase) is designed; four fixes:
  1. HUD: SetStoryHUDHidden(Hidden) caches BP_FoAFrontEnd.HUD's visibility once, hides it, and restores exactly that.
     TryClothingInspection hides it after PlayerCinematic(true); CancelClothingInspection restores it. The T9 hero shot
     (PayoffShot / PayoffShotCut) uses it too.
  2. Return: the inspection's end timer now runs ReturnClothingInspection (fade to black 0.2 s, held, then
     FinishClothingInspection), and FinishClothingInspection ends with BP_FoAPlayer.HandoffFadeUp: the same
     fade-hidden cut as ExitTopDown. A cancel during the dip fades the screen back up (bClothingReturnDip).
  3. The hanger kneel ends standing on the floor where he knelt, 40 cm back from the bed at (269.8, -55, 89), facing
     the shirt's first landing (yaw 188), instead of ClothingHangerHome (QA's run had started him on the bed, z 124).
     The full capsule fits there (Saved/StoryShots/toss_views.json).
  4. The toss's wide shot (TickClothingFlight) moves to (150, -40, 140) looking at (140, -80, 40): the landing end of
     the arc, with the kneeling body 68 deg off axis (outside the 70 deg view) and 1.4 m from the camera.
Hayba only; idempotent.  python Tools/Unreal/flow/patch_chase_cutaway.py"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
C = P + '.BP_BeatDirector_C'
FRONT = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'
GS, KS, K = '/Script/Engine.GameplayStatics:', '/Script/Engine.KismetSystemLibrary:', '/Script/Engine.KismetMathLibrary:'
W = '/Script/UMG.Widget:'
PCM = '/Script/Engine.PlayerCameraManager:StartCameraFade'
BLACK = '(R=0.0,G=0.0,B=0.0,A=1.0)'
DIP = 0.2
STAND = '(X=269.759,Y=-55.0,Z=89.0)'
STAND_YAW = 188.0
T7_STAND = '105,-110,89'  # holds a standing player with the wardrobe down (teleport-tested in PIE, t7_hanger.json)
LANDING0 = '110.7,-76.4,38.5'  # the toss lands the shirt here (clothing_chase_contract LANDINGS[0])
WIDE_VIEW, WIDE_FOCUS = '150,-40,140', '140,-80,40'  # the pins' own literal form
OLD_VIEW, OLD_FOCUS = ('160', '-270', '190'), ('190', '-100', '70')
os.environ['HAYBA_AGENT_ID'] = 'story'


def call(name, **args):
    r = h.call(name, args, owner='story', timeout=60)
    assert r.get('ok'), r
    d = r.get('data', {})
    assert d.get('ok', True), d
    return d


def has_graph(name):
    return h.call('blueprint_inspect_graph', {'path': P, 'graph_name': name}).get('ok')


def next_of(es, node, pin='then'):
    hits = [x for x in es if x['from_node'] == node and x['from_pin'] == pin]
    return hits[0] if hits else None


def default(n, pin):
    return next((p.get('default_value') or '' for p in n['pins'] if p['name'] == pin), '')


def hud_function():
    if not has_graph('SetStoryHUDHidden'):
        call('blueprint_add_function', path=P, function_name='SetStoryHUDHidden', inputs=[dict(name='Hidden', type='bool')])
    ns, es = inspect(P, 'SetStoryHUDHidden')
    if any(n['title'] == 'SetVisibility' for n in ns):
        e = find(ns, 'SetStoryHUDHidden')
        if next_of(es, e) is None:  # first build (2026-11-10) left the entry's exec unwired: the function never ran
            which = next(x['to_node'] for x in es if x['from_node'] == e and x['from_pin'] == 'Hidden')
            b = Batch(P, 'SetStoryHUDHidden')
            b.link(e, 'then', which, 'execute')
            b.run()
            return 'entry wired'
        return 'kept'
    e = find(ns, 'SetStoryHUDHidden')
    b = Batch(P, 'SetStoryHUDHidden')
    b.node('which', 'branch', 250, 0)
    b.link(e, 'then', 'which', 'execute')
    b.link(e, 'Hidden', 'which', 'Condition')
    # hide: once (a second hide must not cache the hidden state as the one to restore)
    b.get('was', 'bStoryHUDHidden', 450, -350)
    b.fn('notyet', K + 'Not_PreBool', 650, -350)
    b.link('was', 'bStoryHUDHidden', 'notyet', 'A')
    b.node('once', 'branch', 800, -200)
    b.link('notyet', 'ReturnValue', 'once', 'Condition')
    b.fn('fe', GS + 'GetActorOfClass', 1050, -200, ActorClass=FRONT)
    b.fn('fevalid', KS + 'IsValid', 1050, -400)
    b.link('fe', 'ReturnValue', 'fevalid', 'Object')
    b.node('feok', 'branch', 1300, -200)
    b.link('fevalid', 'ReturnValue', 'feok', 'Condition')
    b.get('hud', 'HUD', 1300, -450, FRONT)
    b.link('fe', 'ReturnValue', 'hud', 'self')
    b.fn('hudvalid', KS + 'IsValid', 1550, -450)
    b.link('hud', 'HUD', 'hudvalid', 'Object')
    b.node('hudok', 'branch', 1550, -200)
    b.link('hudvalid', 'ReturnValue', 'hudok', 'Condition')
    b.set('keep', 'StoryHUD', 1800, -200)
    b.link('hud', 'HUD', 'keep', 'StoryHUD')
    b.fn('vis', W + 'GetVisibility', 1800, -450)
    b.link('hud', 'HUD', 'vis', 'self')
    b.set('keepvis', 'StoryHUDVisibility', 2050, -200)
    b.link('vis', 'ReturnValue', 'keepvis', 'StoryHUDVisibility')
    b.fn('hide', W + 'SetVisibility', 2300, -200, InVisibility='Hidden')
    b.link('hud', 'HUD', 'hide', 'self')
    b.set('mark', 'bStoryHUDHidden', 2550, -200)
    b.pin('mark', 'bStoryHUDHidden', 'true')
    b.link('which', 'then', 'once', 'execute')
    b.link('once', 'then', 'fe', 'execute')
    b.chain('fe', 'feok')
    b.link('feok', 'then', 'hudok', 'execute')
    b.link('hudok', 'then', 'keep', 'execute')
    b.chain('keep', 'keepvis', 'hide', 'mark')
    # show: only what this function hid, back to exactly the cached visibility
    b.get('washidden', 'bStoryHUDHidden', 450, 350)
    b.node('ours', 'branch', 800, 250)
    b.link('washidden', 'bStoryHUDHidden', 'ours', 'Condition')
    b.set('unmark', 'bStoryHUDHidden', 1050, 250)
    b.pin('unmark', 'bStoryHUDHidden', 'false')
    b.get('cached', 'StoryHUD', 1050, 500)
    b.fn('cachedvalid', KS + 'IsValid', 1300, 500)
    b.link('cached', 'StoryHUD', 'cachedvalid', 'Object')
    b.node('cachedok', 'branch', 1300, 250)
    b.link('cachedvalid', 'ReturnValue', 'cachedok', 'Condition')
    b.get('cachedvis', 'StoryHUDVisibility', 1550, 500)
    b.fn('show', W + 'SetVisibility', 1550, 250)
    b.link('cached', 'StoryHUD', 'show', 'self')
    b.link('cachedvis', 'StoryHUDVisibility', 'show', 'InVisibility')
    b.link('which', 'else', 'ours', 'execute')
    b.link('ours', 'then', 'unmark', 'execute')
    b.chain('unmark', 'cachedok')
    b.link('cachedok', 'then', 'show', 'execute')
    b.comment('Story cinematics own the screen', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()
    return 'built'


def insert_after(graph, title, ref_fn, match=None):
    """Insert a call right after the first node titled `title` (matching `match(node)`) on its exec path."""
    ns, es = inspect(P, graph)
    node = next(n['node_id'] for n in ns if n['title'] == title and (match is None or match(n)))
    after = next_of(es, node)
    b = Batch(P, graph)
    if after:
        b.cut(node, 'then', after['to_node'], after['to_pin'])
    ref_fn(b)
    b.link(node, 'then', 'new', 'execute')
    if after:
        b.link('newend' if any(o.get('ref') == 'newend' for o in b.ops) else 'new', 'then', after['to_node'], after['to_pin'])
    b.run()


def hud_calls():
    done = []
    for graph, enable in (('TryClothingInspection', 'true'), ('CancelClothingInspection', 'false'),
                          ('PayoffShot', 'true'), ('PayoffShotCut', 'false')):
        ns, _ = inspect(P, graph)
        if any(n['title'] == 'SetStoryHUDHidden' for n in ns):
            continue
        insert_after(graph, 'PlayerCinematic', lambda b: b.fn('new', C + ':SetStoryHUDHidden', 0, -300, Hidden=enable),
                     lambda n: (default(n, 'Enable').lower() or 'false') == enable)  # a false default may export empty
        done.append(graph)
    return done or 'kept'


def return_dip():
    report = []
    if not has_graph('ReturnClothingInspection'):
        call('blueprint_add_function', path=P, function_name='ReturnClothingInspection')
    ns, _ = inspect(P, 'ReturnClothingInspection')
    if not any(n['title'] == 'StartCameraFade' for n in ns):
        b = Batch(P, 'ReturnClothingInspection')
        b.set('dip', 'bClothingReturnDip', 250, 0)
        b.pin('dip', 'bClothingReturnDip', 'true')
        b.fn('pcm', GS + 'GetPlayerCameraManager', 500, 250, PlayerIndex=0)
        b.fn('down', PCM, 500, 0, FromAlpha=0.0, ToAlpha=1.0, Duration=DIP, Color=BLACK, bHoldWhenFinished='true')
        b.link('pcm', 'ReturnValue', 'down', 'self')
        b.fn('later', KS + 'K2_SetTimer', 850, 0, FunctionName='FinishClothingInspection', Time=DIP, bLooping='false')
        b.link(find(ns, 'ReturnClothingInspection'), 'then', 'dip', 'execute')
        b.chain('dip', 'down', 'later')
        b.comment('Dip out of the cutaway', ['dip', 'pcm', 'down', 'later'])
        b.run()
        report.append('ReturnClothingInspection built')
    # the inspection's end timer goes through the dip
    ns, _ = inspect(P, 'TryClothingInspection')
    timers = [n['node_id'] for n in ns if n['title'] == 'Set Timer by Function Name' and default(n, 'FunctionName') == 'FinishClothingInspection']
    if timers:
        b = Batch(P, 'TryClothingInspection')
        for t in timers:
            b.pin(t, 'FunctionName', 'ReturnClothingInspection')
        b.run()
        report.append('TryClothingInspection ends through the dip')
    # Cancel: also clear the dip's timer, and fade back up if it cancels mid-dip
    ns, _ = inspect(P, 'CancelClothingInspection')
    if not any(n['title'] == 'Clear Timer by Function Name' and default(n, 'FunctionName') == 'ReturnClothingInspection' for n in ns):
        insert_after('CancelClothingInspection', 'Clear Timer by Function Name',
                     lambda b: b.fn('new', KS + 'K2_ClearTimer', 0, -300, FunctionName='ReturnClothingInspection'),
                     lambda n: default(n, 'FunctionName') == 'FinishClothingInspection')
        report.append('Cancel clears the dip timer')
    ns, es = inspect(P, 'CancelClothingInspection')
    if not any(n['title'] == 'Set bClothingReturnDip' for n in ns):
        tail = next(n['node_id'] for n in ns if n['title'] == 'SetStoryHUDHidden')
        assert next_of(es, tail) is None, 'Cancel has a tail after the HUD restore'
        b = Batch(P, 'CancelClothingInspection')
        b.get('dipping', 'bClothingReturnDip', 3600, 300)
        b.node('middip', 'branch', 3700, 0)
        b.link('dipping', 'bClothingReturnDip', 'middip', 'Condition')
        b.set('nodip', 'bClothingReturnDip', 3950, 0)
        b.pin('nodip', 'bClothingReturnDip', 'false')
        b.fn('pcm', GS + 'GetPlayerCameraManager', 4200, 300, PlayerIndex=0)
        b.fn('up', PCM, 4200, 0, FromAlpha=1.0, ToAlpha=0.0, Duration=0.3, Color=BLACK)
        b.link('pcm', 'ReturnValue', 'up', 'self')
        b.link(tail, 'then', 'middip', 'execute')
        b.link('middip', 'then', 'nodip', 'execute')
        b.chain('nodip', 'up')
        b.comment('Cancelled mid-dip: lift the black', ['dipping', 'middip', 'nodip', 'pcm', 'up'])
        b.run()
        report.append('Cancel lifts a pending dip')
    # Finish: the dip is spent; after the view is back, fade up in his eyes
    ns, es = inspect(P, 'FinishClothingInspection')
    if not any(n['title'] == 'HandoffFadeUp' for n in ns):
        e = find(ns, 'FinishClothingInspection')
        first = next_of(es, e)
        ends = [n['node_id'] for n in ns if n['title'] in ('FinishClothingChaseShot', 'Narrate') and next_of(es, n['node_id']) is None]
        owned = next(n['node_id'] for n in ns if n['title'] == 'Branch' and any(x['from_node'] == e for x in es) and
                     any(x['to_node'] == n['node_id'] for x in es if x['from_node'] == e))
        b = Batch(P, 'FinishClothingInspection')
        b.cut(e, 'then', first['to_node'], first['to_pin'])
        b.set('spent', 'bClothingReturnDip', 100, -250)
        b.pin('spent', 'bClothingReturnDip', 'false')
        b.link(e, 'then', 'spent', 'execute')
        b.link('spent', 'then', first['to_node'], first['to_pin'])
        b.fn('pawn', GS + 'GetPlayerPawn', 1400, 500, PlayerIndex=0)
        b.node('player', 'cast', 1500, 250, class_path=PLAYER)
        b.link('pawn', 'ReturnValue', 'player', 'Object')
        b.fn('up', PLAYER + ':HandoffFadeUp', 1800, 150)
        b.link('player', 'AsBP Fo APlayer', 'up', 'self')
        b.fn('pcm', GS + 'GetPlayerCameraManager', 1800, 550, PlayerIndex=0)
        b.fn('plain', PCM, 1800, 400, FromAlpha=1.0, ToAlpha=0.0, Duration=0.5, Color=BLACK)
        b.link('pcm', 'ReturnValue', 'plain', 'self')
        for end in ends:
            b.link(end, 'then', 'player', 'execute')
        if next_of(es, owned, 'else') is None:
            b.link(owned, 'else', 'player', 'execute')  # cancelled while dipping: still lift the black
        b.link('player', 'then', 'up', 'execute')
        b.link('player', 'CastFailed', 'plain', 'execute')
        b.comment('Back in his eyes', ['spent', 'pawn', 'player', 'up', 'pcm', 'plain'])
        b.run()
        report.append('Finish fades up after %d ends' % len(ends))
    return report or 'kept'


def stand_up():
    ns, es = inspect(P, 'ClearClothingHanger')
    if any(n['title'] == 'SetControlRotation' for n in ns):
        return 'kept'
    home_set = next(n['node_id'] for n in ns if n['title'] == 'Set Actor Transform')
    home_get = next(x for x in es if x['to_node'] == home_set and x['to_pin'] == 'NewTransform')
    after = next_of(es, home_set)
    b = Batch(P, 'ClearClothingHanger')
    b.cut(home_get['from_node'], home_get['from_pin'], home_set, 'NewTransform')
    b.fn('standrot', K + 'MakeRotator', 2100, 1200, Roll=0, Pitch=0, Yaw=STAND_YAW)
    b.fn('stand', K + 'MakeTransform', 2300, 1100, Location=STAND, Scale='(X=1.0,Y=1.0,Z=1.0)')
    b.link('standrot', 'ReturnValue', 'stand', 'Rotation')
    b.link('stand', 'ReturnValue', home_set, 'NewTransform')
    b.fn('pc', GS + 'GetPlayerController', 2500, 1300, PlayerIndex=0)
    b.fn('viewrot', K + 'MakeRotator', 2500, 1450, Roll=0, Pitch=-10, Yaw=STAND_YAW)
    b.fn('face', '/Script/Engine.Controller:SetControlRotation', 2650, -200)
    b.link('pc', 'ReturnValue', 'face', 'self')
    b.link('viewrot', 'ReturnValue', 'face', 'NewRotation')
    b.cut(home_set, 'then', after['to_node'], after['to_pin'])
    b.link(home_set, 'then', 'face', 'execute')
    b.link('face', 'then', after['to_node'], after['to_pin'])
    b.comment('Stand up where he knelt, facing the shirt', ['standrot', 'stand', 'pc', 'viewrot', 'face'])
    b.run()
    return 'stands at %s yaw %.0f' % (STAND, STAND_YAW)


def stand_where_valid():
    """T7 proof 2026-11-10: the toss only ever happens after the fall, and the fallen wardrobe covers (269.8, -55). He now
    goes back to where he started the unhook when that was the floor (z < 100), else to (150, -110), floor that the T7
    survey (t7_geometry.json) found standable with the wardrobe down; either way he faces the shirt's first landing,
    25 deg down."""
    ns, es = inspect(P, 'ClearClothingHanger')
    if any(n['title'] == 'SelectTransform' for n in ns):
        return 'kept'
    setter = next(n['node_id'] for n in ns if n['title'] == 'Set Actor Transform')
    face = next(n['node_id'] for n in ns if n['title'] == 'SetControlRotation')
    fixed = next(n['node_id'] for n in ns if n['title'] == 'MakeTransform')
    standrot = next(x['from_node'] for x in es if x['to_node'] == fixed and x['to_pin'] == 'Rotation')
    viewrot = next((x['from_node'] for x in es if x['to_node'] == face and x['to_pin'] == 'NewRotation'), None)
    b = Batch(P, 'ClearClothingHanger')
    if viewrot:
        b.ops.append(dict(op='remove', node_ids=[viewrot]))
    b.pin(fixed, 'Location', T7_STAND)
    b.pin(standrot, 'Yaw', 139.0)
    b.get('home', 'ClothingHangerHome', 2100, 1500)
    b.fn('homeparts', K + 'BreakTransform', 2300, 1500)
    b.link('home', 'ClothingHangerHome', 'homeparts', 'InTransform')
    b.fn('homez', K + 'BreakVector', 2500, 1500)
    b.link('homeparts', 'Location', 'homez', 'InVec')
    b.fn('onfloor', K + 'Less_DoubleDouble', 2700, 1500, B=100.0)
    b.link('homez', 'Z', 'onfloor', 'A')
    b.fn('chosen', K + 'SelectTransform', 2900, 1300)
    b.link('home', 'ClothingHangerHome', 'chosen', 'A')
    b.link(fixed, 'ReturnValue', 'chosen', 'B')
    b.link('onfloor', 'ReturnValue', 'chosen', 'bPickA')
    b.cut(fixed, 'ReturnValue', setter, 'NewTransform')
    b.link('chosen', 'ReturnValue', setter, 'NewTransform')
    b.fn('chosenparts', K + 'BreakTransform', 3100, 1300)
    b.link('chosen', 'ReturnValue', 'chosenparts', 'InTransform')
    b.fn('landing', K + 'MakeVector', 3100, 1500, **dict(zip('XYZ', map(float, LANDING0.split(',')))))
    b.fn('toshirt', K + 'FindLookAtRotation', 3300, 1300)  # by-ref vector pins take no literal: a MakeVector feeds Target
    b.link('chosenparts', 'Location', 'toshirt', 'Start')
    b.link('landing', 'ReturnValue', 'toshirt', 'Target')
    b.fn('yaw', K + 'BreakRotator', 3500, 1300)
    b.link('toshirt', 'ReturnValue', 'yaw', 'InRot')
    b.fn('view', K + 'MakeRotator', 3700, 1300, Roll=0.0, Pitch=-25.0)
    b.link('yaw', 'Yaw', 'view', 'Yaw')
    b.link('view', 'ReturnValue', face, 'NewRotation')
    b.comment('Back on the floor, facing the shirt', ['home', 'homeparts', 'homez', 'onfloor', 'chosen', 'chosenparts', 'landing', 'toshirt', 'yaw', 'view'])
    b.run()
    return 'home when on the floor, else %s; faces the landing' % T7_STAND


def instant_stand():
    """Proof 2026-11-10: after the dip, the kneel montage blended out over 0.35 s under the first-person camera, so his
    view rose from the floor and the landed shirt filled the frame. The kneel now stops at once (blend 0) under black."""
    ns, es = inspect(P, 'ClearClothingHanger')
    if any(n['title'] in ('Montage Stop', 'Montage_Stop') for n in ns):
        return 'kept'
    stop = next(n['node_id'] for n in ns if n['title'] == 'StopAnimMontage')
    anim = next(n['node_id'] for n in ns if n['title'] == 'GetAnimInstance')
    mont = next(n['node_id'] for n in ns if n['title'] == 'Get ClothingHangerMontage')
    before = next(x for x in es if x['to_node'] == stop and x['to_pin'] == 'execute')
    after = next_of(es, stop)
    b = Batch(P, 'ClearClothingHanger')
    b.ops.append(dict(op='remove', node_ids=[stop]))
    b.fn('stop0', '/Script/Engine.AnimInstance:Montage_Stop', 900, 0, InBlendOutTime=0.0)
    b.link(anim, 'ReturnValue', 'stop0', 'self')
    b.link(mont, 'ClothingHangerMontage', 'stop0', 'Montage')
    b.link(before['from_node'], before['from_pin'], 'stop0', 'execute')
    b.link('stop0', 'then', after['to_node'], after['to_pin'])
    b.run()
    return 'kneel stops instantly'


def wide_view():
    ns, _ = inspect(P, 'TickClothingFlight')
    pins = []
    for n in ns:
        if n['title'] not in ('VLerp', 'Lerp (Vector)'):
            continue
        val = default(n, 'B').replace(' ', '')
        if all(v in val for v in OLD_VIEW):
            pins.append((n['node_id'], WIDE_VIEW))
        elif all(v in val for v in OLD_FOCUS):
            pins.append((n['node_id'], WIDE_FOCUS))
    if not pins:
        return 'kept'
    assert len(pins) == 2, pins
    b = Batch(P, 'TickClothingFlight')
    for nid, v in pins:
        b.pin(nid, 'B', v)
    b.run()
    return 'wide view %s -> %s' % (WIDE_VIEW, WIDE_FOCUS)


assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + P], ttl_s=300, wait_s=240)
try:
    for name, t in (('StoryHUD', 'object:/Script/UMG.UserWidget'), ('StoryHUDVisibility', 'enum:/Script/UMG.ESlateVisibility'),
                    ('bStoryHUDHidden', 'bool'), ('bClothingReturnDip', 'bool')):
        call('blueprint_add_variable', path=P, variable_name=name, variable_type=t, category='Story|Cinematics', update_existing=True)
    report = dict(SetStoryHUDHidden=hud_function(), HUDCalls=hud_calls(), ReturnDip=return_dip(), StandUp=stand_up(),
                  WideView=wide_view(), InstantStand=instant_stand(), StandValid=stand_where_valid())
    Path('P:/FoA/Saved/StoryShots/chase_cutaway_patch.json').write_text(json.dumps(report, indent=1))
    print('chase cutaway', report)
finally:
    h.release('story', token)
