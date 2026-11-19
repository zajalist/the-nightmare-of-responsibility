"""WBP_IntroStory shell, part 2: variables and graph (run after intro_widget_calls.py; lease the widget's folder).
  $env:FOA_AREAS='/Game/FoA/UI/Intro'; python Tools/Unreal/ui/hayba_replay.py Tools/LookDev/intro_widget_graph.py
Contract (integration P16, BP_FoAFrontEnd): created by AfterWakeFade on the first start ever and added over black.
  Construct: find the front end (Host), bind the full-screen skip button, show panel 0.
  NextPanel: next texture and subtitle, Host.PlayUISound(Host.SndPanelTransition), timer for this panel's seconds;
             after the last panel, Finish.
  Finish:    once only, Host.OnStoryFinished() (the front end removes the widget and wakes the player).
Panels, Lines and Seconds are class defaults (Hayba blueprint_set_defaults), so the final art swaps in without a rebuild."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())  # noqa: S102  (the UI lane's graph helpers)

W = '/Game/FoA/UI/Intro/WBP_IntroStory'
HOST = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
TEX = '/Game/FoA/UI/Intro/Textures'
KML, KAL, KSL = '/Script/Engine.KismetMathLibrary', '/Script/Engine.KismetArrayLibrary', '/Script/Engine.KismetSystemLibrary'
LINES = ["There is a man who keeps sleeping through his life.",
         "Something stands at the foot of the bed. It is patient.",
         "Seventeen days. He crossed out every one.",
         "The letters wait. The cup waits. The good shirt waits on the chair.",
         "Here, the chores have grown teeth. They are completely serious.",
         "Today, you will get dressed.",
         "Today, you will leave the house.",
         ""]
SECONDS = [7.0, 7.0, 7.0, 7.0, 8.0, 6.0, 6.0, 4.0]


def build():
    host_cls = unreal.load_class(None, HOST)
    assert host_cls, HOST
    ensure_vars(W, [
        ('Host', ptype(host_cls), '', 'Intro', False),
        ('Index', ptype('int'), '-1', 'Intro', False),
        ('bDone', ptype('bool'), 'false', 'Intro', False),
        ('Panels', BEL.get_array_type(ptype(unreal.Texture2D)), '', 'Intro', True),
        ('Lines', BEL.get_array_type(ptype('string')), '', 'Intro', True),
        ('Seconds', BEL.get_array_type(ptype('real')), '', 'Intro', True),
    ])
    Graph.function(W, 'Finish')
    Graph.function(W, 'NextPanel')

    def arr(g, var, idx_node, idx_pin, x, y):
        """Get (a copy) of var[idx]."""
        getter = g.get(var, x, y)
        pin = g.pin(getter, var, 'out')
        names = [n for n in g.ed.list_available_nodes([pin]) if n.endswith('Get (a copy)')]
        assert names, 'no array Get node'
        n = g.at(g.ed.create_node_from_name(names[0], V2(x + 224, y), [pin]), x + 224, y)
        if not PIN.list_connected_pins(g.pin(n, 'TargetArray', 'in')):
            g.link(getter, var, n, 'TargetArray')
        g.link(idx_node, idx_pin, n, 'Index')
        return n

    # Finish: once only, hand back to the front end
    g = Graph(W, 'Finish')
    e = g.at(entry_node(g), 0, 0)
    done = g.get('bDone', 160, 160)
    br = g.branch(320, 0)
    mark = g.set('bDone', 576, 0)
    g.default(mark, 'bDone', 'true')
    host = g.get('Host', 576, 160)
    fin = g.call(f'{HOST}:OnStoryFinished', 832, 0)
    g.exec_chain(e, br)
    g.link(done, 'bDone', br, 'Condition')
    g.link(br, 'False', mark, 'execute')
    g.exec_chain(mark, fin)
    g.link(host, 'Host', fin, 'self')
    g.comment('Hand back once', '', [e, done, br, mark, host, fin], C_EVENT)

    # NextPanel: advance, show, sound, schedule the next one
    g = Graph(W, 'NextPanel')
    e = g.at(entry_node(g), 0, 0)
    idx = g.get('Index', 160, 192)
    add = g.call(f'{KML}:Add_IntInt', 352, 192, B=1)
    seti = g.set('Index', 576, 0)
    g.link(idx, 'Index', add, 'A')
    g.link(add, 'ReturnValue', seti, 'Index')
    idx2 = g.get('Index', 768, 192)
    pget = g.get('Panels', 768, 288)
    lens = [n for n in g.ed.list_available_nodes([g.pin(pget, 'Panels', 'out')]) if n.endswith('|Length')]
    ln = g.at(g.ed.create_node_from_name(lens[0], V2(960, 288), [g.pin(pget, 'Panels', 'out')]), 960, 288)
    if not PIN.list_connected_pins(g.pin(ln, 'TargetArray', 'in')):
        g.link(pget, 'Panels', ln, 'TargetArray')
    less = g.call(f'{KML}:Less_IntInt', 1184, 192)
    g.link(idx2, 'Index', less, 'A')
    g.link(ln, 'ReturnValue', less, 'B')
    br = g.branch(1408, 0)
    g.link(less, 'ReturnValue', br, 'Condition')
    g.exec_chain(e, seti, br)
    # show: texture and subtitle
    img = g.get('Img_Panel', 1600, -320)
    tex = arr(g, 'Panels', idx2, 'Index', 1600, -224)
    brush = g.call('/Script/UMG.Image:SetBrushFromTexture', 1984, -320)
    g.link(img, 'Img_Panel', brush, 'self')
    g.link(tex, 'Output', brush, 'Texture')
    sub = g.get('Txt_Sub', 2240, -320)
    line = arr(g, 'Lines', idx2, 'Index', 2240, -224)
    totext = g.call(f'{KML.replace("KismetMathLibrary", "KismetTextLibrary")}:Conv_StringToText', 2688, -224)
    g.link(line, 'Output', totext, 'InString')
    settext = g.call('/Script/UMG.TextBlock:SetText', 2944, -320)
    g.link(sub, 'Txt_Sub', settext, 'self')
    g.link(totext, 'ReturnValue', settext, 'InText')
    # the transition sound, through the front end's one UI sound path
    host = g.get('Host', 3200, -128)
    snd = g.get('SndPanelTransition', 3200, -32, class_path=HOST)
    g.link(host, 'Host', snd, 'self')
    play = g.call(f'{HOST}:PlayUISound', 3456, -320)
    g.link(host, 'Host', play, 'self')
    g.link(snd, 'SndPanelTransition', play, 'Cue')
    # schedule the next panel after this panel's seconds
    secs = arr(g, 'Seconds', idx2, 'Index', 3712, -128)
    timer = g.call(f'{KSL}:K2_SetTimer', 4096, -320, FunctionName='NextPanel', bLooping='false')
    g.link(secs, 'Output', timer, 'Time')
    g.link(br, 'True', brush, 'execute')
    g.exec_chain(brush, settext, play, timer)
    fin = g.call(self_call(W, 'Finish'), 1664, 192)
    g.link(br, 'False', fin, 'execute')
    g.comment('Advance the index', '', [e, idx, add, seti, idx2, pget, ln, less, br], C_LOGIC)
    g.comment('Show the panel', '', [img, tex, brush, sub, line, totext, settext], C_VISUAL)
    g.comment('Panel sound', '', [host, snd, play], C_VISUAL)
    g.comment('Schedule the next', '', [secs, timer, fin], C_LOGIC)

    # Construct: host, skip, first panel
    g = Graph(W)
    for n in [n for n in g.ed.list_all_nodes() if 'Construct' in n.get_name() or 'SkipClicked' in n.get_name()]:
        g.ed.remove_nodes([n])
    ev = g.event('Construct', 0, 0)
    find, cast, seth = host_lookup(g, HOST, 256, 0)
    g.link(ev, 'then', find, 'execute')
    btn = g.get('Btn_Skip', 1248, 192)
    bind, skip = bind_event(g, btn, 'Btn_Skip', 'OnClicked', 'SkipClicked', 1472, 0)
    first = g.call(self_call(W, 'NextPanel'), 1856, 0)
    g.exec_chain(seth, bind, first)
    fin = g.call(self_call(W, 'Finish'), 1856, 192)
    g.link(skip, 'then', fin, 'execute')
    g.comment('Start the story', '', [ev, find, cast, seth, btn, bind, first], C_EVENT)
    g.comment('Skip any time', '', [skip, fin], C_EVENT)

    q = lambda s: '"' + s.replace('"', '\\"') + '"'  # noqa: E731
    compile_save(W, defaults={
        'Panels': '(' + ','.join(f'"{TEX}/T_Intro_P{i}.T_Intro_P{i}"' for i in range(1, 9)) + ')',
        'Lines': '(' + ','.join(q(s) for s in LINES) + ')',
        'Seconds': '(' + ','.join(str(s) for s in SECONDS) + ')',
    })


build()
