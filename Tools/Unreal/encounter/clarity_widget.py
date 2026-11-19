"""Battle clarity, WBP_Encounter side (battle lane, 2026-11-17). Hayba only; idempotent; edits in place.
  $env:HAYBA_AGENT_ID='battle'; python Tools/Unreal/encounter/clarity_widget.py <phase>
Hold a lease on WBP_Encounter first (editor_lock.py acquire battle --assets /Game/FoA/Gameplay/Encounter/WBP_Encounter).
Phases, in order:
  screen   collapse the top-right panel, help lines, controls footer, phase line, status line, target line, eye box and
           the Change target text button; card labels lose their "(N Resolve)" suffix
  tree     GarmentMarks canvas: MarkRows (MarkPips0-4, copies of the old roster's pip row), ThreatRing (a circle outline in the keycap's
           ink) and one Glyph (a copy of the prompt keycap)
  declare  widget variables and function stubs
  bodies   PlaceMark(Index), PlaceThreat, PlaceGlyph, PulseCards, PlaceMarks, MinimalLog
  lengths  PlaceMark's Array_Length through clarity_length.py (Hayba leaves that wildcard untyped)
  hook     Event Tick runs PlaceMarks after TornTick; RedrawAll ends with MinimalLog
  selftest offline checks of the node finders (no editor)
What the player sees: each garment's buttons as pips just above it (lit = done; the target bright and larger, the rest
dim; a garment winding up a heavy attack swells), a ring that sweeps closed on the hero while an attack winds up (its
last 30% is the brace window), one key glyph at a time (Space in a wind-up, Enter on the first turn, E beside the target
later), the stun card breathing while its garment telegraphs, and one narration line only outside the player's choice
and the enemy's attacks.
After any graph capture (FoAGraphToolsLibrary), recompile and save both Blueprints: the capture leaves them BS_DIRTY and
the playtest pre-flight then skips every lane's burst (11-17 23:30)."""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal/level2']
from hayba_call import call  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402
import build_drive as b  # noqa: E402

WBP = '/Game/FoA/Gameplay/Encounter/WBP_Encounter'
ENC = '/Game/FoA/Gameplay/Encounter/BP_Encounter'
GAR = '/Game/FoA/Gameplay/Encounter/BP_Garment'
OPP = '/Game/FoA/Gameplay/Encounter/PDA_Opponent'
MOVE = '/Game/FoA/Gameplay/Encounter/PDA_Move'
EC, GC, WC = b.cls(ENC), b.cls(GAR), b.cls(WBP)
K, GS, SL = b.K, b.GS, b.SL
W = '/Script/UMG.Widget:'
WLL = '/Script/UMG.WidgetLayoutLibrary:'
ARR = '/Script/Engine.KismetArrayLibrary:'
SANDBUTTON = '/Game/FoA/UI/Widgets/Common/WBP_SandButton'
CARD_FACES = ('TornSize_Act0', 'TornSize_Act1', 'TornSize_Act2', 'TornSize_Breathe', 'TornSize_Mirror')
CARD_WIDGETS = tuple((n, 'HitTestInvisible') for n in CARD_FACES) + tuple(
    (n, 'SelfHitTestInvisible') for n in ('Btn_Act0', 'Btn_Act1', 'Btn_Act2', 'Btn_Breathe', 'Btn_Mirror'))
# Designer-collapsed: nothing at runtime sets their visibility (only text or opacity).
COLLAPSE = ('Txt_BattleHelp', 'Txt_BattleControls', 'Txt_BattlePhase', 'Txt_Statuses', 'Txt_Target', 'Txt_TornDetail',
            'TornIntent', 'Btn_NextTarget', 'EnemyPanel')
# Runtime SetVisibility nodes that would show them again: (graph, widget getter, old value) -> Collapsed.
RUNTIME = (('RefreshBattlePresentation', 'Get EnemyPanel', 'Visible'),
           ('RefreshBattlePresentation', 'Get Txt_BattleControls', 'Visible'),
           ('TornTrackIntent', 'Get TornIntent', 'HitTestInvisible'))
RING_SIZE = (190, 190)
LENGTH_SENTINEL = 9001  # PlaceMark's count pin until lengths() wires Array_Length into it
FUNCS = {'ShowCards': [], 'PlaceMark': [('Index', 'int')], 'PlaceThreat': [], 'PlaceGlyph': [], 'PulseCards': [], 'PlaceMarks': [],
         'MinimalLog': []}
VARS = [('PopAt', 'float', '-10'), ('PopWho', 'object:/Script/Engine.Actor', ''), ('MarksAt', 'float', '-1'), ('bPipsDirty', 'bool', 'true'), ('BattleTurns', 'int', '0'), ('LastState', 'name', 'None'), ('TargetMarkX', 'float', '0'),
        ('TargetMarkY', 'float', '0'), ('RingX', 'float', '0'), ('RingY', 'float', '0')]


def ok(r, what):
    assert r.get('ok') and (r.get('data') or {}).get('ok', True), (what, r)
    return r.get('data') or {}


