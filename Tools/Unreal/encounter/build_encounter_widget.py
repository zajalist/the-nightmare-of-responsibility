"""WBP_Encounter graph (the designer tree comes from gen_encounter_tree.py via Hayba ui_build_tree). Run via ue_remote.py.
The widget owns no rules: it re-reads BP_Encounter on OnChanged, shows OnDamage numbers, and its buttons call the
encounter's public functions. No Tick: the key window bar runs on a short looping timer only while a prompt is open.
  Construct           bind OnChanged, OnDamage and the eight buttons, then draw once
  Redraw              RefreshEnemies, RefreshSelf, RefreshCommands, RefreshPrompt
  SetPips(Row, Lit, Shown)  Shown pips visible, the first Lit of them bright
  MoveLabel(Move)     "Button Up (10 Resolve)", or the name alone when free
  ShowDamage(Who, Amount)   a number floats over whoever was hit for 0.9 s

Production UI postpasses (after the existing battle_presentation/refine_battle_ui passes):
  1. Ensure BP_Encounter.MoveDetail is built and compiled.
  2. Run read_battle_feedback.py read-only, then native redesign_battle_choices.py.
  3. Refresh read_battle_feedback.py, then refine_battle_choices_readability.py.
  4. Refresh read_battle_feedback.py, then bind_recovery_details.py.
These preserve the actual buttons and their handlers. The legacy graph pass alone expects
direct ActButtons children and must not be run over the shipped card tree without these
postpasses. Verify with pie_battle_feedback_check.py and actual 960px captures afterwards.
"""
import unreal

exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read())
WBP = f'{ENC}/WBP_Encounter'
WSELF = lambda f: self_call(WBP, f)  # noqa: E731
BP_C = f'{ENC}/BP_Encounter.BP_Encounter_C'
G_C = f'{ENC}/BP_Garment.BP_Garment_C'
SB_C = '/Game/FoA/UI/Widgets/Common/WBP_SandButton.WBP_SandButton_C'
TB, W, PW, PB = ('/Script/UMG.' + c for c in ('TextBlock', 'Widget', 'PanelWidget', 'ProgressBar'))
SHOW, HIDE = 'HitTestInvisible', 'Collapsed'


def T(name):
    return BEL.get_basic_type_by_name(name)


def band(g, y0, y1, x0=-10 ** 6, x1=10 ** 6):
    return [n for n in g.ed.list_all_nodes() if y0 <= BEL.get_node_pos(n).y < y1 and x0 <= BEL.get_node_pos(n).x < x1]


def enc(g, x, y):
    return mget(g, 'Encounter', x, y)


def ef(g, var, x, y, src=None):
    """Encounter.var"""
    return field(g, src if src is not None else enc(g, x - 200, y), var, BP_C, x, y)


def set_text(g, target, x, y, src):
    tgt = mget(g, target, x - 220, y + 200) if isinstance(target, str) else target
    return fcall(g, f'{TB}:SetText', x, y, self=tgt, InText=src)


def int_text(g, src, x, y):
    return fcall(g, '/Script/Engine.KismetTextLibrary:Conv_IntToText', x, y, Value=src)


def child(g, panel, index, cls_needle, x, y):
    """panel.GetChildAt(index) cast to a widget class (impure cast); returns (cast, as-pin)."""
    ga = fcall(g, f'{PW}:GetChildAt', x, y + 160, self=panel, Index=index)
    cast = make(g, x + 260, y, cls_needle)
    wire(po(ga), pi(cast, 'Object'))
    out = [p for p in BEL.list_output_pins(cast) if str(PIN.get_pin_name(p)).startswith('As')][0]
    return cast, out


