"""Graphs for the two reusable settings rows (run via ue_remote.py; FOA_WIDGETS=Slider,Switcher to subset).
WBP_SettingRow_Slider   : Label, Min/Max/Step, Value, DisplayScale/Decimals -> OnRowValueChanged(Value)
WBP_SettingRow_Switcher : Label, Options, Index -> OnRowIndexChanged(Index); Left/Right (any device) and the chevrons step
Both light Img_Focus while anything inside them has keyboard/gamepad focus."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
import os
import unreal

C = '/Game/FoA/UI/Widgets/Common'
KML = '/Script/Engine.KismetMathLibrary'
KTL = '/Script/Engine.KismetTextLibrary'
UWBL = '/Script/UMG.WidgetBlueprintLibrary'
ONLY = [s for s in os.environ.get('FOA_WIDGETS', 'Slider,Switcher').split(',') if s]
T_REAL, T_INT, T_TEXT = ptype('real'), ptype('int'), ptype('text')


def focus_rows(g, y):
    """OnAdded/RemovedFromFocusPath -> Img_Focus visible / hidden."""
    nodes = []
    for i, (ev_name, vis) in enumerate((('OnAddedToFocusPath', 'HitTestInvisible'), ('OnRemovedFromFocusPath', 'Hidden'))):
        row = y + i * 160
        ev = g.event(ev_name, 0, row)
        img = g.get('Img_Focus', 288, row + 96)
        setv = g.call('/Script/UMG.Widget:SetVisibility', 352, row, InVisibility=vis)
        g.link(ev, 'then', setv, 'execute'); g.link(img, 'Img_Focus', setv, 'self')
        nodes += [ev, img, setv]
    g.comment('Focus highlight', 'The row lights while it (or its slider) holds keyboard/gamepad focus', nodes, C_VISUAL)


def dispatcher(path, name, param, ptype_):
    bp = unreal.load_asset(path)
    if name not in [str(n) for n in BEL.list_event_dispatchers(bp)]:
        BEL.add_event_dispatcher(bp, name)
        BEL.add_event_dispatcher_parameter(bp, name, param, ptype_)


def call_dispatcher(g, name, x, y):
    names = [n for n in g.ed.list_available_nodes([]) if n.replace(' ', '').endswith('Call' + name)]
    return g.at(g.ed.create_node_from_name(names[0], V2(x, y), []), x, y)


# ------------------------------------------------------------------ Slider row
if 'Slider' in ONLY:
    P_ = f'{C}/WBP_SettingRow_Slider'
    ensure_vars(P_, [('Label', T_TEXT, 'Setting', 'Row', True, True), ('MinValue', T_REAL, '0.0', 'Row', True),
                     ('MaxValue', T_REAL, '1.0', 'Row', True), ('StepSize', T_REAL, '0.05', 'Row', True),
                     ('Value', T_REAL, '1.0', 'Row', True), ('DisplayScale', T_REAL, '100.0', 'Row', True),
                     ('DisplayDecimals', T_INT, '0', 'Row', True)])
    dispatcher(P_, 'OnRowValueChanged', 'Value', T_REAL)
    # Native Slider callbacks use float. Our public stored values/dispatcher use double; binding a double
    # callback to OnValueChanged fails signature validation, so derive its input from the actual native pin.
    probe = Graph(P_)
    value_node = probe.call('/Script/UMG.Slider:GetValue', 0, -512)
    native_value_type = PIN.get_pin_type(probe.pin(value_node, 'ReturnValue', 'out'))
    probe.ed.remove_nodes([value_node])
    for f in ('ApplyRow', 'UpdateValueText', 'SetRowValue', 'HandleSliderChanged'):
        drop_function(P_, f)
    Graph.function(P_, 'ApplyRow'); Graph.function(P_, 'UpdateValueText')
    Graph.function(P_, 'SetRowValue', inputs=[('NewValue', T_REAL)])
    changed = Graph.function(P_, 'HandleSliderChanged', inputs=[('NewValue', native_value_type)])
    changed_entry = entry_node(changed)
    native_argument = next(p for p in BEL.list_output_pins(changed_entry) if str(PIN.get_pin_name(p)) != 'then')
    if PIN.get_pin_type(native_argument).export_text() != native_value_type.export_text():
        assert changed.ed.remove_graph_input_parameter(str(PIN.get_pin_name(native_argument)))
        native_argument = changed.ed.add_graph_input_parameter('SliderValue', native_value_type)
    native_argument_name = str(PIN.get_pin_name(native_argument))

    f = Graph(P_, 'UpdateValueText')
    e = f.at(entry_node(f), 0, 0)
    v = f.get('Value', 160, 160); sc = f.get('DisplayScale', 160, 240)
    mul = f.call(f'{KML}:Multiply_DoubleDouble', 352, 160)
    dec = f.get('DisplayDecimals', 352, 288)
    txt = f.call(f'{KTL}:Conv_DoubleToText', 576, 160, bAlwaysSign='false', bUseGrouping='false')
    tv = f.get('Txt_Value', 832, 96)
    st = f.call('/Script/UMG.TextBlock:SetText', 896, 0)
    f.exec_chain(e, st)
    f.link(v, 'Value', mul, 'A'); f.link(sc, 'DisplayScale', mul, 'B'); f.link(mul, 'ReturnValue', txt, 'Value')
    f.link(dec, 'DisplayDecimals', txt, 'MinimumFractionalDigits'); f.link(dec, 'DisplayDecimals', txt, 'MaximumFractionalDigits')
    f.link(tv, 'Txt_Value', st, 'self'); f.link(txt, 'ReturnValue', st, 'InText')
    f.comment('Value readout', 'Value x DisplayScale with fixed decimals (volume 0-1 reads 0-100)',
              [e, v, sc, mul, dec, txt, tv, st], C_VISUAL)

    f = Graph(P_, 'ApplyRow')
    e = f.at(entry_node(f), 0, 0)
    lt = f.get('Txt_Label', 224, 160); lv = f.get('Label', 224, 240)
    stl = f.call('/Script/UMG.TextBlock:SetText', 288, 0)
    f.exec_chain(e, stl)
    f.link(lt, 'Txt_Label', stl, 'self'); f.link(lv, 'Label', stl, 'InText')
    nodes, prev, x = [e, lt, lv, stl], stl, 576
    for setter, var, pin in (('SetMinValue', 'MinValue', 'InValue'), ('SetMaxValue', 'MaxValue', 'InValue'),
                             ('SetStepSize', 'StepSize', 'InValue'), ('SetValue', 'Value', 'InValue')):
        sld = f.get('Sld_Value', x - 64, 160); val = f.get(var, x - 64, 240)
        call = f.call(f'/Script/UMG.Slider:{setter}', x, 0)
        f.link(prev, 'then', call, 'execute'); f.link(sld, 'Sld_Value', call, 'self'); f.link(val, var, call, pin)
        prev, x = call, x + 320
        nodes += [sld, val, call]
    upd = f.call(self_call(P_, 'UpdateValueText'), x, 0)
    f.link(prev, 'then', upd, 'execute')
    f.comment('Apply row', 'Label, range, step and value onto the Slider, then the readout', nodes + [upd], C_VISUAL)

    f = Graph(P_, 'SetRowValue')
    e = f.at(entry_node(f), 0, 0)
    lower = f.get('MinValue', 16, 192); upper = f.get('MaxValue', 16, 288)
    clamp = f.call(f'{KML}:FClamp', 256, 192)
    setv = f.set('Value', 256, 0)
    sld = f.get('Sld_Value', 448, 160)
    sv = f.call('/Script/UMG.Slider:SetValue', 512, 0)
    upd = f.call(self_call(P_, 'UpdateValueText'), 832, 0)
    f.exec_chain(e, setv, sv, upd); f.link(e, 'NewValue', clamp, 'Value')
    f.link(lower, 'MinValue', clamp, 'Min'); f.link(upper, 'MaxValue', clamp, 'Max')
    f.link(clamp, 'ReturnValue', setv, 'Value')
    f.link(sld, 'Sld_Value', sv, 'self'); f.link(setv, 'Value', sv, 'InValue')
    f.comment('Set row value', 'Used when the settings screen loads current values (no broadcast)',
              [e, lower, upper, clamp, setv, sld, sv, upd], C_LOGIC)

    f = Graph(P_, 'HandleSliderChanged')
    e = f.at(entry_node(f), 0, 0)
    setv = f.set('Value', 256, 0)
    upd = f.call(self_call(P_, 'UpdateValueText'), 512, 0)
    bc = call_dispatcher(f, 'OnRowValueChanged', 832, 0)
    f.exec_chain(e, setv, upd, bc); f.link(e, native_argument_name, setv, 'Value'); f.link(setv, 'Value', bc, 'Value')
    f.comment('User moved the slider', 'Store, refresh the readout, broadcast to the settings screen',
              [e, setv, upd, bc], C_LOGIC)

    g = Graph(P_).clear()
    pre = g.event('PreConstruct', 0, 0)
    ap = g.call(self_call(P_, 'ApplyRow'), 288, 0)
    g.link(pre, 'then', ap, 'execute')
    g.comment('Design time + runtime', 'Label, range and value', [pre, ap], C_EVENT)
    con = g.event('Construct', 0, 192)
    sld = g.get('Sld_Value', 224, 352)
    bind, mk = bind_function(g, sld, 'Sld_Value', 'OnValueChanged', 'HandleSliderChanged', 352, 192)
    g.link(con, 'then', bind, 'execute')
    g.comment('Listen to the slider', 'OnValueChanged -> HandleSliderChanged', [con, sld, bind, mk], C_EVENT)
    focus_rows(g, 576)
    compile_save(P_)

# ------------------------------------------------------------------ Switcher row
if 'Switcher' in ONLY:
    P_ = f'{C}/WBP_SettingRow_Switcher'
    T_TEXT_ARR = BEL.get_array_type(T_TEXT)
    ensure_vars(P_, [('Label', T_TEXT, 'Setting', 'Row', True, True), ('Options', T_TEXT_ARR, '', 'Row', True),
                     ('Index', T_INT, '0', 'Row', True)])
    dispatcher(P_, 'OnRowIndexChanged', 'Index', T_INT)
    for fname in ('ApplyRow', 'UpdateValueText', 'Step', 'SetRowIndex', 'SetOptions'):
        drop_function(P_, fname)
    Graph.function(P_, 'ApplyRow'); Graph.function(P_, 'UpdateValueText')
    Graph.function(P_, 'Step', inputs=[('Delta', T_INT)])
    Graph.function(P_, 'SetRowIndex', inputs=[('NewIndex', T_INT)])
    Graph.function(P_, 'SetOptions', inputs=[('NewOptions', T_TEXT_ARR), ('NewIndex', T_INT)])

    f = Graph(P_, 'UpdateValueText')
    e = f.at(entry_node(f), 0, 0)
    opts = f.get('Options', 160, 160); idx = f.get('Index', 160, 240)
    get = f.node('Utilities|Array|Get(acopy)', 352, 160) if any(
        n == 'Utilities|Array|Get(acopy)' for n in f.ed.list_available_nodes([])) else None
    if get is None:
        names = [n for n in f.ed.list_available_nodes([f.pin(opts, 'Options')]) if n.replace(' ', '').lower().endswith('get(acopy)')]
        get = f.at(f.ed.create_node_from_name(names[0], V2(352, 160), [f.pin(opts, 'Options')]), 352, 160)
    tv = f.get('Txt_Value', 576, 96)
    st = f.call('/Script/UMG.TextBlock:SetText', 640, 0)
    f.exec_chain(e, st)
    pins = [str(PIN.get_pin_name(p)) for p in BEL.list_all_pins(get)]
    f.link(opts, 'Options', get, pins[0]); f.link(idx, 'Index', get, pins[1])
    f.link(tv, 'Txt_Value', st, 'self'); f.link(get, pins[2], st, 'InText')
    f.comment('Value text', 'Options[Index] (Step and SetRowIndex keep Index in range)', [e, opts, idx, get, tv, st], C_VISUAL)

    f = Graph(P_, 'ApplyRow')
    e = f.at(entry_node(f), 0, 0)
    lt = f.get('Txt_Label', 224, 160); lv = f.get('Label', 224, 240)
    stl = f.call('/Script/UMG.TextBlock:SetText', 288, 0)
    upd = f.call(self_call(P_, 'UpdateValueText'), 576, 0)
    f.exec_chain(e, stl, upd); f.link(lt, 'Txt_Label', stl, 'self'); f.link(lv, 'Label', stl, 'InText')
    f.comment('Apply row', 'Label and current option', [e, lt, lv, stl, upd], C_VISUAL)

    f = Graph(P_, 'Step')
    e = f.at(entry_node(f), 0, 0)
    idx = f.get('Index', 160, 160)
    add = f.call(f'{KML}:Add_IntInt', 352, 160)
    opts = f.get('Options', 352, 288)
    ln = f.call('/Script/Engine.KismetArrayLibrary:Array_Length', 544, 288)
    wrap = f.call(f'{KML}:Percent_IntInt', 768, 160)
    add2 = f.call(f'{KML}:Add_IntInt', 960, 160)       # +Length first so -1 wraps to the last option
    wrap2 = f.call(f'{KML}:Percent_IntInt', 1152, 160)
    setv = f.set('Index', 1344, 0)
    upd = f.call(self_call(P_, 'UpdateValueText'), 1600, 0)
    bc = call_dispatcher(f, 'OnRowIndexChanged', 1888, 0)
    f.exec_chain(e, setv, upd, bc)
    f.link(idx, 'Index', add, 'A'); f.link(e, 'Delta', add, 'B')
    f.link(opts, 'Options', ln, 'TargetArray')
    f.link(add, 'ReturnValue', wrap, 'A'); f.link(ln, 'ReturnValue', wrap, 'B')
    f.link(wrap, 'ReturnValue', add2, 'A'); f.link(ln, 'ReturnValue', add2, 'B')
    f.link(add2, 'ReturnValue', wrap2, 'A'); f.link(ln, 'ReturnValue', wrap2, 'B')
    f.link(wrap2, 'ReturnValue', setv, 'Index'); f.link(setv, 'Index', bc, 'Index')
    f.comment('Step the option', 'Index = ((Index + Delta) % N + N) % N wraps both ways, then refresh + broadcast',
              [e, idx, add, opts, ln, wrap, add2, wrap2, setv, upd, bc], C_LOGIC)

    f = Graph(P_, 'SetRowIndex')
    e = f.at(entry_node(f), 0, 0)
    options = f.get('Options', 16, 192)
    last = f.call('/Script/Engine.KismetArrayLibrary:Array_LastIndex', 256, 192)
    clamp = f.call(f'{KML}:Clamp', 512, 192, Min=0)
    setv = f.set('Index', 256, 0)
    upd = f.call(self_call(P_, 'UpdateValueText'), 512, 0)
    f.exec_chain(e, setv, upd); f.link(options, 'Options', last, 'TargetArray')
    f.link(e, 'NewIndex', clamp, 'Value'); f.link(last, 'ReturnValue', clamp, 'Max')
    f.link(clamp, 'ReturnValue', setv, 'Index')
    f.comment('Set row index', 'Used when the settings screen loads current values (no broadcast)',
              [e, options, last, clamp, setv, upd], C_LOGIC)

    f = Graph(P_, 'SetOptions')
    e = f.at(entry_node(f), 0, 0)
    seto = f.set('Options', 256, 0)
    seti = f.call(self_call(P_, 'SetRowIndex'), 512, 0)
    f.exec_chain(e, seto, seti); f.link(e, 'NewOptions', seto, 'Options'); f.link(e, 'NewIndex', seti, 'NewIndex')
    f.comment('Set options', 'Runtime lists, e.g. the supported resolutions', [e, seto, seti], C_LOGIC)

    g = Graph(P_).clear()
    pre = g.event('PreConstruct', 0, 0)
    ap = g.call(self_call(P_, 'ApplyRow'), 288, 0)
    g.link(pre, 'then', ap, 'execute')
    g.comment('Design time + runtime', 'Label and current option', [pre, ap], C_EVENT)
    con = g.event('Construct', 0, 192)
    prv = g.get('Btn_Prev', 224, 352)
    b1, e1 = bind_event(g, prv, 'Btn_Prev', 'OnClicked', 'HandlePrevClicked', 352, 192)
    nxt = g.get('Btn_Next', 672, 352)
    b2, e2 = bind_event(g, nxt, 'Btn_Next', 'OnClicked', 'HandleNextClicked', 768, 192)
    g.link(con, 'then', b1, 'execute'); g.link(b1, 'then', b2, 'execute')
    g.at(e1, 0, 448); g.at(e2, 0, 608)
    s1 = g.call(self_call(P_, 'Step'), 352, 448, Delta=-1)
    s2 = g.call(self_call(P_, 'Step'), 352, 608, Delta=1)
    g.link(e1, 'then', s1, 'execute'); g.link(e2, 'then', s2, 'execute')
    g.comment('Chevron clicks', 'Mouse: previous / next option', [con, prv, b1, nxt, b2, e1, e2, s1, s2], C_EVENT)
    focus_rows(g, 800)
    compile_save(P_)

    # OnKeyDown: Left/Right from any device (arrows, d-pad, stick) step the option; everything else navigates
    g = override_graph(P_, 'OnKeyDown')
    assert g is not None, 'add OnKeyDown to the row in the editor first (never from script)'
    e = g.at(entry_node(g), 0, 0)
    ret = g.ed.list_nodes_of_class(unreal.K2Node_FunctionResult)[0]
    for n in list(g.ed.list_all_nodes()):
        if n not in (e, ret):
            g.ed.remove_nodes([n])
    nav = g.call('/Script/Engine.KismetInputLibrary:Key_GetNavigationDirectionFromKey', 224, 160)
    nav_int = g.call(f'{KML}:Conv_ByteToInt', 448, 416)
    left = g.call(f'{KML}:EqualEqual_IntInt', 576, 96, B=0)    # EUINavigation::Left
    right = g.call(f'{KML}:EqualEqual_IntInt', 576, 224, B=1)  # EUINavigation::Right
    bl = g.branch(800, 0)
    sl = g.call(self_call(P_, 'Step'), 1056, -128, Delta=-1)
    br2 = g.branch(1056, 96)
    sr = g.call(self_call(P_, 'Step'), 1312, 0, Delta=1)
    yes = g.call(f'{UWBL}:Handled', 1568, -224)
    no = g.call(f'{UWBL}:Unhandled', 1568, 288)
    r_left = g.at(g.ed.add_return_node(), 1824, -128)
    g.at(ret, 1824, 0)
    r_no = g.at(g.ed.add_return_node(), 1824, 224)
    g.link(e, 'InKeyEvent', nav, 'InKeyEvent')
    g.link(nav, 'ReturnValue', nav_int, 'InByte')
    g.link(nav_int, 'ReturnValue', left, 'A'); g.link(nav_int, 'ReturnValue', right, 'A')
    g.exec_chain(e, bl); g.link(left, 'ReturnValue', bl, 'Condition')
    g.link(bl, 'True', sl, 'execute'); g.link(sl, 'then', r_left, 'execute'); g.link(yes, 'ReturnValue', r_left, 'ReturnValue')
    g.link(bl, 'False', br2, 'execute'); g.link(right, 'ReturnValue', br2, 'Condition')
    g.link(br2, 'True', sr, 'execute'); g.link(sr, 'then', ret, 'execute'); g.link(yes, 'ReturnValue', ret, 'ReturnValue')
    g.link(br2, 'False', r_no, 'execute'); g.link(no, 'ReturnValue', r_no, 'ReturnValue')
    g.comment('Left and right', 'Any device via Key_GetNavigationDirectionFromKey; up/down keep navigating',
              [e, nav, nav_int, left, right, bl, sl, br2, sr, yes, no, r_left, ret, r_no], C_EVENT)
    compile_save(P_, defaults={'bIsFocusable': True, 'Options': ['Off', 'On']})