def pin(node, name):
    return next((p.get('default_value') for p in node['pins'] if p['name'] == name), None)


def visibility_nodes(nodes, edges, getter, value):
    """SetVisibility nodes whose target comes from `getter` and whose InVisibility is `value`."""
    by = {n['node_id']: n for n in nodes}
    return [e['to_node'] for e in edges
            if e['to_pin'] == 'self' and by[e['from_node']]['title'] == getter
            and by[e['to_node']]['title'] == 'SetVisibility' and pin(by[e['to_node']], 'InVisibility') == value]


def screen():
    for name in COLLAPSE:
        r = call('ui_set_visibility', dict(widget_blueprint_path=WBP, widget_name=name, visibility='Collapsed'))
        print('designer', name, r.get('ok'), (r.get('data') or {}).get('failed') or r.get('error') or '')
    graphs = {}
    for graph, getter, value in RUNTIME:
        nodes, edges = graphs.setdefault(graph, inspect(WBP, graph))
        hits = visibility_nodes(nodes, edges, getter, value)
        print(graph, getter, value, '->', len(hits), 'node(s)')
        if hits:
            g = Batch(WBP, graph)
            for h in hits:
                g.pin(h, 'InVisibility', 'Collapsed')
            g.run()
            graphs[graph] = inspect(WBP, graph)
    # MoveLabel: name only. The cost branch compares Cost > B; B=9999 always takes the plain-name return.
    nodes, _ = inspect(WBP, 'MoveLabel')
    gt = [n['node_id'] for n in nodes if n['title'] == 'integer > integer' and pin(n, 'B') != '9999']
    if gt:
        g = Batch(WBP, 'MoveLabel')
        g.pin(gt[0], 'B', 9999)
        g.run()
    print('MoveLabel cost suffix off:', not gt or 'patched')
    # Unlit pips at 0.22 vanish once the garment rows are dimmed too; 0.4 still reads as "one more to do".
    nodes, _ = inspect(WBP, 'SetPips')
    dim = [n['node_id'] for n in nodes if n['title'] == 'SelectFloat' and pin(n, 'B') == '0.22']
    if dim:
        g = Batch(WBP, 'SetPips')
        g.pin(dim[0], 'B', 0.4)
        g.run()