def sigs():
    move = BEL.get_object_reference_type(unreal.load_class(None, MOVE_C))
    I = T('int')
    return {'SetPips': ((('Row', BEL.get_object_reference_type(unreal.PanelWidget)), ('Lit', I), ('Shown', I),
                         ('Index', I)), (), False),
            'MoveLabel': ((('Move', move),), (('Label', T('text')),), True),
            'ShowDamage': ((('Who', BEL.get_object_reference_type(unreal.Actor)), ('Amount', I)), (), False),
            'RefreshRow': ((('Index', I),), (), False), 'RefreshEnemies': ((), (), False),
            'AddStatusLine': ((('Index', I),), (), False), 'RefreshSelf': ((), (), False),
            'RefreshAct': ((('Index', I),), (), False), 'RefreshCommands': ((), (), False),
            'RefreshPrompt': ((), (), False), 'RedrawAll': ((), (), False)}


def stubs():
    """Variables and empty function graphs, so one Hayba ui_compile_widget makes them callable before 'graph'."""
    bp = unreal.load_asset(WBP)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    ensure_vars_nc(WBP, [('Encounter', BEL.get_object_reference_type(unreal.load_class(None, BP_C)), '', 'Encounter',
                          True, True),
                         ('WindowTimer', BEL.get_struct_type(unreal.TimerHandle.static_struct()), '', 'Encounter|State',
                          False),
                         ('StatusLines', BEL.get_array_type(T('string')), '', 'Encounter|State', False)])
    stub_functions(WBP, sigs())
    print('widget stubs ok: now Hayba ui_compile_widget')


