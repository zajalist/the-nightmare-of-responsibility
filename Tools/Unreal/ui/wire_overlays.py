"""Graphs for the overlay screens: WBP_Pause, WBP_ConfirmDialog, WBP_Credits (run via ue_remote.py;
FOA_WIDGETS=Pause,Confirm,Credits to subset). Same pattern as wire_menus.py: Host found once in Construct, each
button raises one intent, Esc / gamepad B is the Back key."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
import os
import unreal

FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
FE_C = FE + '.BP_FoAFrontEnd_C'
SB_C = '/Game/FoA/UI/Widgets/Common/WBP_SandButton.WBP_SandButton_C'
KML = '/Script/Engine.KismetMathLibrary'
KIL = '/Script/SlateCore.KismetInputLibrary' if unreal.load_class(None, '/Script/SlateCore.KismetInputLibrary') else \
    '/Script/Engine.KismetInputLibrary'
UWBL = '/Script/UMG.WidgetBlueprintLibrary'
HOST_T = ptype(unreal.load_class(None, FE_C))
ONLY = [s for s in os.environ.get('FOA_WIDGETS', 'Pause,Confirm,Credits').split(',') if s]


def construct_and_bind(path, rows, focus_btn, title):
    """Construct: find Host, bind each (button, intent), focus the default button. Handlers stack below."""
    ensure_vars(path, [('Host', HOST_T, '', 'Screen', False)])
    g = Graph(path).clear()
    con = g.event('Construct', 0, 0)
    find, cast, seth = host_lookup(g, FE_C, 256, 0)
    g.link(con, 'then', find, 'execute')
    prev, nodes, handlers = seth, [con, find, cast, seth], []
    for i, (btn, intent) in enumerate(rows):
        x = 1024 + i * 384
        src = g.get(btn, x - 64, 192)
        bind, ev = bind_event(g, src, btn, 'OnSandClicked', f'On{btn[4:]}Clicked', x, 0)
        g.link(prev, 'then', bind, 'execute')
        prev = bind
        nodes += [src, bind]
        handlers.append((ev, intent))
    x = 1024 + len(rows) * 384
    # The default button takes focus 0.05 s after Construct: OpenOverlay's FocusUI(overlay root) runs after Construct
    # and took focus off a button focused here, so the keyboard landed on the viewport (intro_bugs B13)
    arm = g.call('/Script/Engine.KismetSystemLibrary:K2_SetTimer', x, 0, FunctionName='FocusDefault', Time=0.05)
    g.link(prev, 'then', arm, 'execute')
    g.comment(title, 'Find host, bind buttons, then focus the default button a beat later', nodes + [arm], C_EVENT)
    fd = g.custom_event('FocusDefault', x, -480)
    fb = g.get(focus_btn, x + 64, -320)
    focus = g.call(f'{SB_C}:FocusButton', x + 320, -480)
    g.link(fd, 'then', focus, 'execute'); g.link(fb, focus_btn, focus, 'self')
    g.comment('Default selection', 'The safe or first button', [fd, fb, focus], C_EVENT)
    g._focus_node = arm
    hn = []
    for i, (ev, intent) in enumerate(handlers):
        y = 512 + i * 160
        g.at(ev, 0, y)
        host = g.get('Host', 320, y + 96)
        call = g.call(f'{FE_C}:{intent}', 384, y)
        g.link(ev, 'then', call, 'execute'); g.link(host, 'Host', call, 'self')
        hn += [ev, host, call]
    g.comment('Button intents', ', '.join(i for _, i in rows), hn, C_LOGIC)
    return g, seth


def back_override(path, intent):
    """OnKeyDown: Esc or gamepad B runs `intent` on Host and is handled; anything else passes through.
    Skips widgets that already have the override: re-overriding crashed the editor (18:53, BlueprintEditorLibrary)."""
    g = override_graph(path, 'OnKeyDown')
    if g is None:
        return
    e = g.at(entry_node(g), 0, 0)
    ret = g.ed.list_nodes_of_class(unreal.K2Node_FunctionResult)[0]
    for n in list(g.ed.list_all_nodes()):
        if n not in (e, ret):
            g.ed.remove_nodes([n])
    key = g.call(f'{KIL}:GetKey', 224, 192)
    esc = g.call('/Script/Engine.KismetInputLibrary:EqualEqual_KeyKey', 480, 160)
    pad = g.call('/Script/Engine.KismetInputLibrary:EqualEqual_KeyKey', 480, 288)
    either = g.call(f'{KML}:BooleanOR', 736, 192)
    br = g.branch(896, 0)
    host = g.get('Host', 1088, -96)
    call = g.call(f'{FE_C}:{intent}', 1152, -160)
    yes = g.call(f'{UWBL}:Handled', 1472, -32)
    no = g.call(f'{UWBL}:Unhandled', 1472, 224)
    ret2 = g.at(g.ed.add_return_node(), 1728, 160)
    g.at(ret, 1728, -160)
    g.link(e, 'InKeyEvent', key, 'Input'); g.link(key, 'ReturnValue', esc, 'A'); g.link(key, 'ReturnValue', pad, 'A')
    assert PIN.set_pin_value(g.pin(esc,'B','in'), 'Escape')
    assert PIN.set_pin_value(g.pin(pad,'B','in'), 'Gamepad_FaceButton_Right')
    g.link(esc, 'ReturnValue', either, 'A'); g.link(pad, 'ReturnValue', either, 'B')
    g.exec_chain(e, br); g.link(either, 'ReturnValue', br, 'Condition')
    g.link(br, 'True', call, 'execute'); g.link(host, 'Host', call, 'self'); g.link(call, 'then', ret, 'execute')
    g.link(yes, 'ReturnValue', ret, 'ReturnValue')
    g.link(br, 'False', ret2, 'execute'); g.link(no, 'ReturnValue', ret2, 'ReturnValue')
    g.comment('Back key', f'Esc or gamepad B: {intent}; other keys pass through to focus navigation',
              [e, key, esc, pad, either, br, host, call, yes, no, ret, ret2], C_EVENT)


if 'Pause' in ONLY:
    P_ = '/Game/FoA/UI/Widgets/Menus/WBP_Pause'
    construct_and_bind(P_, (('Btn_Resume', 'Resume'), ('Btn_Settings', 'OpenSettings'),
                            ('Btn_RestartDay', 'RequestRestartDay'), ('Btn_QuitToTitle', 'RequestQuitToTitle')),
                       'Btn_Resume', 'Pause menu')
    back_override(P_, 'Resume')
    compile_save(P_, defaults={'bIsFocusable': True})

if 'Confirm' in ONLY:
    P_ = '/Game/FoA/UI/Widgets/Common/WBP_ConfirmDialog'
    g, seth = construct_and_bind(P_, (('Btn_Confirm', 'ConfirmPending'), ('Btn_Cancel', 'CloseOverlay')),
                                 'Btn_Cancel', 'Confirm dialog')
    # Copy comes from Host (set by AskConfirm): title, body, confirm label. Row y = -320, above the bind row.
    nodes, prev = [], None
    for i, (var, widget, fn_path) in enumerate((('ConfirmTitle', 'Txt_Title', '/Script/UMG.TextBlock:SetText'),
                                                ('ConfirmBody', 'Txt_Body', '/Script/UMG.TextBlock:SetText'),
                                                ('ConfirmLabel', 'Btn_Confirm', f'{SB_C}:SetLabel'))):
        x = 256 + i * 384
        host = g.get('Host', x - 64, -160)
        val = g.get(var, x, -96, class_path=FE_C)
        tgt = g.get(widget, x - 64, -224)
        st = g.call(fn_path, x + 64, -320)
        g.link(host, 'Host', val, 'self'); g.link(tgt, widget, st, 'self')
        g.link(val, var, st, 'InText' if 'TextBlock' in fn_path else 'NewLabel')
        if prev:
            g.link(prev, 'then', st, 'execute')
        prev = st
        nodes += [host, val, tgt, st]
    g.comment('Copy from Host', 'Title, body and confirm label chosen by the request (plain sentences)', nodes, C_VISUAL)
    g.link(g._focus_node, 'then', nodes[3], 'execute')
    back_override(P_, 'CloseOverlay')
    compile_save(P_)

if 'Credits' in ONLY:
    P_ = '/Game/FoA/UI/Widgets/Menus/WBP_Credits'
    construct_and_bind(P_, (('Btn_Back', 'CloseOverlay'),), 'Btn_Back', 'Credits screen')
    back_override(P_, 'CloseOverlay')
    compile_save(P_)