def tree():
    have = {m['name'] for m in ok(call('ui_query', dict(path=WBP, name_pattern='Mark', include_slot=False)),
                                     'query').get('matches', [])}
    if 'GarmentMarks' not in have:
        ok(call('ui_build_tree', dict(widget_blueprint_path=WBP, parent_widget_name='RootCanvas',
                                      tree=dict(**{'class': 'CanvasPanel'}, name='GarmentMarks',
                                                children=[dict(**{'class': 'Image'}, name='ThreatRing')]))), 'build')
    lay = lambda name, **k: ok(call('ui_set_slot_layout', dict(widget_blueprint_path=WBP, widget_name=name, **k)), name)  # noqa: E731
    lay('GarmentMarks', anchors=[0, 0, 1, 1], position=[0, 0], size=[0, 0])
    call('ui_set_visibility', dict(widget_blueprint_path=WBP, widget_name='GarmentMarks', visibility='HitTestInvisible'))
    for i in range(5):  # superseded meter images (11-17 23:35): an empty meter vanished on the dark room
        if 'Mark%d' % i in have:
            ok(call('ui_remove_element', dict(widget_blueprint_path=WBP, widget_name='Mark%d' % i)), 'remove')
    if 'MarkRows' not in have:
        ok(call('ui_build_tree', dict(widget_blueprint_path=WBP, parent_widget_name='GarmentMarks',
                                      tree=dict(**{'class': 'CanvasPanel'}, name='MarkRows'))), 'rows')
    lay('MarkRows', anchors=[0, 0, 1, 1], position=[0, 0], size=[0, 0])
    for i in range(5):  # each row is a copy of the old roster's pip row (six pips, SetPips lights them)
        if 'MarkPips%d' % i not in have:
            ok(call('ui_duplicate_element', dict(widget_blueprint_path=WBP, widget_name='Pips0', new_name='MarkPips%d' % i,
                                                 parent_widget_name='MarkRows')), 'dup')
        lay('MarkPips%d' % i, anchors=[0, 0, 0, 0], position=[-400, -400], alignment=[0.5, 1.0], auto_size=True)
        ok(call('ui_set_widget_properties', dict(widget_blueprint_path=WBP, widget_name='MarkPips%d' % i,
                                                 properties={'RenderOpacity': 0.0})), 'pips')
        # The roster's Pips0 is designer-collapsed, and so was every copy (B3 23:44: no pips on screen).
        call('ui_set_visibility', dict(widget_blueprint_path=WBP, widget_name='MarkPips%d' % i, visibility='HitTestInvisible'))
    call('ui_set_visibility', dict(widget_blueprint_path=WBP, widget_name='MarkRows', visibility='HitTestInvisible'))
    ok(call('ui_set_variable', dict(widget_blueprint_path=WBP, widget_name='MarkRows', is_variable=True)), 'rows var')
    # Each pip: a white dot with a dark ink rim, so it reads on the pale wall and the dark fireplace alike
    # (coordinator review 11-18 00:55). bUseBrushTransparency keeps SetPips' opacity working.
    def kids(node):  # the copied pips are named Pip0_6..Pip0_35: walk the tree (flat queries stop at 50 matches)
        if node.get('name') == 'MarkRows':
            return [p['name'] for row in node.get('children', []) for p in row.get('children', [])]
        return next((k for c in node.get('children', []) if isinstance(c, dict) for k in [kids(c)] if k), [])
    pips = kids(ok(call('ui_query', dict(path=WBP, include_slot=False)), 'tree')['root'])
    assert len(pips) == 30, len(pips)
    for name in pips:
        ok(call('object_set_property', dict(path=WBP + '.WBP_Encounter:WidgetTree.' + name, properties={'Brush': (
            '(TintColor=(SpecifiedColor=(R=1.0,G=1.0,B=1.0,A=1.0),ColorUseRule=UseColor_Specified),DrawAs=RoundedBox,'
            'ImageSize=(X=14,Y=14),ResourceObject=None,OutlineSettings=(CornerRadii=(X=7,Y=7,Z=7,W=7),'
            'Color=(SpecifiedColor=(R=0.02,G=0.02,B=0.02,A=0.9),ColorUseRule=UseColor_Specified),Width=1.5,'
            'RoundingType=FixedRadius,bUseBrushTransparency=True))')})), name)
    lay('ThreatRing', anchors=[0, 0, 0, 0], position=[-400, -400], size=list(RING_SIZE), alignment=[0.5, 0.5])
    # A plain Slate circle outline in the keycap's ink (the keycap is a RoundedBox too). MI_UI_Ring_Parry was tried
    # first and drew nothing at runtime (B3f 00:16: opacity 1, no ring); it had no other user to prove it.
    # bUseBrushTransparency must be on (off, Slate drew the box opaque and ignored RenderOpacity, B3k 00:53), and the
    # fill needs a little alpha: a fully transparent tint skipped the whole box, outline included (B3k 01:03).
    r = RING_SIZE[0] / 2
    ok(call('object_set_property', dict(path=WBP + '.WBP_Encounter:WidgetTree.ThreatRing', properties={'Brush': (
        '(TintColor=(SpecifiedColor=(R=0.0,G=0.0,B=0.0,A=0.12),ColorUseRule=UseColor_Specified),DrawAs=RoundedBox,'
        'ImageSize=(X=%d,Y=%d),ResourceObject=None,OutlineSettings=(CornerRadii=(X=%d,Y=%d,Z=%d,W=%d),'
        'Color=(SpecifiedColor=(R=0.86,G=0.86,B=0.86,A=1.0),ColorUseRule=UseColor_Specified),Width=5.0,'
        'RoundingType=FixedRadius,bUseBrushTransparency=True))' % (RING_SIZE[0], RING_SIZE[1], r, r, r, r))})), 'ring brush')
    glyphs = call('ui_query', dict(path=WBP, name_pattern='Glyph', include_slot=False)).get('data', {}).get('matches', [])
    if not any(m['name'] == 'Glyph' for m in glyphs):  # TornGlyph_Act* also match the pattern
        d = ok(call('ui_duplicate_element', dict(widget_blueprint_path=WBP, widget_name='KeyCap', new_name='Glyph',
                                                 parent_widget_name='GarmentMarks')), 'dup')
        print('glyph copy', d)
    text = [m['name'] for m in ok(call('ui_query', dict(path=WBP, name_pattern='Txt_PromptKey', include_slot=False)),
                                  'q').get('matches', []) if m['name'] != 'Txt_PromptKey']
    if text:
        ok(call('ui_rename_element', dict(widget_blueprint_path=WBP, widget_name=text[0], new_name='Txt_Glyph')), 'rename')
    lay('Glyph', anchors=[0, 0, 0, 0], position=[-400, -400], alignment=[0.5, 0.5], auto_size=True)
    # The copied keycap drew its box opaque at render opacity 0 (empty keycaps all over D1 01:12): transparency on.
    ok(call('object_set_property', dict(path=WBP + '.WBP_Encounter:WidgetTree.Glyph', properties={'Background': (
        '(TintColor=(SpecifiedColor=(R=0.0,G=0.0,B=0.0,A=0.35),ColorUseRule=UseColor_Specified),DrawAs=RoundedBox,'
        'ImageSize=(X=32,Y=32),ResourceObject=None,OutlineSettings=(CornerRadii=(X=10,Y=10,Z=10,W=10),'
        'Color=(SpecifiedColor=(R=0.86,G=0.86,B=0.86,A=0.9),ColorUseRule=UseColor_Specified),Width=2.0,'
        'RoundingType=FixedRadius,bUseBrushTransparency=True))')})), 'glyph box')
    for name in ('GarmentMarks', 'ThreatRing', 'Glyph', 'Txt_Glyph') + CARD_FACES:
        ok(call('ui_set_variable', dict(widget_blueprint_path=WBP, widget_name=name, is_variable=True)), name)
    for name in ('ThreatRing', 'Glyph'):
        ok(call('ui_set_widget_properties', dict(widget_blueprint_path=WBP, widget_name=name,
                                                 properties={'RenderOpacity': 0.0})), name)
    r = call('blueprint_compile', dict(path=WBP, save=True))
    print('tree compile', (r.get('data') or {}).get('error_count'), (r.get('data') or {}).get('saved'))