def main():
    bp = unreal.load_asset(WBP)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    move = BEL.get_object_reference_type(unreal.load_class(None, MOVE_C))

    # SetPips(Row, Lit, Shown, Index): recursive index counter over the row's children (no loop macros)
    g, e, _ = new_function(WBP, 'SetPips', [('Row', BEL.get_object_reference_type(unreal.PanelWidget)),
                                            ('Lit', T('int')), ('Shown', T('int')), ('Index', T('int'))])
    g.at(e, 0, 0)
    row, idx = po(e, 'Row'), po(e, 'Index')
    br = g.at(g.ed.add_branch_node(), 300, 0)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 60, 300, A=idx, B=fcall(g, f'{PW}:GetChildrenCount', -180, 300, self=row))),
         BEL.find_condition_pin(br))
    el = po(fcall(g, f'{PW}:GetChildAt', 300, 420, self=row, Index=idx))
    op = fcall(g, f'{KML}:SelectFloat', 560, 300, A=1.0, B=0.22,
               bPickA=fcall(g, f'{KML}:Less_IntInt', 360, 560, A=idx, B=po(e, 'Lit')))
    so = fcall(g, f'{W}:SetRenderOpacity', 800, 0, self=el, InOpacity=op)
    br2 = g.at(g.ed.add_branch_node(), 1060, 0)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 860, 300, A=idx, B=po(e, 'Shown'))), BEL.find_condition_pin(br2))
    on = fcall(g, f'{W}:SetVisibility', 1320, -120, self=el, InVisibility=SHOW)
    off = fcall(g, f'{W}:SetVisibility', 1320, 140, self=el, InVisibility=HIDE)
    nxt = fcall(g, WSELF('SetPips'), 1640, 0, Row=row, Lit=po(e, 'Lit'), Shown=po(e, 'Shown'),
                Index=fcall(g, f'{KML}:Add_IntInt', 1440, 300, A=idx, B=1))
    go(e, br)
    go(br, so)
    go(so, br2)
    go(br2, on)
    go(br2, off, 'else')
    go(on, nxt)
    go(off, nxt)
    box(g, 'Pips (index counter)', 'Pip Index is shown if Index < Shown (the Resistance) and bright if Index < Lit '
        '(progress made, keys hit); then the next pip.', g.ed.list_all_nodes(), 'stage')

    # MoveLabel(Move) -> Label
    g, e, r = new_function(WBP, 'MoveLabel', [('Move', move)], [('Label', T('text'))], pure=True)
    g.at(e, 0, 0)
    name = field(g, po(e, 'Move'), 'DisplayName', MOVE_C, 300, 260)
    cost = fcall(g, f'{BP_C}:MoveCost', 300, 400, self=enc(g, 60, 440), Move=po(e, 'Move'))
    br = g.at(g.ed.add_branch_node(), 860, 0)
    wire(po(fcall(g, f'{KML}:Greater_IntInt', 600, 320, A=po(cost, 'Cost'), B=0)), BEL.find_condition_pin(br))
    fmt = make(g, 860, 300, 'Format Text')
    val(fmt, 'Format', '{Name} ({Cost} Resolve)')
    wire(po(name), pi(fmt, 'Name'))
    wire(po(cost, 'Cost'), pi(fmt, 'Cost'))
    g.at(r, 1260, -140)
    feed(r, Label=po(fmt))
    r2 = g.at(g.ed.add_return_node(), 1260, 180)
    wire(po(name), pi(r2, 'Label'))
    go(e, br)
    go(br, r)
    go(br, r2, 'else')
    box(g, 'Move label', 'Name and Resolve cost, or just the name when the move is free (a free preview included).',
        g.ed.list_all_nodes(), 'data')

    # ShowDamage(Who, Amount) + HideDamage
    g, e, _ = new_function(WBP, 'ShowDamage', [('Who', BEL.get_object_reference_type(unreal.Actor)),
                                               ('Amount', T('int'))])
    g.at(e, 0, 0)
    above = fcall(g, f'{KML}:Add_VectorVector', 300, 300, A=fcall(g, '/Script/Engine.Actor:K2_GetActorLocation', 60, 300,
                                                                    self=po(e, 'Who')), B='(X=0,Y=0,Z=170)')
    proj = fcall(g, '/Script/UMG.WidgetLayoutLibrary:ProjectWorldLocationToWidgetPosition', 560, 300,
                 PlayerController=fcall(g, '/Script/UMG.UserWidget:GetOwningPlayer', 300, 460),
                 WorldLocation=above, bPlayerViewportRelative='false')
    fmt = make(g, 560, 560, 'Format Text')
    val(fmt, 'Format', '{Sign}{N}')
    wire(po(e, 'Amount'), pi(fmt, 'N'))
    sign = fcall(g, '/Script/Engine.KismetTextLibrary:Conv_StringToText', 300, 680,
                 InString=fcall(g, f'{KML}:SelectString', 60, 680, A='+', B='',
                                bPickA=fcall(g, f'{KML}:Greater_IntInt', -180, 680, A=po(e, 'Amount'), B=0)))
    wire(po(sign), pi(fmt, 'Sign'))
    st = set_text(g, 'Txt_Damage', 900, 0, po(fmt))
    tr = fcall(g, f'{W}:SetRenderTranslation', 1200, 0, self=mget(g, 'Txt_Damage', 1000, 200),
               Translation=po(proj, 'ScreenPosition'))
    vis = fcall(g, f'{W}:SetVisibility', 1500, 0, self=mget(g, 'Txt_Damage', 1300, 200), InVisibility=SHOW)
    tm = fcall(g, f'{KSL}:K2_SetTimer', 1800, 0, FunctionName='HideDamage', Time=0.9, bLooping='false')
    chain(e, st, tr, vis, tm)
    box(g, 'Damage number', 'Progress (+) or harm (-) floats over whoever was hit, then clears after 0.9 s.',
        g.ed.list_all_nodes(), 'stage')

    # RefreshRow(Index): recursive index counter: row Index shows garment Index, spare rows collapse
    g, e, _ = new_function(WBP, 'RefreshRow', [('Index', T('int'))])
    g.at(e, 0, 0)
    E = enc(g, 0, 400)
    i = po(e, 'Index')
    gars = ef(g, 'Garments', 200, 520, E)
    rows = mget(g, 'EnemyRows', 0, 260)
    brn = g.at(g.ed.add_branch_node(), 300, 0)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 200, 160, A=i, B=fcall(g, f'{PW}:GetChildrenCount', 0, 160, self=rows))),
         BEL.find_condition_pin(brn))
    row = fcall(g, f'{PW}:GetChildAt', 600, 260, self=rows, Index=i)
    br = g.at(g.ed.add_branch_node(), 860, 0)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 600, 420, A=i, B=fcall(g, f'{KAL}:Array_Length', 400, 520, TargetArray=gars))),
         BEL.find_condition_pin(br))
    hide = fcall(g, f'{W}:SetVisibility', 1120, 260, self=po(row), InVisibility=HIDE)
    show = fcall(g, f'{W}:SetVisibility', 1120, -120, self=po(row), InVisibility=SHOW)
    gm = po(fcall(g, f'{KAL}:Array_Get', 860, 560, TargetArray=gars, Index=i), 'Item')
    data = field(g, gm, 'Data', G_C, 1120, 560)
    focus = fcall(g, f'{KML}:SelectFloat', 1380, 420, A=1.0, B=0.5,
                  bPickA=fcall(g, f'{KML}:EqualEqual_IntInt', 1120, 420, A=i, B=ef(g, 'Target', 900, 420, E)))
    op = fcall(g, f'{W}:SetRenderOpacity', 1640, -120, self=po(row), InOpacity=focus)
    rowbox = make(g, 1900, -120, 'CastToVerticalBox')
    wire(po(row), pi(rowbox, 'Object'))
    rb = as_pin(rowbox)
    c0, t0 = child(g, rb, 0, 'CastToTextBlock', 2200, -120)
    n0 = set_text(g, t0, 2780, -120, field(g, data, 'DisplayName', OPP_C, 2560, 160))
    c1, p1 = child(g, rb, 1, 'CastToPanelWidget', 3060, -120)
    pips = fcall(g, WSELF('SetPips'), 3640, -120, Row=p1, Lit=field(g, gm, 'Progress', G_C, 3400, 160),
                 Shown=field(g, data, 'Resistance', OPP_C, 3400, 280), Index=0)
    c2, t2 = child(g, rb, 2, 'CastToTextBlock', 3920, -120)
    line = fcall(g, f'{G_C}:StatusLine', 4280, 200, self=gm, bRevealed=ef(g, 'bRevealed', 4060, 340, E))
    n2 = set_text(g, t2, 4500, -120, po(line, 'Line'))
    nxt = fcall(g, WSELF('RefreshRow'), 4800, 120, Index=fcall(g, f'{KML}:Add_IntInt', 4600, 360, A=i, B=1))
    go(e, brn)
    go(brn, br)
    go(br, show)
    go(br, hide, 'else')
    chain(show, op, rowbox, c0, n0, c1, pips, c2, n2, nxt)
    go(hide, nxt)
    box(g, 'Enemy row (index counter)', 'Row Index shows garment Index: name, progress pips (Resistance shown) and its '
        'status line; the target at full strength, the rest dimmed; spare rows collapse. Then the next row.',
        g.ed.list_all_nodes(), 'stage')

    g, e, _ = new_function(WBP, 'RefreshEnemies')
    g.at(e, 0, 0)
    first = fcall(g, WSELF('RefreshRow'), 300, 0, Index=0)
    go(e, first)
    box(g, 'Enemy line', 'From the first row.', g.ed.list_all_nodes(), 'stage')

    # AddStatusLine(Index): recursive index counter: the label of status Index joins StatusLines
    g, e, _ = new_function(WBP, 'AddStatusLine', [('Index', T('int'))])
    g.at(e, 0, 0)
    E = enc(g, -200, 300)
    st = ef(g, 'Statuses', 0, 300, E)
    br = g.at(g.ed.add_branch_node(), 300, 0)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 260, 300, A=po(e, 'Index'),
                  B=fcall(g, f'{KAL}:Array_Length', 60, 420, TargetArray=st))), BEL.find_condition_pin(br))
    lab = fcall(g, f'{BML}:Map_Find', 600, 300, TargetMap=ef(g, 'StatusLabels', 400, 460, E),
                Key=po(fcall(g, f'{KAL}:Array_Get', 400, 300, TargetArray=st, Index=po(e, 'Index')), 'Item'))
    add = fcall(g, f'{KAL}:Array_Add', 1100, 0, TargetArray=mget(g, 'StatusLines', 880, 200),
                NewItem=fcall(g, '/Script/Engine.KismetTextLibrary:Conv_TextToString', 860, 320, InText=po(lab, 'Value')))
    nxt = fcall(g, WSELF('AddStatusLine'), 1400, 0, Index=fcall(g, f'{KML}:Add_IntInt', 1200, 260, A=po(e, 'Index'), B=1))
    go(e, br)
    go(br, add)
    go(add, nxt)
    box(g, 'Status line (index counter)', 'Status Index by its StatusLabels text, then the next.', g.ed.list_all_nodes(),
        'stage')

    # RefreshSelf(): Composure, Resolve, statuses, narration
    g, e, _ = new_function(WBP, 'RefreshSelf')
    g.at(e, 0, 0)
    E = enc(g, 0, 300)
    L = ef(g, 'Leader', 200, 460, E)
    prev, x = e, 380
    for stat, start in (('Composure', 'StartComposure'), ('Resolve', 'StartResolve')):
        v = ef(g, stat, x - 120, 300, E)
        st = set_text(g, f'Txt_{stat}', x + 140, 0, int_text(g, v, x + 100, 420))
        frac = fcall(g, f'{KML}:Divide_DoubleDouble', x + 560, 380,
                     A=fcall(g, f'{KML}:Conv_IntToDouble', x + 360, 520, InInt=v),
                     B=fcall(g, f'{KML}:Conv_IntToDouble', x + 360, 640, InInt=field(g, L, start, OPP_C, x + 120, 640)))
        sp = fcall(g, f'{PB}:SetPercent', x + 800, 0, self=mget(g, f'Bar_{stat}', x + 600, 220), InPercent=frac)
        chain(prev, st, sp)
        prev, x = sp, x + 1100
    sn = set_text(g, 'Txt_Narration', x + 200, 0, ef(g, 'Narration', x, 300, E))
    go(prev, sn)
    X = x + 600
    box(g, 'The Nightmare', 'Composure and Resolve as numbers and bars, and the battle log line.',
        band(g, -200, 900, x1=X - 100), 'stage')
    clr = fcall(g, f'{KAL}:Array_Clear', X, 0, TargetArray=mget(g, 'StatusLines', X - 200, 200))
    lines = fcall(g, WSELF('AddStatusLine'), X + 260, 0, Index=0)
    join = fcall(g, '/Script/Engine.KismetStringLibrary:JoinStringArray', X + 560, 300,
                 SourceArray=mget(g, 'StatusLines', X + 340, 300), Separator='\n')
    ss = set_text(g, 'Txt_Statuses', X + 820, 0,
                  fcall(g, '/Script/Engine.KismetTextLibrary:Conv_StringToText', X + 800, 300, InString=join))
    chain(sn, clr, lines, ss)
    box(g, 'Statuses', 'Each active status by its StatusLabels line, one per line (the UI lane may turn these into icons).',
        band(g, -200, 900, x0=X - 240), 'stage')

    # RefreshAct(Index): recursive index counter over the Act buttons: the target's Act move Index, or collapsed
    g, e, _ = new_function(WBP, 'RefreshAct', [('Index', T('int'))])
    g.at(e, 0, 0)
    E = enc(g, 0, 400)
    i = po(e, 'Index')
    btns = mget(g, 'ActButtons', 0, 260)
    brn = g.at(g.ed.add_branch_node(), 300, 0)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 200, 160, A=i, B=fcall(g, f'{PW}:GetChildrenCount', 0, 160, self=btns))),
         BEL.find_condition_pin(brn))
    acts = field(g, field(g, po(fcall(g, f'{BP_C}:TargetGarment', 200, 520, self=E), 'Garment'), 'Data', G_C, 420, 520),
                 'ActMoves', OPP_C, 640, 520)
    cast = make(g, 600, 0, 'CastToWBP_SandButton')
    wire(po(fcall(g, f'{PW}:GetChildAt', 400, 260, self=btns, Index=i)), pi(cast, 'Object'))
    btn = as_pin(cast)
    br = g.at(g.ed.add_branch_node(), 1180, 0)
    wire(po(fcall(g, f'{KML}:Less_IntInt', 960, 300, A=i, B=fcall(g, f'{KAL}:Array_Length', 860, 440, TargetArray=acts))),
         BEL.find_condition_pin(br))
    show = fcall(g, f'{W}:SetVisibility', 1440, -120, self=btn, InVisibility='Visible')
    hide = fcall(g, f'{W}:SetVisibility', 1440, 200, self=btn, InVisibility=HIDE)
    mv = po(fcall(g, f'{KAL}:Array_Get', 1180, 440, TargetArray=acts, Index=i), 'Item')
    setl = fcall(g, f'{SB_C}:SetLabel', 1720, -120, self=btn,
                 NewLabel=po(fcall(g, WSELF('MoveLabel'), 1460, 420, Move=mv), 'Label'))
    en = fcall(g, f'{W}:SetIsEnabled', 2280, -120, self=btn,
               bInIsEnabled=fcall(g, f'{KML}:BooleanAND', 2000, 300, A=ef(g, 'bPlayerTurn', 1800, 560, E),
                                  B=po(fcall(g, f'{BP_C}:CanUseMove', 1720, 420, self=E, Move=mv), 'bCan')))
    nxt = fcall(g, WSELF('RefreshAct'), 2600, 60, Index=fcall(g, f'{KML}:Add_IntInt', 2400, 300, A=i, B=1))
    go(e, brn)
    go(brn, cast)
    go(cast, br)
    go(br, show)
    go(br, hide, 'else')
    chain(show, setl, en, nxt)
    go(hide, nxt)
    box(g, 'Act button (index counter)', 'Button Index plays the target\'s Act move Index with its cost, enabled on the '
        'player\'s turn when Resolve and statuses allow; spare buttons collapse. Then the next.', g.ed.list_all_nodes(),
        'entry')

    # RefreshCommands(): the target, its Act moves, and the command buttons
    g, e, _ = new_function(WBP, 'RefreshCommands')
    g.at(e, 0, 0)
    E = enc(g, 0, 400)
    turn = ef(g, 'bPlayerTurn', 200, 640, E)
    tg = po(fcall(g, f'{BP_C}:TargetGarment', 200, 520, self=E), 'Garment')
    tt = set_text(g, 'Txt_Target', 300, 0, field(g, field(g, tg, 'Data', G_C, 420, 520), 'DisplayName', OPP_C, 640, 300))
    acts = fcall(g, WSELF('RefreshAct'), 600, 0, Index=0)
    chain(e, tt, acts)
    X = 1000
    box(g, 'Act', 'The target by name, then its Act buttons.', band(g, -300, 900, x1=X - 100), 'entry')
    prev = acts
    for k, (btn_name, mvar) in enumerate((('Btn_Breathe', 'BreatheMove'), ('Btn_Mirror', 'MirrorMove'),
                                          ('Btn_Items', None), ('Btn_Flee', None), ('Btn_NextTarget', None))):
        x = X + k * 300
        ok = po(fcall(g, f'{KML}:BooleanAND', x, 300, A=turn,
                      B=po(fcall(g, f'{BP_C}:CanUseMove', x - 40, 440, self=E, Move=ef(g, mvar, x - 40, 580, E)),
                           'bCan'))) if mvar else turn
        en = fcall(g, f'{W}:SetIsEnabled', x, 0, self=mget(g, btn_name, x - 40, 160), bInIsEnabled=ok)
        go(prev, en)
        prev = en
    box(g, 'Commands', 'Breathe and Mirror when usable; Items, Flee and Next target on the player\'s turn.',
        band(g, -300, 900, x0=X - 100), 'entry')

    # RedrawAll(): every part of the screen, from the encounter's current state
    g, e, _ = new_function(WBP, 'RedrawAll')
    g.at(e, 0, 0)
    r = [fcall(g, WSELF(f), 300 + k * 280, 0) for k, f in enumerate(('RefreshEnemies', 'RefreshSelf', 'RefreshCommands',
                                                                     'RefreshPrompt'))]
    chain(e, *r)
    box(g, 'Redraw everything', 'The enemy line, the Nightmare, the commands and the key prompt.', g.ed.list_all_nodes(),
        'stage')

    # RefreshPrompt(): the key to press, keys hit so far, and the window bar's timer
    g, e, _ = new_function(WBP, 'RefreshPrompt')
    g.at(e, 0, 0)
    E = enc(g, 0, 320)
    br = g.at(g.ed.add_branch_node(), 300, 0)
    wire(po(ef(g, 'bAwaitingKey', 100, 440, E)), BEL.find_condition_pin(br))
    on = fcall(g, f'{W}:SetVisibility', 600, -120, self=mget(g, 'PromptBox', 400, -240), InVisibility=SHOW)
    off = fcall(g, f'{W}:SetVisibility', 600, 160, self=mget(g, 'PromptBox', 400, 300), InVisibility=HIDE)
    key = fcall(g, f'{KAL}:Array_Get', 860, 300, TargetArray=ef(g, 'InputKeys', 660, 400, E),
                Index=ef(g, 'InputIndex', 660, 520, E))
    kname = fcall(g, f'{KIL}:Key_GetDisplayName', 1100, 300, Key=po(key, 'Item'), bLongDisplayName='false')
    sk = set_text(g, 'Txt_PromptKey', 1360, -120, kname)
    pips = fcall(g, WSELF('SetPips'), 1680, -120, Row=mget(g, 'Pips_Hits', 1480, 160),
                 Lit=ef(g, 'InputHits', 1480, 280, E), Shown=3, Index=0)
    tm = fcall(g, f'{KSL}:K2_SetTimer', 2000, -120, FunctionName='TickWindow', Time=0.033, bLooping='true')
    st = mset(g, 'WindowTimer', 2320, -120, po(tm, 'ReturnValue'))
    clr = fcall(g, f'{KSL}:K2_ClearAndInvalidateTimerHandle', 900, 160, Handle=mget(g, 'WindowTimer', 700, 440))
    go(e, br)
    go(br, on)
    go(br, off, 'else')
    chain(on, sk, pips, tm, st)
    go(off, clr)
    box(g, 'Key prompt', 'While the encounter waits for a key: show it, light the hits so far and run the window bar at '
        '30 Hz; otherwise hide it and stop the timer.', g.ed.list_all_nodes(), 'input')

    # Event graph
    g = Graph(WBP).clear()
    con = g.event('Construct', 0, 0)
    src = mget(g, 'Encounter', 0, 220)
    bind, redraw = bind_event(g, src, 'Encounter', 'OnChanged', 'Redraw', 320, 0)
    go(con, bind)
    # OnDamage(Who, Amount) -> ShowDamage through a Create Event node (signature comes from the function)
    src2 = mget(g, 'Encounter', 640, 220)
    names = [n for n in g.ed.list_available_nodes([po(src2)]) if n.lower().replace(' ', '').endswith('bindeventtoondamage')]
    bind2 = g.at(g.ed.create_node_from_name(names[0], unreal.Vector2D(700, 0), [po(src2)]), 700, 0)
    if not PIN.list_connected_pins(pi(bind2, 'self')):
        wire(po(src2), pi(bind2, 'self'))
    mk = make(g, 640, 360, 'Create Event')
    BEL.set_create_delegate_function(mk, 'ShowDamage')
    wire(po(mk, 'OutputDelegate'), pi(bind2, 'Delegate'))
    go(bind, bind2)
    prev, handlers = bind2, []
    buttons = [f'Btn_Act{i}' for i in range(3)] + ['Btn_Breathe', 'Btn_Mirror', 'Btn_Items', 'Btn_Flee', 'Btn_NextTarget']
    for k, b in enumerate(buttons):
        x = 1100 + k * 420
        s = mget(g, b, x - 60, 220)
        bnd, h = bind_event(g, s, b, 'OnSandClicked', f'On{b[4:]}', x, 0)
        go(prev, bnd)
        prev = bnd
        handlers.append((b, h))  # the Redraw event must exist on the class before a node can call it
    first = fcall(g, WSELF('RedrawAll'), 1100 + len(buttons) * 420, 0)
    go(prev, first)
    box(g, 'Bind once', 'Listen to the encounter (OnChanged, OnDamage) and the eight buttons, then draw the first frame.',
        band(g, -200, 520), 'entry')
    y = 640
    g.at(redraw, 0, y)
    r = [fcall(g, WSELF('RedrawAll'), 320, y)]
    chain(redraw, *r)
    box(g, 'Redraw on change', 'BP_Encounter broadcasts OnChanged after every state change; the widget re-reads it.',
        band(g, y - 100, y + 300), 'stage')
    y = 1040
    hn = []
    for k, (b, h) in enumerate(handlers):
        yy = y + k * 200
        g.at(h, 0, yy)
        E = enc(g, 300, yy + 120)
        if b.startswith('Btn_Act'):
            acts = field(g, field(g, po(fcall(g, f'{BP_C}:TargetGarment', 300, yy + 120, self=E), 'Garment'), 'Data', G_C,
                                  560, yy + 120), 'ActMoves', OPP_C, 780, yy + 120)
            c = fcall(g, f'{BP_C}:ChooseMove', 1300, yy, self=E,
                      Move=po(fcall(g, f'{KAL}:Array_Get', 1040, yy + 120, TargetArray=acts, Index=int(b[-1])), 'Item'))
        elif b in ('Btn_Breathe', 'Btn_Mirror'):
            c = fcall(g, f'{BP_C}:ChooseMove', 1300, yy, self=E,
                      Move=ef(g, 'BreatheMove' if b == 'Btn_Breathe' else 'MirrorMove', 1040, yy + 120, E))
        elif b == 'Btn_NextTarget':
            c = fcall(g, f'{BP_C}:CycleTarget', 1040, yy, self=E, Direction=1)
            c2 = fcall(g, WSELF('RedrawAll'), 1300, yy)
            go(c, c2)
        else:
            c = fcall(g, f'{BP_C}:{b[4:]}', 1300, yy, self=E)
            if b == 'Btn_Items':
                feedback = set_text(g, 'Txt_Narration', 1620, yy, ef(g, 'Narration', 1420, yy + 160, E))
                go(c, feedback)
        go(h, c)
    box(g, 'Buttons', 'Act i plays the target\'s Act move i; Breathe and Mirror play the encounter\'s moves; Items and '
        'Flee call the encounter; Next target cycles it.', band(g, y - 100, y + 200 * len(handlers)), 'entry')
    x = 1800
    tw = g.custom_event('TickWindow', x, y)
    E = enc(g, x, y + 220)
    left = fcall(g, f'{KSL}:K2_GetTimerRemainingTimeHandle', x + 280, y + 220, Handle=ef(g, 'KeyTimer', x + 280, y + 380, E))
    frac = fcall(g, f'{KML}:Divide_DoubleDouble', x + 580, y + 220, A=po(left), B=ef(g, 'ActiveWindow', x + 380, y + 500, E))
    sp = fcall(g, f'{PB}:SetPercent', x + 820, y, self=mget(g, 'Bar_Window', x + 620, y + 120), InPercent=frac)
    go(tw, sp)
    hd = g.custom_event('HideDamage', x, y + 700)
    hv = fcall(g, f'{W}:SetVisibility', x + 300, y + 700, self=mget(g, 'Txt_Damage', x + 100, y + 900), InVisibility=HIDE)
    go(hd, hv)
    box(g, 'Timers', 'TickWindow drains the key window bar while a prompt is open; HideDamage clears the number.',
        band(g, y - 100, y + 1100, x0=x - 40), 'input')
    print('widget graph ok: now Hayba ui_compile_widget and asset_save')


import os  # noqa: E402
{'stubs': stubs, 'graph': main}[os.environ.get('FOA_PHASE', 'stubs')]()
