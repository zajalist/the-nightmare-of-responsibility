"""Graphs for the front-end screens (run via ue_remote.py; FOA_WIDGETS=Splash,Title,MainMenu,InputHint to subset).
Every screen finds BP_FoAFrontEnd once in Construct (Host) and calls one intent function on it."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
import os
import unreal

M = '/Game/FoA/UI/Widgets/Menus'
FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
FE_C = FE + '.BP_FoAFrontEnd_C'
KML = '/Script/Engine.KismetMathLibrary'
UWBL = '/Script/UMG.WidgetBlueprintLibrary'
HOST_T = ptype(unreal.load_class(None, FE_C))
SPLAT = bool(unreal.EditorAssetLibrary.does_asset_exist('/Game/FoA/UI/Materials/MI_UI_SplatLogo_Hayba'))
ONLY = [s for s in os.environ.get('FOA_WIDGETS', 'Splash,Title,MainMenu,InputHint').split(',') if s]


def host_var(path):
    ensure_vars(path, [('Host', HOST_T, '', 'Screen', False)])


def construct_with_host(g, y=0, extra=()):
    con = g.event('Construct', 0, y)
    find, cast, seth = host_lookup(g, FE_C, 256, y)
    g.link(con, 'then', find, 'execute')
    return con, find, cast, seth


def override_handled(path, name, call_target, y_comment):
    """OnKeyDown / OnMouseButtonDown override: call one function, then return Handled. Reuses the existing override."""
    g = override_graph(path, name)
    if g is None:
        return
    e = g.at(entry_node(g), 0, 0)
    ret = g.ed.list_nodes_of_class(unreal.K2Node_FunctionResult)[0]
    call, host = call_target(g)
    handled = g.call(f'{UWBL}:Handled', 576, 160)
    g.at(ret, 896, 0)
    g.exec_chain(e, call); g.link(call, 'then', ret, 'execute'); g.link(handled, 'ReturnValue', ret, 'ReturnValue')
    g.comment(words(name), y_comment, [e, call, host, handled, ret], C_EVENT)


def host_call(func):
    def make(g):
        host = g.get('Host', 224, 160)
        call = g.call(f'{FE_C}:{func}', 288, 0)
        g.link(host, 'Host', call, 'self')
        return call, host
    return make


# ------------------------------------------------------------------ Splash
if 'Splash' in ONLY:
    P_ = f'{M}/WBP_BootSplash'
    host_var(P_)
    ensure_vars(P_, [('Elapsed', ptype('real'), '0.0', 'Splash|State', False),
                     ('LastReal', ptype('real'), '0.0', 'Splash|State', False),
                     ('HaybaMID', ptype(unreal.MaterialInstanceDynamic), '', 'Splash|State', False),
                     ('bFinished', ptype('bool'), 'false', 'Splash|State', False),
                     ('CardSeconds', ptype('real'), '2.0', 'Splash', True),     # AAA pass: 0.2 black, 0.5 in, 0.9 hold, 0.4 out
                     ('FinishAt', ptype('real'), '6.0', 'Splash', True),        # title at 6.1 s (clock starts at -0.1)
                     ('CardCount', ptype('int'), '3', 'Splash', True),
                     ('CueIndex', ptype('int'), '0', 'Splash|State', False),          # next sound cue (2 per card)
                     ('NextCueTime', ptype('real'), '0.2', 'Splash|State', False)])  # when it fires (first fade-up)
    for f in ('UpdateSplash', 'SkipCard', 'CheckCue'):
        drop_function(P_, f)
    Graph.function(P_, 'UpdateSplash'); Graph.function(P_, 'SkipCard'); Graph.function(P_, 'CheckCue')
    f = Graph(P_, 'UpdateSplash')
    e = f.at(entry_node(f), 0, 0)
    el = f.get('Elapsed', 160, 160)
    # real time since the last step (a fixed 0.0333 per timer call drifted: the boot ran ~12% fast against the page)
    now = f.call('/Script/Engine.GameplayStatics:GetRealTimeSeconds', 0, 352)
    lr = f.get('LastReal', 0, 432)
    dtr = f.call(f'{KML}:Subtract_DoubleDouble', 160, 352)
    dtc = f.call(f'{KML}:FClamp', 288, 352, Min=0.0, Max=0.1)
    setlr = f.set('LastReal', 800, 0)  # after Set Elapsed: set first, now - LastReal was 0 and the clock never moved
    add = f.call(f'{KML}:Add_DoubleDouble', 416, 160)
    sete = f.set('Elapsed', 544, 0)
    f.link(now, 'ReturnValue', dtr, 'A'); f.link(lr, 'LastReal', dtr, 'B'); f.link(dtr, 'ReturnValue', dtc, 'Value')
    f.link(dtc, 'ReturnValue', add, 'B'); f.link(now, 'ReturnValue', setlr, 'LastReal')
    per = f.get('CardSeconds', 736, 288)
    div = f.call(f'{KML}:Divide_DoubleDouble', 800, 160)
    card = f.call(f'{KML}:FTrunc', 1024, 160)
    cnt = f.get('CardCount', 1024, 288)
    last = f.call(f'{KML}:Subtract_IntInt', 1216, 288, B=1)
    clamp = f.call(f'{KML}:Min', 1408, 160)
    sw = f.get('Switch_Cards', 1408, 32)
    seti = f.call('/Script/UMG.WidgetSwitcher:SetActiveWidgetIndex', 1664, 0)
    # Film opening per card (page v3.1): black 0.85 s, fade up 1.3 s, hold, fade to black over the last 1.2 s
    # card time = Elapsed - card x CardSeconds (not Elapsed % CardSeconds: on the clamped last card the modulo wrapped and
    # the Hayba card faded in a second time before the title, the user's "it fades twice")
    cidx = f.call(f'{KML}:Conv_IntToDouble', 800, 576)
    cstart = f.call(f'{KML}:Multiply_DoubleDouble', 800, 640)
    rem = f.call(f'{KML}:Subtract_DoubleDouble', 800, 448)
    up = f.call(f'{KML}:Subtract_DoubleDouble', 1024, 448, B=0.2)
    upn = f.call(f'{KML}:Divide_DoubleDouble', 1216, 448, B=0.5)
    left0 = f.call(f'{KML}:Subtract_DoubleDouble', 1024, 576)
    left = f.call(f'{KML}:Divide_DoubleDouble', 1216, 576, B=0.4)
    near = f.call(f'{KML}:FMin', 1408, 448)
    vis0 = f.call(f'{KML}:FClamp', 1600, 448, Min=0.0, Max=1.0)
    vis = f.call(f'{KML}:Ease', 1700, 520, A=0.0, B=1.0, EasingFunc='EaseOut', BlendExp=3.0)
    sw2 = f.get('Switch_Cards', 1792, 576)
    fade = f.call('/Script/UMG.Widget:SetRenderOpacity', 1920, 0)
    f.exec_chain(e, sete, setlr, seti, fade)
    f.link(el, 'Elapsed', add, 'A'); f.link(add, 'ReturnValue', sete, 'Elapsed')
    f.link(sete, 'Elapsed', div, 'A'); f.link(per, 'CardSeconds', div, 'B'); f.link(div, 'ReturnValue', card, 'A')
    f.link(cnt, 'CardCount', last, 'A'); f.link(card, 'ReturnValue', clamp, 'A'); f.link(last, 'ReturnValue', clamp, 'B')
    f.link(sw, 'Switch_Cards', seti, 'self'); f.link(clamp, 'ReturnValue', seti, 'Index')
    f.link(clamp, 'ReturnValue', cidx, 'InInt'); f.link(cidx, 'ReturnValue', cstart, 'A'); f.link(per, 'CardSeconds', cstart, 'B')
    f.link(sete, 'Elapsed', rem, 'A'); f.link(cstart, 'ReturnValue', rem, 'B')
    f.link(rem, 'ReturnValue', up, 'A'); f.link(up, 'ReturnValue', upn, 'A')
    f.link(per, 'CardSeconds', left0, 'A'); f.link(rem, 'ReturnValue', left0, 'B'); f.link(left0, 'ReturnValue', left, 'A')
    f.link(upn, 'ReturnValue', near, 'A'); f.link(left, 'ReturnValue', near, 'B'); f.link(near, 'ReturnValue', vis0, 'Value')
    f.link(vis0, 'ReturnValue', vis, 'Alpha')  # ease-out cubic: fast arrival, slow settle (and x^3 on the way out)
    is_h = f.call(f'{KML}:EqualEqual_IntInt', 1984, 704, B=2)
    card_op = f.call(f'{KML}:SelectFloat', 1984, 576, A=1.0)
    f.link(clamp, 'ReturnValue', is_h, 'A'); f.link(is_h, 'ReturnValue', card_op, 'bPickA'); f.link(vis, 'ReturnValue', card_op, 'B')
    f.link(card_op, 'ReturnValue', fade, 'InOpacity'); f.link(sw2, 'Switch_Cards', fade, 'self')
    cap = f.get('Txt_Hayba', 2176, 768)
    capf = f.call('/Script/UMG.Widget:SetRenderOpacity', 2176, 640)
    f.link(fade, 'then', capf, 'execute'); f.link(cap, 'Txt_Hayba', capf, 'self'); f.link(vis, 'ReturnValue', capf, 'InOpacity')
    fade_tail = capf
    if SPLAT:
        # Hayba mark: its grains assemble on the card's own fade envelope (vis), and blow away on the way out
        # page v3.1: the grains assemble over 2.4 s (longer than the 1.3 s fade up) and blow away with the fade out
        asm = f.call(f'{KML}:Divide_DoubleDouble', 1984, 1088, B=0.9)
        anear = f.call(f'{KML}:FMin', 2176, 1088)
        avis = f.call(f'{KML}:FClamp', 2368, 1088, Min=0.0, Max=1.0)
        aleft = f.call(f'{KML}:Divide_DoubleDouble', 1984, 1216, B=0.6)  # grains blow away over 0.6 s
        f.link(left0, 'ReturnValue', aleft, 'A')
        f.link(up, 'ReturnValue', asm, 'A'); f.link(asm, 'ReturnValue', anear, 'A'); f.link(aleft, 'ReturnValue', anear, 'B')
        f.link(anear, 'ReturnValue', avis, 'Value')
        hmid = f.get('HaybaMID', 2240, 960)
        sett = f.call('/Script/Engine.MaterialInstanceDynamic:SetScalarParameterValue', 2496, 960, ParameterName='Transition')
        f.link(hmid, 'HaybaMID', sett, 'self'); f.link(avis, 'ReturnValue', sett, 'Value')
        f.comment('Hayba grains', 'Grains assemble over 2.4 s and blow away as the card fades out',
                  [asm, aleft, anear, avis, hmid, sett], C_VISUAL)
    # Finish once the last card has faded to black; the front end fades the title up from black
    fin_t = f.get('FinishAt', 2016, 768)
    ge_ = f.call(f'{KML}:GreaterEqual_DoubleDouble', 2464, 768)
    done = f.get('bFinished', 2464, 896)
    notd = f.call(f'{KML}:Not_PreBool', 2656, 896)
    both = f.call(f'{KML}:BooleanAND', 2848, 768)
    br = f.branch(2560, 0)
    setd = f.set('bFinished', 2816, 0); f.default(setd, 'bFinished', 'true')
    host = f.get('Host', 2944, 160)
    finish = f.call(f'{FE_C}:OnSplashFinished', 3072, 0)
    cue = f.call(self_call(P_, 'CheckCue'), 2240, 0)
    f.link(fade_tail, 'then', cue, 'execute')
    tail = cue
    if SPLAT:
        f.link(tail, 'then', sett, 'execute'); f.link(sett, 'then', br, 'execute')
    else:
        f.link(tail, 'then', br, 'execute')
    f.link(sete, 'Elapsed', ge_, 'A'); f.link(fin_t, 'FinishAt', ge_, 'B')
    f.link(done, 'bFinished', notd, 'A'); f.link(ge_, 'ReturnValue', both, 'A'); f.link(notd, 'ReturnValue', both, 'B')
    f.link(both, 'ReturnValue', br, 'Condition')
    stop = f.call('/Script/Engine.KismetSystemLibrary:K2_ClearTimer', 3072, -160, FunctionName='UpdateSplash')
    f.link(br, 'True', setd, 'execute'); f.link(setd, 'then', stop, 'execute'); f.link(stop, 'then', finish, 'execute')
    f.link(host, 'Host', finish, 'self')
    f.comment('Advance the card', 'Card = trunc(Elapsed / CardSeconds), clamped to the last card',
              [e, now, lr, dtr, dtc, setlr, el, add, sete, per, div, card, cnt, last, clamp, sw, seti], C_LOGIC)
    f.comment('Fade through black', 'Opacity = clamp(min((t - 0.85) / 1.3, (CardSeconds - t) / 1.2))',
              [cidx, cstart, rem, up, upn, left0, left, near, vis0, vis, sw2, fade, is_h, card_op, cap, capf], C_VISUAL)
    f.comment('Hand over to the title', 'Once, after the last card is black; the title then fades up from black',
              [fin_t, ge_, done, notd, both, br, setd, stop, host, finish], C_EVENT)

    # CheckCue: tells the front end when a card starts to fade up (even cue) or out (odd cue), for its sound
    f = Graph(P_, 'CheckCue')
    e = f.at(entry_node(f), 0, 0)
    el = f.get('Elapsed', 160, 160); nct = f.get('NextCueTime', 160, 224)
    due = f.call(f'{KML}:GreaterEqual_DoubleDouble', 352, 160)
    ci = f.get('CueIndex', 160, 320); cnt = f.get('CardCount', 160, 384)
    lim = f.call(f'{KML}:Multiply_IntInt', 352, 384); f.default(lim, 'B', 2)
    left = f.call(f'{KML}:Less_IntInt', 544, 320)
    go = f.call(f'{KML}:BooleanAND', 736, 224)
    br = f.branch(864, 0)
    host = f.get('Host', 992, 160); ci2 = f.get('CueIndex', 992, 224)
    tell = f.call(f'{FE_C}:OnSplashCue', 1120, 0)
    inc = f.call(f'{KML}:Add_IntInt', 1344, 192); f.default(inc, 'B', 1)
    seti = f.set('CueIndex', 1536, 0)
    # next cue time = trunc(k / 2) x CardSeconds + (k odd ? CardSeconds - 1.0 : 0.8)
    half = f.call(f'{KML}:Divide_IntInt', 1792, 192); f.default(half, 'B', 2)
    per = f.get('CardSeconds', 1792, 288)
    base = f.call(f'{KML}:Multiply_DoubleDouble', 2048, 192)
    odd = f.call(f'{KML}:Percent_IntInt', 1792, 384); f.default(odd, 'B', 2)
    is_odd = f.call(f'{KML}:EqualEqual_IntInt', 2048, 384); f.default(is_odd, 'B', 1)
    fade_out = f.call(f'{KML}:Subtract_DoubleDouble', 2048, 480); f.default(fade_out, 'B', 0.4)
    off = f.call(f'{KML}:SelectFloat', 2304, 384, B=0.2)
    nxt = f.call(f'{KML}:Add_DoubleDouble', 2560, 192)
    sett_ = f.set('NextCueTime', 2816, 0)
    f.exec_chain(e, br); f.link(br, 'True', tell, 'execute'); f.exec_chain(tell, seti, sett_)
    f.link(el, 'Elapsed', due, 'A'); f.link(nct, 'NextCueTime', due, 'B')
    f.link(cnt, 'CardCount', lim, 'A'); f.link(ci, 'CueIndex', left, 'A'); f.link(lim, 'ReturnValue', left, 'B')
    f.link(due, 'ReturnValue', go, 'A'); f.link(left, 'ReturnValue', go, 'B'); f.link(go, 'ReturnValue', br, 'Condition')
    f.link(host, 'Host', tell, 'self'); f.link(ci2, 'CueIndex', tell, 'Index')
    f.link(ci2, 'CueIndex', inc, 'A'); f.link(inc, 'ReturnValue', seti, 'CueIndex')
    f.link(seti, 'CueIndex', half, 'A'); f.link(half, 'ReturnValue', base, 'A'); f.link(per, 'CardSeconds', base, 'B')
    f.link(seti, 'CueIndex', odd, 'A'); f.link(odd, 'ReturnValue', is_odd, 'A')
    f.link(per, 'CardSeconds', fade_out, 'A'); f.link(fade_out, 'ReturnValue', off, 'A'); f.link(is_odd, 'ReturnValue', off, 'bPickA')
    f.link(base, 'ReturnValue', nxt, 'A'); f.link(off, 'ReturnValue', nxt, 'B'); f.link(nxt, 'ReturnValue', sett_, 'NextCueTime')
    f.comment('Cue due?', 'Fires once per fade: index k is card k / 2, fading up when k is even and out when odd',
              [e, el, nct, due, ci, cnt, lim, left, go, br], C_LOGIC)
    f.comment('Report and schedule', 'Host.OnSplashCue picks the sound; next time = card start + 0.8 s '
              'or + CardSeconds - 1.0 s', [host, ci2, tell, inc, seti, half, per, base, odd, is_odd, fade_out, off, nxt,
                                          sett_], C_VISUAL)

    f = Graph(P_, 'SkipCard')
    e = f.at(entry_node(f), 0, 0)
    el = f.get('Elapsed', 160, 160); per = f.get('CardSeconds', 160, 240)
    div = f.call(f'{KML}:Divide_DoubleDouble', 320, 160)
    nxt = f.call(f'{KML}:FCeil', 544, 160)
    mul = f.call(f'{KML}:Multiply_DoubleDouble', 736, 160)
    per3 = f.get('CardSeconds', 576, 288)
    early = f.call(f'{KML}:Subtract_DoubleDouble', 960, 160, B=0.4)
    never_back = f.call(f'{KML}:FMax', 1184, 160)
    el2 = f.get('Elapsed', 960, 288)
    sete = f.set('Elapsed', 1408, 0)
    f.exec_chain(e, sete)
    f.link(el, 'Elapsed', div, 'A'); f.link(per, 'CardSeconds', div, 'B'); f.link(div, 'ReturnValue', nxt, 'A')
    f.link(nxt, 'ReturnValue', mul, 'A'); f.link(per3, 'CardSeconds', mul, 'B')
    f.link(mul, 'ReturnValue', early, 'A'); f.link(early, 'ReturnValue', never_back, 'A')
    f.link(el2, 'Elapsed', never_back, 'B'); f.link(never_back, 'ReturnValue', sete, 'Elapsed')
    f.comment('Skip the card', "Jump to the start of this card's fade to black (never backwards)",
              [e, el, per, div, nxt, mul, per3, early, el2, never_back, sete], C_LOGIC)

    g = Graph(P_).clear()
    con, find, cast, seth = construct_with_host(g)
    tail = seth
    if SPLAT:
        himg = g.get('Img_HaybaLogo', 1024, 160)
        hdyn = g.call('/Script/UMG.Image:GetDynamicMaterial', 1088, 0)
        hset = g.set('HaybaMID', 1408, 0)
        g.exec_chain(seth, hdyn, hset)
        g.link(himg, 'Img_HaybaLogo', hdyn, 'self'); g.link(hdyn, 'ReturnValue', hset, 'HaybaMID')
        tail = hset
    tmr = g.call('/Script/Engine.KismetSystemLibrary:K2_SetTimer', 1664, 0, FunctionName='UpdateSplash', Time=0.0333,
                 bLooping='true')
    g.link(tail, 'then', tmr, 'execute')
    g.comment('Run the splash', 'A 30 Hz timer drives the card clock and fades only while the splash is up (no Tick)',
              [tmr], C_EVENT)
    for name in ('OnKeyDown', 'OnMouseButtonDown'):
        override_handled(P_, name, lambda gg: (gg.call(self_call(P_, 'SkipCard'), 288, 0), gg.get('Elapsed', 224, 160)),
                         'Any key or click skips to the next card')
    compile_save(P_, defaults={'bIsFocusable': True, 'CardSeconds': 2.0, 'CardCount': 3, 'FinishAt': 6.0,
                               'Elapsed': -0.1, 'NextCueTime': 0.2})
    if unreal.find_object(None, f'{P_}.WBP_BootSplash:WidgetTree.Txt_PhotoWarning'):
        import runpy as _warning_runpy
        _warning_runpy.run_path('P:/FoA/Tools/Unreal/ui/wire_photo_warning.py', run_name='__main__')

# ------------------------------------------------------------------ Title
if 'Title' in ONLY:
    P_ = f'{M}/WBP_Title'
    host_var(P_)
    ensure_vars(P_, [('bReady', ptype('bool'), 'false', 'Title|State', False)])
    for fn_name in ('FadeInStep', 'PromptStep', 'MarkReady', 'TryConfirm'):
        Graph.function(P_, fn_name)

    def stepper(name, step, targets, title):
        """name(): add `step` to the opacity of targets[0] (and copy it to the rest) until 1, then stop its timer."""
        f = Graph(P_, name)
        e = f.at(entry_node(f), 0, 0)
        first = f.get(targets[0], 160, 224) if targets[0] != 'self' else None
        cur = f.call('/Script/UMG.Widget:GetRenderOpacity', 224, 160)
        add = f.call(f'{KML}:Add_DoubleDouble', 480, 160, B=step)
        cl = f.call(f'{KML}:FClamp', 704, 160, Min=0.0, Max=1.0)
        sets, nodes = [], [e, cur, add, cl] + ([first] if first else [])
        for i, t in enumerate(targets):
            so = f.call('/Script/UMG.Widget:SetRenderOpacity', 960 + i * 288, 0)
            if t != 'self':
                tg = f.get(t, 896 + i * 288, 160)
                f.link(tg, t, so, 'self'); nodes.append(tg)
            f.link(cl, 'ReturnValue', so, 'InOpacity'); sets.append(so)
        full = f.call(f'{KML}:GreaterEqual_DoubleDouble', 960 + len(targets) * 288, 224, B=1.0)
        br = f.branch(1024 + len(targets) * 288, 0)
        stop = f.call('/Script/Engine.KismetSystemLibrary:K2_ClearTimer', 1280 + len(targets) * 288, -96, FunctionName=name)
        f.exec_chain(e, *sets, br)
        if first:
            f.link(first, targets[0], cur, 'self')
        f.link(cur, 'ReturnValue', add, 'A'); f.link(add, 'ReturnValue', cl, 'Value')
        f.link(cl, 'ReturnValue', full, 'A'); f.link(full, 'ReturnValue', br, 'Condition'); f.link(br, 'True', stop, 'execute')
        f.comment(title, 'Steps opacity to 1 and stops its own timer (no Tick)', nodes + sets + [full, br, stop], C_VISUAL)

    stepper('FadeInStep', 0.0185, ['self'], 'Title fades up')                         # 1.8 s at 30 Hz
    stepper('PromptStep', 0.042, ['Txt_Press', 'Img_PromptHalo'], 'Prompt fades in')   # 0.8 s at 30 Hz
    f = Graph(P_, 'MarkReady'); e = f.at(entry_node(f), 0, 0)
    sr = f.set('bReady', 256, 0); f.default(sr, 'bReady', 'true'); f.exec_chain(e, sr)
    f.comment('Title settled', 'Record the natural end of the fade', [e, sr], C_LOGIC)
    f = Graph(P_, 'TryConfirm'); e = f.at(entry_node(f), 0, 0)
    host = f.get('Host', 480, 160); conf = f.call(f'{FE_C}:OnTitleConfirmed', 544, 0)
    f.exec_chain(e, conf); f.link(host, 'Host', conf, 'self')
    f.comment('Confirm the title', 'Any key opens the menu, including during the fade', [e, host, conf], C_LOGIC)

    g = Graph(P_).clear()
    con, find, cast, seth = construct_with_host(g)
    hide = g.call('/Script/UMG.Widget:SetRenderOpacity', 1024, 0, InOpacity=0.0)
    tp = g.get('Txt_Press', 1216, 160); hp = g.call('/Script/UMG.Widget:SetRenderOpacity', 1280, 0, InOpacity=0.0)
    th = g.get('Img_PromptHalo', 1472, 160); hh = g.call('/Script/UMG.Widget:SetRenderOpacity', 1536, 0, InOpacity=0.0)
    KSL_ = '/Script/Engine.KismetSystemLibrary'
    t1 = g.call(f'{KSL_}:K2_SetTimer', 1792, 0, FunctionName='FadeInStep', Time=0.033, bLooping='true', InitialStartDelay=0.9)
    t2 = g.call(f'{KSL_}:K2_SetTimer', 2112, 0, FunctionName='MarkReady', Time=2.8)
    t3 = g.call(f'{KSL_}:K2_SetTimer', 2432, 0, FunctionName='PromptStep', Time=0.033, bLooping='true', InitialStartDelay=3.2)
    g.exec_chain(seth, hide, hp, hh, t1, t2, t3)
    g.link(tp, 'Txt_Press', hp, 'self'); g.link(th, 'Img_PromptHalo', hh, 'self')
    g.comment('Title timing', 'Page v3.1: type fades in after 0.9 s over 1.8 s, prompt at 3.2 s; keys always work',
              [con, find, cast, seth, hide, tp, hp, th, hh, t1, t2, t3], C_EVENT)
    for name in ('OnKeyDown', 'OnMouseButtonDown'):
        override_handled(P_, name, lambda gg: (gg.call(self_call(P_, 'TryConfirm'), 288, 0), gg.get('bReady', 224, 160)),
                         'Any key or click, including during the title fade')
    compile_save(P_, defaults={'bIsFocusable': True})

# ------------------------------------------------------------------ Main menu
if 'MainMenu' in ONLY:
    P_ = f'{M}/WBP_MainMenu'
    host_var(P_)
    g = Graph(P_).clear()
    con, find, cast, seth = construct_with_host(g)
    prev, nodes = seth, [con, find, cast, seth]
    rows = (('Btn_WakeUp', 'WakeUp'), ('Btn_Settings', 'OpenSettings'), ('Btn_Credits', 'OpenCredits'),
            ('Btn_Quit', 'RequestQuit'))
    handlers = []
    for i, (btn, intent) in enumerate(rows):
        x = 1024 + i * 384
        src = g.get(btn, x - 64, 192)
        bind, ev = bind_event(g, src, btn, 'OnSandClicked', f'On{btn[4:]}Clicked', x, 0)
        g.link(prev, 'then', bind, 'execute')
        prev = bind
        nodes += [src, bind]
        handlers.append((ev, intent))
    # The front end's FocusUI(Screen) runs right after Construct and takes focus off the button, so the default
    # selection (Wake up, shown as hovered: its sand stir and grains) lands one tick later through a timer
    arm = g.call('/Script/Engine.KismetSystemLibrary:K2_SetTimer', 2624, 0, FunctionName='FocusDefault', Time=0.05)
    g.link(prev, 'then', arm, 'execute')
    g.comment('Bind buttons, focus', 'Each button raises one intent on BP_FoAFrontEnd', nodes + [arm], C_EVENT)
    # The words, footer and hints fade in over 0.6 s as the title gives way to the menu (the page's screen transition);
    # the logotype is on both screens and stays put
    ensure_vars(P_, [('MenuFade', ptype('real'), '0.0', 'Menu|State', False)])
    FADE = ('VB_Buttons', 'HB_Hints', 'Txt_Build')
    zero_y, prev0, zn = -640, arm, []
    for i, w_ in enumerate(FADE):
        wg = g.get(w_, 2944 + i * 320, zero_y + 160)
        z = g.call('/Script/UMG.Widget:SetRenderOpacity', 3008 + i * 320, zero_y, InOpacity=0.0)
        g.link(prev0, 'then', z, 'execute'); g.link(wg, w_, z, 'self'); prev0 = z; zn += [wg, z]
    mt = g.call('/Script/Engine.KismetSystemLibrary:K2_SetTimer', 3968, zero_y, FunctionName='MenuFadeStep', Time=0.033,
                bLooping='true')
    g.link(prev0, 'then', mt, 'execute')
    g.comment('Menu fades in', 'Words, footer and hints from 0, then a 30 Hz step', zn + [mt], C_VISUAL)
    st = g.custom_event('MenuFadeStep', 2560, -960)
    mf = g.get('MenuFade', 2560, -800)
    inc = g.call('/Script/Engine.KismetMathLibrary:Add_DoubleDouble', 2752, -800, B=0.055)
    clp = g.call('/Script/Engine.KismetMathLibrary:FClamp', 2944, -800, Min=0.0, Max=1.0)
    smf = g.set('MenuFade', 3136, -960)
    g.link(st, 'then', smf, 'execute'); g.link(mf, 'MenuFade', inc, 'A'); g.link(inc, 'ReturnValue', clp, 'Value')
    g.link(clp, 'ReturnValue', smf, 'MenuFade')
    prev1, sn = smf, [st, mf, inc, clp, smf]
    for i, w_ in enumerate(FADE):
        wg = g.get(w_, 3392 + i * 320, -800)
        o = g.call('/Script/UMG.Widget:SetRenderOpacity', 3456 + i * 320, -960)
        g.link(prev1, 'then', o, 'execute'); g.link(wg, w_, o, 'self'); g.link(smf, 'MenuFade', o, 'InOpacity'); prev1 = o
        sn += [wg, o]
    done = g.call('/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble', 4416, -800, B=1.0)
    br_ = g.branch(4480, -960)
    stop = g.call('/Script/Engine.KismetSystemLibrary:K2_ClearTimer', 4736, -960, FunctionName='MenuFadeStep')
    g.link(prev1, 'then', br_, 'execute'); g.link(smf, 'MenuFade', done, 'A'); g.link(done, 'ReturnValue', br_, 'Condition')
    g.link(br_, 'True', stop, 'execute')
    g.comment('Menu fade step', 'Opacity rises 0.055 per step and the timer stops itself at 1', sn + [done, br_, stop], C_VISUAL)
    fd = g.custom_event('FocusDefault', 2560, -320)
    wake = g.get('Btn_WakeUp', 2816, -160)
    focus = g.call('/Game/FoA/UI/Widgets/Common/WBP_SandButton.WBP_SandButton_C:FocusButton', 2880, -320)
    g.link(fd, 'then', focus, 'execute'); g.link(wake, 'Btn_WakeUp', focus, 'self')
    g.comment('Default selection', 'Wake up takes focus after the screen does', [fd, wake, focus], C_EVENT)
    hn = []
    for i, (ev, intent) in enumerate(handlers):
        y = 512 + i * 160
        g.at(ev, 0, y)
        host = g.get('Host', 320, y + 96)
        call = g.call(f'{FE_C}:{intent}', 384, y)
        g.link(ev, 'then', call, 'execute'); g.link(host, 'Host', call, 'self')
        hn += [ev, host, call]
    g.comment('Menu intents', 'Wake Up, Settings, Credits, Quit (asks to confirm)', hn, C_LOGIC)
    # Esc goes Back here instead of falling through to the editor's PIE Stop; every other key stays Unhandled so the
    # buttons and Up/Down navigation still get it
    k = override_graph(P_, 'OnKeyDown')
    if k is not None:
        e = k.at(entry_node(k), 0, 0)
        ret_u = k.at(k.ed.list_nodes_of_class(unreal.K2Node_FunctionResult)[0], 896, 160)
        key = k.call('/Script/Engine.KismetInputLibrary:GetKey', 160, 160)
        esc = k.call('/Script/Engine.KismetInputLibrary:EqualEqual_KeyKey', 352, 160)  # '==': typed by its first link
        pad = k.call('/Script/Engine.KismetInputLibrary:EqualEqual_KeyKey', 352, 384)
        either = k.call('/Script/Engine.KismetMathLibrary:BooleanOR', 576, 320)
        br = k.branch(576, 0)
        host = k.get('Host', 768, -96)
        back = k.call(f'{FE_C}:HandleBack', 832, -224)
        ret_h = k.at(k.ed.add_return_node(), 1152, -224)
        handled = k.call(f'{UWBL}:Handled', 960, -96)
        k.link(e, 'InKeyEvent', key, 'Input'); k.link(key, 'ReturnValue', esc, 'A')
        k.link(key, 'ReturnValue', pad, 'A')
        k.link(esc, 'ReturnValue', either, 'A'); k.link(pad, 'ReturnValue', either, 'B')
        k.link(either, 'ReturnValue', br, 'Condition')
        assert PIN.set_pin_value(k.pin(esc, 'B', 'in'), 'Escape')
        assert PIN.set_pin_value(k.pin(pad, 'B', 'in'), 'Gamepad_FaceButton_Right')
        k.link(e, 'then', br, 'execute'); k.link(br, 'True', back, 'execute'); k.link(host, 'Host', back, 'self')
        k.link(back, 'then', ret_h, 'execute'); k.link(handled, 'ReturnValue', ret_h, 'ReturnValue')
        unh = k.call(f'{UWBL}:Unhandled', 640, 288)
        k.link(br, 'False', ret_u, 'execute'); k.link(unh, 'ReturnValue', ret_u, 'ReturnValue')
        k.comment('Back keys', 'Escape and controller B call HandleBack and are consumed; other keys pass through',
                  [e, key, esc, pad, either, br, host, back, ret_h, handled, unh, ret_u], C_EVENT)
    compile_save(P_)

# ------------------------------------------------------------------ Input hint
if 'InputHint' in ONLY:
    P_ = '/Game/FoA/UI/Widgets/Common/WBP_InputHint'
    ensure_vars(P_, [('KeyLabel', ptype('text'), 'Enter', 'Input Hint', True, True),
                     ('ActionLabel', ptype('text'), 'Select', 'Input Hint', True, True)])
    g = Graph(P_).clear()
    pre = g.event('PreConstruct', 0, 0)
    k_t = g.get('Txt_Key', 224, 160); k_v = g.get('KeyLabel', 224, 240)
    set_k = g.call('/Script/UMG.TextBlock:SetText', 288, 0)
    a_t = g.get('Txt_Action', 576, 160); a_v = g.get('ActionLabel', 576, 240)
    set_a = g.call('/Script/UMG.TextBlock:SetText', 640, 0)
    g.exec_chain(pre, set_k, set_a)
    g.link(k_t, 'Txt_Key', set_k, 'self'); g.link(k_v, 'KeyLabel', set_k, 'InText')
    g.link(a_t, 'Txt_Action', set_a, 'self'); g.link(a_v, 'ActionLabel', set_a, 'InText')
    g.comment('Apply labels', 'Key cap and action text, at design time too', [pre, k_t, k_v, set_k, a_t, a_v, set_a],
              C_VISUAL)
    compile_save(P_)