def declare():
    for name, kind, default in VARS:
        b.call('blueprint_add_variable', path=WBP, variable_name=name, variable_type=kind, default_value=default,
               category='Clarity', update_existing=True)
    for name, ins in FUNCS.items():
        if not b.h.call('blueprint_inspect_graph', dict(path=WBP, graph_name=name, limit=1)).get('ok'):
            b.call('blueprint_add_function', path=WBP, function_name=name, inputs=[dict(name=n, type=t) for n, t in ins])
    r = call('blueprint_compile', dict(path=WBP, save=True))
    print('declare compile', (r.get('data') or {}).get('error_count'))


def item_at(g, array, index):
    r = g.ref()
    g.node(r, 'get_array_item', 0, 0)
    g.put(r, 'Array', array)
    g.put(r, 'Dimension 1', index)
    return r, 'Output'


def now(g):
    return g.f(SL + 'GetGameTimeInSeconds')


def screen_at(g, world):
    """Viewport-relative widget position of a world point: (x, y, onscreen)."""
    p = g.f(WLL + 'ProjectWorldLocationToWidgetPosition', PlayerController=g.f(GS + 'GetPlayerController', PlayerIndex=0),
            WorldLocation=world, bPlayerViewportRelative=True)
    xy = g.f(K + 'BreakVector2D', InVec=(p[0], 'ScreenPosition'))
    return (xy[0], 'X'), (xy[0], 'Y'), (p[0], 'ReturnValue')


def bodies():
    # PlaceMark(Index): the garment's buttons as a row of pips just above it (lit = done), bright for the target,
    # swelling while it winds up a heavy attack. Pips beat the UI kit meter here: an empty meter is a dark slab on a
    # dark room (11-17 B3k frames), an unlit pip still reads as "one more to do".
    g = b.G(WBP, 'PlaceMark')
    idx = g.arg('Index')
    mark = g.cast(g.f('/Script/UMG.PanelWidget:GetChildAt', self=g.getv('MarkRows'), Index=idx), '/Script/UMG.PanelWidget', 'Panel Widget')
    enc = g.getv('Encounter')
    garments = g.getv('Garments', enc, ENC)
    # B is the garment count, wired by lengths(): a batch connect leaves Array_Length's wildcard untyped.
    g.side(g.branch(g.math('Less_IntInt', A=idx, B=LENGTH_SENTINEL)))
    gar = item_at(g, garments, idx)
    state = g.getv('BattleState', enc, ENC)
    over = g.math('BooleanOR', A=g.math('EqualEqual_NameName', A=state, B='Victory'),
                  B=g.math('EqualEqual_NameName', A=state, B='Defeat'))
    live = g.math('BooleanAND', A=g.f(SL + 'IsValid', Object=gar),
                  B=g.math('BooleanAND', A=g.getv('bActive', enc, ENC), B=g.math('Not_PreBool', A=over)))
    # A row shows only while its garment is really there: alive (not yet worn), drawn in the last 0.25 s (so not
    # hidden, not sunk in the sand before it rises, not behind the hero or off screen), and in front of the camera.
    # Coordinator review 11-18 01:50: single pips floated by his hip and over empty floor on the first turn.
    seen = g.math('BooleanAND', A=(g.f(GC + ':IsAlive', self=gar)[0], 'bAlive'),
                  B=g.f(b.A + 'WasRecentlyRendered', self=gar, Tolerance=0.25))
    # The visible mesh (Body: the rig, or the placeholder mesh), not the actor: its bounds also hold the hidden
    # placeholder, which put rows off the garment (B3k 01:50: a pip on the hero's arm).
    bounds = g.f(SL + 'GetComponentBounds', Component=g.getv('Body', gar, GAR))
    ext = g.math('BreakVector', InVec=(bounds[0], 'BoxExtent'))
    # On the garment's chest, 30 cm under the top of its bounds (their centre sits low: B3k 01:03 had the rows on the floor).
    chest = g.math('Add_VectorVector', A=(bounds[0], 'Origin'),
                   B=g.math('MakeVector', X=0, Y=0, Z=g.math('Subtract_DoubleDouble', A=(ext[0], 'Z'), B=30.0)))
    x, y, onscreen = screen_at(g, chest)
    slot = g.f(WLL + 'SlotAsCanvasSlot', Widget=mark)
    g.do('/Script/UMG.CanvasPanelSlot:SetPosition', self=slot, InPosition=g.math('MakeVector2D', X=x, Y=y))
    winding = g.math('EqualEqual_NameName', A=g.getv('State', gar, GAR), B='Telegraph')
    pulse = g.math('Add_DoubleDouble', A=0.5, B=g.math('Multiply_DoubleDouble', A=0.5, B=g.math('Sin', A=g.math(
        'Multiply_DoubleDouble', A=now(g), B=9.0))))
    target = g.math('EqualEqual_IntInt', A=idx, B=g.getv('Target', enc, ENC))
    # Single-button garments only show their row when targeted or winding up: an idle lone pip read as a stray dot.
    worth = g.math('BooleanOR', A=g.math('BooleanOR', A=target, B=winding), B=g.math('Greater_IntInt', A=g.getv('Resistance', g.getv('Data', gar, GAR), OPP), B=1))
    visible = g.math('BooleanAND', A=g.math('BooleanAND', A=live, B=worth), B=g.math('BooleanAND', A=seen, B=onscreen))
    # Fade at the 30 Hz update: in by 0.2 a step (about 0.15 s), out by half a step, snapping to 0 near the end.
    cur = g.f(W + 'GetRenderOpacity', self=mark)
    want = g.math('SelectFloat', A=1.0, B=0.6, bPickA=target)
    fade_in = g.math('FMin', A=want, B=g.math('Add_DoubleDouble', A=cur, B=0.2))
    fade_out = g.math('SelectFloat', A=0.0, B=g.math('Multiply_DoubleDouble', A=cur, B=0.5),
                      bPickA=g.math('Less_DoubleDouble', A=cur, B=0.04))
    g.do(W + 'SetRenderOpacity', self=mark, InOpacity=g.math('SelectFloat', A=fade_in, B=fade_out, bPickA=visible))
    # 14 px pips: 2.6x on the target, 2x on the rest (B3k 00:03 frames: unreadable at 1x).
    # A pip that fills pops: ShowDamage stamps PopAt/PopWho, the row swells 60% and settles over 0.35 s.
    pop = g.math('SelectFloat', A=g.math('FClamp', Value=g.math('Subtract_DoubleDouble', A=1.0, B=g.math('Divide_DoubleDouble', A=g.math(
        'Subtract_DoubleDouble', A=now(g), B=g.getv('PopAt')), B=0.35)), Min=0.0, Max=1.0), B=0.0,
        bPickA=g.math('EqualEqual_ObjectObject', A=gar, B=g.getv('PopWho')))
    size = g.math('Multiply_DoubleDouble', A=g.math('Multiply_DoubleDouble', A=g.math('SelectFloat', A=2.6, B=2.0, bPickA=target),
                                                    B=g.math('Add_DoubleDouble', A=1.0, B=g.math('Multiply_DoubleDouble', A=0.6, B=pop))),
                  B=g.math('SelectFloat', A=g.math('Add_DoubleDouble', A=1.0, B=g.math('Multiply_DoubleDouble', A=0.3, B=pulse)),
                           B=1.0, bPickA=winding))
    g.do(W + 'SetRenderScale', self=mark, Scale=g.math('MakeVector2D', X=size, Y=size))
    g.setv('TargetMarkX', g.math('SelectFloat', A=x, B=g.getv('TargetMarkX'), bPickA=target))
    g.setv('TargetMarkY', g.math('SelectFloat', A=y, B=g.getv('TargetMarkY'), bPickA=target))
    # Pips only change on OnChanged (MinimalLog raises bPipsDirty), so SetPips' recursion skips the other frames.
    g.side(g.branch(g.getv('bPipsDirty')))
    g.own('SetPips', Row=mark, Lit=g.getv('Progress', gar, GAR), Shown=g.getv('Resistance', g.getv('Data', gar, GAR), OPP), Index=0)
    g.finish()

    # PlaceThreat: the parry ring sweeps closed on the hero's chest during a wind-up, then flashes on the impact.
    g = b.G(WBP, 'PlaceThreat')
    ring = g.getv('ThreatRing')
    enc = g.getv('Encounter')
    wind = g.getv('bWindUp', enc, ENC)
    t = now(g)
    sweep = g.math('FClamp', Value=g.math('Divide_DoubleDouble', A=g.math('Subtract_DoubleDouble', A=t, B=g.getv('WindUpStart', enc, ENC)),
                                         B=g.math('FMax', A=g.getv('WindUpTime', enc, ENC), B=0.05)), Min=0.0, Max=1.0)
    flash = g.math('FClamp', Value=g.math('Subtract_DoubleDouble', A=1.0, B=g.math('Divide_DoubleDouble', A=g.math(
        'Subtract_DoubleDouble', A=t, B=g.getv('ImpactAt', enc, ENC)), B=0.35)), Min=0.0, Max=1.0)
    # Attacks only happen in EnemyPhase: the ring never shows on the player's turn, a resolving move or the outcome
    # (B3 00:31 frames had it on the hero after a Deep Breath and at Victory).
    attacking = g.math('BooleanAND', A=g.getv('bActive', enc, ENC),
                       B=g.math('EqualEqual_NameName', A=g.getv('BattleState', enc, ENC), B='EnemyPhase'))
    show = g.math('BooleanAND', A=attacking,
                  B=g.math('BooleanOR', A=wind, B=g.math('Greater_DoubleDouble', A=flash, B=0.0)))
    pawn = g.f(GS + 'GetPlayerPawn', PlayerIndex=0)
    chest = g.math('Add_VectorVector', A=g.f(b.A + 'K2_GetActorLocation', self=pawn), B=g.math('MakeVector', X=0, Y=0, Z=38.0))
    x, y, onscreen = screen_at(g, chest)
    # The attack shots frame the hero at the screen's left edge (B3k 23:33: his chest at x=-36): keep the ring on screen.
    view = g.f(WLL + 'GetViewportSize')
    scale = g.f(WLL + 'GetViewportScale')
    vw = g.math('Divide_DoubleDouble', A=(g.math('BreakVector2D', InVec=view)[0], 'X'), B=scale)
    vh = g.math('Divide_DoubleDouble', A=(g.math('BreakVector2D', InVec=view)[0], 'Y'), B=scale)
    x = g.math('FClamp', Value=x, Min=150.0, Max=g.math('Subtract_DoubleDouble', A=vw, B=150.0))
    y = g.math('FClamp', Value=y, Min=150.0, Max=g.math('Subtract_DoubleDouble', A=vh, B=230.0))
    g.do('/Script/UMG.CanvasPanelSlot:SetPosition', self=g.f(WLL + 'SlotAsCanvasSlot', Widget=ring),
         InPosition=g.math('MakeVector2D', X=x, Y=y))
    g.setv('RingX', x)
    g.setv('RingY', y)
    # Closes from 1.8x onto him exactly at the impact; dim until the brace window, full once Space would count;
    # after the impact it swells out and fades (0.35 s).
    window = g.math('BooleanAND', A=g.math('GreaterEqual_DoubleDouble', A=sweep, B=g.getv('BraceFrom', enc, ENC)),
                    B=g.math('Not_PreBool', A=g.getv('bBraceSpent', enc, ENC)))
    close = g.math('SelectFloat', A=g.math('Subtract_DoubleDouble', A=1.8, B=g.math('Multiply_DoubleDouble', A=0.8, B=sweep)),
                   B=g.math('Add_DoubleDouble', A=1.0, B=g.math('Multiply_DoubleDouble', A=0.35, B=g.math(
                       'Subtract_DoubleDouble', A=1.0, B=flash))), bPickA=wind)
    g.do(W + 'SetRenderScale', self=ring, Scale=g.math('MakeVector2D', X=close, Y=close))
    lit = g.math('SelectFloat', A=g.math('SelectFloat', A=1.0, B=0.5, bPickA=window), B=flash, bPickA=wind)
    g.do(W + 'SetRenderOpacity', self=ring, InOpacity=g.math('SelectFloat', A=lit, B=0.0,
                                                               bPickA=g.math('BooleanAND', A=show, B=onscreen)))
    g.finish()

    # PlaceGlyph: one key at a time. Space under the ring in a wind-up; Enter right of the cards on the first turn;
    # Tab beside the target's meter on later turns while two or more garments stand.
    g = b.G(WBP, 'PlaceGlyph')
    enc = g.getv('Encounter')
    command = g.math('BooleanAND', A=g.getv('bPlayerTurn', enc, ENC),
                     B=g.math('EqualEqual_NameName', A=g.getv('BattleState', enc, ENC), B='PlayerCommand'))
    wind = g.math('BooleanAND', A=g.getv('bWindUp', enc, ENC), B=g.math('Not_PreBool', A=g.getv('bBraceSpent', enc, ENC)))
    first = g.math('BooleanAND', A=command, B=g.math('LessEqual_IntInt', A=g.getv('BattleTurns'), B=1))
    tab = g.math('BooleanAND', A=command, B=g.math('GreaterEqual_IntInt', A=g.getv('Remaining', enc, ENC), B=2))
    view = g.f(WLL + 'GetViewportSize')
    scale = g.f(WLL + 'GetViewportScale')
    vw = g.math('Divide_DoubleDouble', A=(g.math('BreakVector2D', InVec=view)[0], 'X'), B=scale)
    vh = g.math('Divide_DoubleDouble', A=(g.math('BreakVector2D', InVec=view)[0], 'Y'), B=scale)
    gx = g.math('SelectFloat', A=g.getv('RingX'), B=g.math('SelectFloat', A=g.math('Multiply_DoubleDouble', A=vw, B=0.765),
                B=g.getv('TargetMarkX'), bPickA=first), bPickA=wind)
    gy = g.math('SelectFloat', A=g.math('Add_DoubleDouble', A=g.getv('RingY'), B=122.0),
                B=g.math('SelectFloat', A=g.math('Multiply_DoubleDouble', A=vh, B=0.84),
                         B=g.math('Subtract_DoubleDouble', A=g.getv('TargetMarkY'), B=80.0), bPickA=first), bPickA=wind)
    label = g.math('SelectString', A='Space', B=g.math('SelectString', A='Enter', B='E', bPickA=first), bPickA=wind)
    g.do('/Script/UMG.TextBlock:SetText', self=g.getv('Txt_Glyph'), InText=g.f('/Script/Engine.KismetTextLibrary:Conv_StringToText', InString=label))
    glyph = g.getv('Glyph')
    g.do('/Script/UMG.CanvasPanelSlot:SetPosition', self=g.f(WLL + 'SlotAsCanvasSlot', Widget=glyph), InPosition=g.math('MakeVector2D', X=gx, Y=gy))
    any_ = g.math('BooleanOR', A=wind, B=g.math('BooleanOR', A=first, B=tab))
    g.do(W + 'SetRenderOpacity', self=glyph, InOpacity=g.math('SelectFloat', A=0.92, B=0.0, bPickA=any_))
    g.finish()

    # PulseCards: while the target winds up a heavy attack, the card that stuns it breathes.
    g = b.G(WBP, 'PulseCards')
    enc = g.getv('Encounter')
    # The cards' frames (each button's Img_CommandFocus) outlived the cards as empty boxes in every enemy phase and
    # followed the thrown card to the garment (B3f 00:16): they show on the player's turn only.
    gar = g.f(EC + ':TargetGarment', self=enc)
    gar = (gar[0], 'Garment')
    g.side(g.branch(g.f(SL + 'IsValid', Object=gar)))
    warn = g.math('BooleanAND', A=g.getv('bPlayerTurn', enc, ENC),
                  B=g.math('EqualEqual_NameName', A=g.getv('State', gar, GAR), B='Telegraph'))
    moves = g.getv('ActMoves', g.getv('Data', gar, GAR), OPP)
    beat = g.math('Add_DoubleDouble', A=1.0, B=g.math('Multiply_DoubleDouble', A=0.06, B=g.math('Sin', A=g.math(
        'Multiply_DoubleDouble', A=now(g), B=7.0))))
    for i in range(2):  # shortcut: every L1 and C.V row has exactly two ActMoves; a one-move row would warn here
        move = item_at(g, moves, i)
        stuns = g.getv('bStuns', move, MOVE)
        s = g.math('SelectFloat', A=beat, B=1.0, bPickA=g.math('BooleanAND', A=warn, B=stuns))
        card = g.getv(f'TornSize_Act{i}')  # inside the card TornStep scales: the two scales multiply (patch_pulse_scale.py)
        g.do(W + 'SetRenderScale', self=card, Scale=g.math('MakeVector2D', X=s, Y=s))
    g.finish()

    # PlaceMarks runs from Event Tick but at most 30 times a second (perf lane, 11-18: the fight's UI was 2.0 ms a frame).
    g = b.G(WBP, 'PlaceMarks')
    t = now(g)
    g.side(g.branch(g.math('GreaterEqual_DoubleDouble', A=g.math('Subtract_DoubleDouble', A=t, B=g.getv('MarksAt')), B=0.033)))
    g.setv('MarksAt', t)
    for i in range(5):
        g.own('PlaceMark', Index=i)
    g.setv('bPipsDirty', False)
    g.own('PlaceThreat')
    g.own('PlaceGlyph')
    g.own('PulseCards')
    g.finish()

    # MinimalLog: one narration line, only between the choices and the attacks; counts the player's turns.
    g = b.G(WBP, 'MinimalLog')
    enc = g.getv('Encounter')
    state = g.getv('BattleState', enc, ENC)
    eq = lambda name: g.math('EqualEqual_NameName', A=state, B=name)  # noqa: E731
    show = g.math('BooleanAND', A=g.math('BooleanOR', A=g.math('BooleanOR', A=eq('Intro'), B=eq('ResolvePlayerAction')),
                                         B=g.math('BooleanOR', A=eq('Victory'), B=eq('Defeat'))),
                  B=g.math('Not_PreBool', A=g.getv('bAwaitingKey', enc, ENC)))
    g.do(W + 'SetRenderOpacity', self=g.getv('LogPanel'), InOpacity=g.math('SelectFloat', A=1.0, B=0.0, bPickA=show))
    entered = g.math('BooleanAND', A=eq('PlayerCommand'),
                     B=g.math('NotEqual_NameName', A=g.getv('LastState'), B='PlayerCommand'))
    g.setv('BattleTurns', g.math('Add_IntInt', A=g.getv('BattleTurns'), B=g.math('SelectInt', A=1, B=0, bPickA=entered)))
    g.setv('LastState', state)
    g.setv('bPipsDirty', True)
    g.finish()

    # ShowCards, first in RedrawAll (before RefreshBattlePresentation focuses a card): the card faces and buttons draw
    # through retainer materials that ignore render opacity, so their empty frames stayed through every enemy phase
    # (B3k 01:03). Hidden (layout kept) outside the player's turn; while a move resolved the faded cards still left empty
    # frames (B3f 01:23), so the thrown card goes too: the garment's hit, pip pop, number and click carry the move.
    g = b.G(WBP, 'ShowCards')
    enc = g.getv('Encounter')
    for name, _ in CARD_WIDGETS:
        g.do(W + 'SetVisibility', self=g.getv(name), InVisibility='Hidden')
    g.side(g.branch(g.getv('bPlayerTurn', enc, ENC)))
    for name, shown in CARD_WIDGETS:
        g.do(W + 'SetVisibility', self=g.getv(name), InVisibility=shown)
    g.finish()


def lengths():
    """PlaceMark's index guard needs Garments' length. Single Hayba commands type Array_Length's wildcard (a batch
    connect does not), so this step adds that one node by hand."""
    nodes, edges = inspect(WBP, 'PlaceMark')
    less = [n['node_id'] for n in nodes if n['title'] == 'integer < integer' and pin(n, 'B') == str(LENGTH_SENTINEL)]
    if not less:
        print('lengths: already wired')
        return
    # Single Hayba commands leave the wildcard untyped too (tested 23:10), so editor Python adds the node.
    import os
    import subprocess
    env = dict(os.environ, FOA_AREAS=WBP)
    subprocess.run([sys.executable, 'P:/FoA/Tools/Unreal/ue_remote.py', 'P:/FoA/Tools/Unreal/encounter/clarity_length.py'],
                   cwd='P:/FoA', env=env, check=True)
    r = ok(call('blueprint_compile', dict(path=WBP, save=True)), 'compile')
    assert not r.get('error_count'), r
    print('lengths: wired, compile', r.get('error_count'), r.get('saved'))


def hook():
    nodes, edges = inspect(WBP, 'ShowDamage')
    if not any(n['title'] == 'Set PopWho' for n in nodes):
        timer = next(n['node_id'] for n in nodes if n['title'] == 'Set Timer by Function Name')
        entry = next(n['node_id'] for n in nodes if n['title'] == 'ShowDamage')
        assert not [e for e in edges if e['from_node'] == timer and e['from_pin'] == 'then']
        g = Batch(WBP, 'ShowDamage')
        g.fn('cl_now', SL + 'GetGameTimeInSeconds', 1800, 300)
        g.set('cl_at', 'PopAt', 2000, 0)
        g.link('cl_now', 'ReturnValue', 'cl_at', 'PopAt')
        g.set('cl_who', 'PopWho', 2300, 0)
        g.link(entry, 'Who', 'cl_who', 'PopWho')
        g.chain(timer, 'cl_at', 'cl_who')
        g.comment('Pip pop', ['cl_now', 'cl_at', 'cl_who'])
        g.run()
    nodes, edges = inspect(WBP, 'EventGraph')
    if not any(n['title'] == 'PlaceMarks' for n in nodes):
        torn = next(n['node_id'] for n in nodes if n['title'] == 'TornTick')
        g = Batch(WBP, 'EventGraph')
        g.fn('cl_marks', WC + ':PlaceMarks', 900, 6200)
        g.link(torn, 'then', 'cl_marks', 'execute')
        g.comment('Marks, ring and glyph', ['cl_marks'])
        g.run()
    nodes, edges = inspect(WBP, 'RedrawAll')
    if not any(n['title'] == 'ShowCards' for n in nodes):
        entry = next(n['node_id'] for n in nodes if n['title'] == 'RedrawAll')
        (first, fpin), = [(e['to_node'], e['to_pin']) for e in edges if e['from_node'] == entry and e['from_pin'] == 'then']
        g = Batch(WBP, 'RedrawAll')
        g.fn('cl_cards', WC + ':ShowCards', 200, 400)
        g.cut(entry, 'then', first, fpin)
        g.link(entry, 'then', 'cl_cards', 'execute')
        g.link('cl_cards', 'then', first, fpin)
        g.comment('Cards on the player turn', ['cl_cards'])
        g.run()
        nodes, edges = inspect(WBP, 'RedrawAll')
    if not any(n['title'] == 'MinimalLog' for n in nodes):
        last = next(n['node_id'] for n in nodes if n['title'] == 'RefreshL2ProgressContext')
        assert not [e for e in edges if e['from_node'] == last and e['from_pin'] == 'then']
        g = Batch(WBP, 'RedrawAll')
        g.fn('cl_log', WC + ':MinimalLog', 1800, 400)
        g.link(last, 'then', 'cl_log', 'execute')
        g.comment('One line at a time', ['cl_log'])
        g.run()


def selftest():
    nodes = [dict(node_id='a', title='Get EnemyPanel', pins=[]),
             dict(node_id='b', title='SetVisibility', pins=[dict(name='InVisibility', default_value='Visible')]),
             dict(node_id='c', title='SetVisibility', pins=[dict(name='InVisibility', default_value='Collapsed')])]
    edges = [dict(from_node='a', from_pin='EnemyPanel', to_node='b', to_pin='self'),
             dict(from_node='a', from_pin='EnemyPanel', to_node='c', to_pin='self')]
    assert visibility_nodes(nodes, edges, 'Get EnemyPanel', 'Visible') == ['b']
    assert visibility_nodes(nodes, edges, 'Get EnemyPanel', 'Hidden') == []
    print('selftest ok')


if __name__ == '__main__':
    {'screen': screen, 'tree': tree, 'declare': declare, 'bodies': bodies, 'lengths': lengths, 'hook': hook,
     'selftest': selftest}[sys.argv[1]]()
