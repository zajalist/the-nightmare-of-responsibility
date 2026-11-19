"""WBP_Settings graph (run via ue_remote.py). Reads current values into the rows on Construct and applies each change
immediately: graphics through GameUserSettings (ApplySettings writes GameUserSettings.ini), everything else through
BPFL_FoASettings (SG_FoASettings slot) so audio volumes and reduce motion take effect at once."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
import unreal

P_ = '/Game/FoA/UI/Widgets/Menus/WBP_Settings'
FE_C = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
LIB = '/Game/FoA/UI/Framework/BPFL_FoASettings.BPFL_FoASettings_C'
SG_C = '/Game/FoA/UI/Framework/SG_FoASettings.SG_FoASettings_C'
SL_C = '/Game/FoA/UI/Widgets/Common/WBP_SettingRow_Slider.WBP_SettingRow_Slider_C'
SW_C = '/Game/FoA/UI/Widgets/Common/WBP_SettingRow_Switcher.WBP_SettingRow_Switcher_C'
SB_C = '/Game/FoA/UI/Widgets/Common/WBP_SandButton.WBP_SandButton_C'
GUS = '/Script/Engine.GameUserSettings'
KML = '/Script/Engine.KismetMathLibrary'
T_REAL, T_INT = ptype('real'), ptype('int')
_probe=Graph(P_)
_get_gus=_probe.call(GUS+':GetGameUserSettings',0,-512)
T_GUS=PIN.get_pin_type(_probe.pin(_get_gus,'ReturnValue','out'))
_probe.ed.remove_nodes([_get_gus])
FRAME_CAPS = (30.0, 60.0, 120.0, 0.0)  # Switcher options: 30, 60, 120, Unlimited

# Row name -> (kind, apply spec). kind: 'slider' (real) or 'switch' (int)
GRAPHICS = [('Row_Quality', 'switch', 'gus', 'SetOverallScalabilityLevel', 'Value'),
            ('Row_WindowMode', 'switch', 'gus_enum', 'SetFullscreenMode', 'InFullscreenMode'),
            ('Row_VSync', 'switch', 'gus_bool', 'SetVSyncEnabled', 'bEnable'),
            ('Row_FrameCap', 'switch', 'gus_cap', 'SetFrameRateLimit', 'NewLimit'),
            ('Row_ResScale', 'slider', 'gus', 'SetResolutionScaleValueEx', 'NewScaleValue'),
            ('Row_Resolution', 'switch', 'gus_res', 'SetScreenResolution', 'Resolution')]
SAVED = [('Row_Master', 'slider', 'MasterVolume'), ('Row_Effects', 'slider', 'EffectsVolume'),
         ('Row_Ambience', 'slider', 'AmbienceVolume'), ('Row_Interface', 'slider', 'InterfaceVolume'),
         ('Row_Sensitivity', 'slider', 'MouseSensitivity'), ('Row_InvertY', 'switch_bool', 'bInvertY'),
         ('Row_Subtitles', 'switch_bool', 'bSubtitles'), ('Row_SubtitleSize', 'switch', 'SubtitleSize'),
         ('Row_ReduceMotion', 'switch_bool', 'bReduceMotion'), ('Row_PhotoWarning', 'switch_bool', 'bShowPhotoWarning')]
TABS = (('Btn_TabGraphics', 0), ('Btn_TabAudio', 1), ('Btn_TabControls', 2), ('Btn_TabAccess', 3))

ensure_vars(P_, [('Host', ptype(unreal.load_class(None, FE_C)), '', 'Screen', False),
                 ('Settings', ptype(unreal.load_class(None, SG_C)), '', 'Settings|State', False),
                 ('GUS', T_GUS, '', 'Settings|State', False),
                 ('Resolutions', BEL.get_array_type(ptype(unreal.IntPoint)), '', 'Settings|State', False)])
BEL.change_member_variable_type(unreal.load_asset(P_), 'GUS', T_GUS)
handlers = [f'On{r[4:]}Changed' for r, *_ in GRAPHICS + SAVED]
for f in ['ShowPage', 'LoadGraphicsRows', 'LoadSavedRows', 'BuildResolutionOptions', 'ApplySaved'] + handlers:
    drop_function(P_, f)
Graph.function(P_, 'ShowPage', inputs=[('Index', T_INT)])
for f in ('LoadGraphicsRows', 'LoadSavedRows', 'BuildResolutionOptions', 'ApplySaved'):
    Graph.function(P_, f)
for (row, kind, *_), h in zip(GRAPHICS + SAVED, handlers):
    Graph.function(P_, h, inputs=[('Value' if kind == 'slider' else 'Index', T_REAL if kind == 'slider' else T_INT)])


def fn(name):
    g = Graph(P_, name)
    return g, g.at(entry_node(g), 0, 0)


# ShowPage(Index): switch the right-hand page
g, e = fn('ShowPage')
sw = g.get('Switch_Pages', 224, 160)
seti = g.call('/Script/UMG.WidgetSwitcher:SetActiveWidgetIndex', 288, 0)
g.exec_chain(e, seti); g.link(sw, 'Switch_Pages', seti, 'self'); g.link(e, 'Index', seti, 'Index')
g.comment('Show page', '', [e, sw, seti], C_VISUAL)
tail = seti
for name, index in TABS:
    x = 620 + index * 1080
    button = g.get(name, x, 220)
    equal = g.call(KML + ':EqualEqual_IntInt', x, 420, B=index)
    alpha = g.call(KML + ':SelectFloat', x + 250, 420, A=1.0, B=0.62)
    store = g.set('TextAlphaRest', x + 500, 0, class_path=SB_C)
    push = g.call(SB_C + ':PushState', x + 780, 0)
    g.link(e, 'Index', equal, 'A'); g.link(equal, 'ReturnValue', alpha, 'bPickA')
    g.link(alpha, 'ReturnValue', store, 'TextAlphaRest'); g.link(button, name, store, 'self')
    g.link(button, name, push, 'self'); g.exec_chain(tail, store, push)
    g.comment('Current settings page', '', [button, equal, alpha, store, push], C_VISUAL)
    tail = push

# ApplySaved: push the save object to audio/accessibility and persist it (every non-graphics change ends here)
g, e = fn('ApplySaved')
s1 = g.get('Settings', 224, 160)
ap = g.call(f'{LIB}:ApplySettings', 288, 0)
s2 = g.get('Settings', 544, 160)
sv = g.call(f'{LIB}:SaveSettings', 608, 0)
g.exec_chain(e, ap, sv); g.link(s1, 'Settings', ap, 'Settings'); g.link(s2, 'Settings', sv, 'Settings')
g.comment('Apply + save', 'Volumes and reduce motion take effect now; the slot persists them', [e, s1, ap, s2, sv], C_DATA)

fe = g.call('/Script/Engine.GameplayStatics:GetActorOfClass', 1152, 0, ActorClass=FE_C)
valid = g.call('/Script/Engine.KismetSystemLibrary:IsValid', 1152, 224); fe_ok = g.branch(1440, 0)
hud = g.get('HUD', 1728, 224, class_path=FE_C)
hud_valid = g.call('/Script/Engine.KismetSystemLibrary:IsValid', 2016, 224); hud_ok = g.branch(2016, 0)
names = [n for n in g.ed.list_available_nodes([]) if n.replace(' ', '').endswith('CastToWBP_HUD')]
assert names, 'WBP_HUD.ApplySubtitleSettings must be built before Settings'
cast = g.at(g.ed.create_node_from_name(names[0], V2(2304, 0), []), 2304, 0)
subtitle = g.call('/Game/FoA/UI/Game/WBP_HUD.WBP_HUD_C:ApplySubtitleSettings', 2656, 0)
settings = g.get('Settings', 2656, 224)
g.exec_chain(sv, fe, fe_ok); g.link(fe, 'ReturnValue', valid, 'Object'); g.link(valid, 'ReturnValue', fe_ok, 'Condition')
g.link(fe, 'ReturnValue', hud, 'self'); g.link(hud, 'HUD', hud_valid, 'Object')
g.link(hud_valid, 'ReturnValue', hud_ok, 'Condition'); g.link(fe_ok, 'True', hud_ok, 'execute')
g.link(hud, 'HUD', cast, 'Object'); g.link(hud_ok, 'True', cast, 'execute'); g.exec_chain(cast, subtitle)
g.link(cast, 'AsWBP_HUD', subtitle, 'self'); g.link(settings, 'Settings', subtitle, 'Settings')
g.comment('Apply subtitle preferences', '', [fe, valid, fe_ok, hud, hud_valid, hud_ok, cast, subtitle, settings], C_DATA)

# BuildResolutionOptions: curated 16:9 + ultrawide sizes (Row_Resolution's Options hold the same list as text).
# Script-made loop macros crashed the editor (19:30), so the list is a MakeArray instead of a loop over
# GetSupportedFullscreenResolutions; resolution scale covers everything in between.
RESOLUTIONS = ((1280, 720), (1600, 900), (1920, 1080), (2560, 1440), (3840, 2160), (2560, 1080), (3440, 1440))
g, e = fn('BuildResolutionOptions')
mk = g.node('Utilities|Array|MakeArray', 224, 160)
for _ in RESOLUTIONS[1:]:
    g.ed.add_node_pin(mk)
setr = g.set('Resolutions', 544, 0)
g.exec_chain(e, setr)
g.link(mk, 'Array', setr, 'Resolutions')          # wire first: the wildcard pins become IntPoint
for i, (w, h) in enumerate(RESOLUTIONS):
    g.default(mk, f'[{i}]', f'(X={w},Y={h})')
gus = g.get('GUS', 544, 288)
cur = g.call(f'{GUS}:GetScreenResolution', 608, 288)
find = g.call('/Script/Engine.KismetArrayLibrary:Array_Find', 864, 160)
clampi = g.call(f'{KML}:Max', 1088, 160)
row = g.get('Row_Resolution', 1088, 96)
seti = g.call(f'{SW_C}:SetRowIndex', 1344, 0)
g.link(gus, 'GUS', cur, 'self')
g.link(cur, 'ReturnValue', find, 'ItemToFind'); g.link(setr, 'Resolutions', find, 'TargetArray')
g.link(find, 'ReturnValue', clampi, 'A'); g.default(clampi, 'B', 0)
g.link(setr, 'then', seti, 'execute'); g.link(row, 'Row_Resolution', seti, 'self'); g.link(clampi, 'ReturnValue', seti, 'NewIndex')
g.comment('Resolution options', 'Curated 16:9 + ultrawide list; the current size is preselected (first entry if unlisted)',
          [e, mk, setr, gus, cur, find, clampi, row, seti], C_DATA)

# LoadGraphicsRows: current GameUserSettings into the graphics rows
g, e = fn('LoadGraphicsRows')
prev, nodes = e, [e]
reads = (('Row_Quality', 'GetOverallScalabilityLevel', None), ('Row_WindowMode', 'GetFullscreenMode', 'enum'),
         ('Row_VSync', 'IsVSyncEnabled', 'bool'))
for i, (row, getter, conv) in enumerate(reads):
    x = 288 + i * 448
    gus = g.get('GUS', x - 64, 288)
    val = g.call(f'{GUS}:{getter}', x - 64, 192)
    g.link(gus, 'GUS', val, 'self')
    src = (val, 'ReturnValue')
    if conv == 'enum':
        c = g.call(f'{KML}:Conv_ByteToInt', x + 160, 288); g.link(val, 'ReturnValue', c, 'InByte'); src = (c, 'ReturnValue')
        nodes.append(c)
    elif conv == 'bool':
        c = g.call(f'{KML}:Conv_BoolToInt', x + 160, 288); g.link(val, 'ReturnValue', c, 'InBool'); src = (c, 'ReturnValue')
        nodes.append(c)
    rw = g.get(row, x + 64, 96)
    setter = g.call(f'{SL_C if conv == "slider" else SW_C}:{"SetRowValue" if conv == "slider" else "SetRowIndex"}',
                    x + 128, 0)
    g.link(prev, 'then', setter, 'execute'); g.link(rw, row, setter, 'self')
    g.link(src[0], src[1], setter, 'NewValue' if conv == 'slider' else 'NewIndex')
    prev = setter
    nodes += [gus, val, rw, setter]
# Resolution quality 0 means the engine's default; show real percent instead of a normalized fraction.
gus_scale = g.get('GUS', 1632, 288)
scale_info = g.call(f'{GUS}:GetResolutionScaleInformationEx', 1632, 448)
default_scale = g.call(f'{GUS}:GetDefaultResolutionScale', 1632, 0)
positive_scale = g.call(f'{KML}:Greater_DoubleDouble', 1984, 640, B=0.0)
select_scale = g.call(f'{KML}:SelectFloat', 2272, 512)
scale_row = g.get('Row_ResScale', 1984, 96)
set_scale = g.call(f'{SL_C}:SetRowValue', 1984, 0)
g.link(gus_scale, 'GUS', scale_info, 'self'); g.link(gus_scale, 'GUS', default_scale, 'self')
g.link(scale_info, 'CurrentScaleValue', positive_scale, 'A')
g.link(scale_info, 'CurrentScaleValue', select_scale, 'A'); g.link(default_scale, 'ReturnValue', select_scale, 'B')
g.link(positive_scale, 'ReturnValue', select_scale, 'bPickA'); g.link(select_scale, 'ReturnValue', set_scale, 'NewValue')
g.link(scale_row, 'Row_ResScale', set_scale, 'self'); g.exec_chain(prev, default_scale, set_scale)
nodes += [gus_scale, scale_info, default_scale, positive_scale, select_scale, scale_row, set_scale]
prev = set_scale
# Frame cap: index of the current limit in (30, 60, 120, 0)
gus = g.get('GUS', 2048, 288)
lim = g.call(f'{GUS}:GetFrameRateLimit', 2048, 192)
mk = g.node('Utilities|Array|MakeArray', 2304, 288)
g.ed.add_node_pin(mk); g.ed.add_node_pin(mk); g.ed.add_node_pin(mk)
find = g.call('/Script/Engine.KismetArrayLibrary:Array_Find', 2560, 192)
clampi = g.call(f'{KML}:Max', 2816, 192)
rw = g.get('Row_FrameCap', 2816, 96)
setter = g.call(f'{SW_C}:SetRowIndex', 3072, 0)
g.link(gus, 'GUS', lim, 'self'); g.link(lim, 'ReturnValue', find, 'ItemToFind'); g.link(mk, 'Array', find, 'TargetArray')
for i, v in enumerate(FRAME_CAPS):
    g.default(mk, f'[{i}]', v)
g.link(find, 'ReturnValue', clampi, 'A'); g.default(clampi, 'B', 0); g.link(prev, 'then', setter, 'execute'); g.link(rw, 'Row_FrameCap', setter, 'self')
g.link(clampi, 'ReturnValue', setter, 'NewIndex')
res = g.call(self_call(P_, 'BuildResolutionOptions'), 3392, 0)
g.link(setter, 'then', res, 'execute')
g.comment('Graphics rows', 'Quality, window mode, VSync, resolution scale, frame cap and resolution from GameUserSettings',
          nodes + [gus, lim, mk, find, clampi, rw, setter, res], C_DATA)

# LoadSavedRows: the save slot into the audio / controls / accessibility rows
g, e = fn('LoadSavedRows')
prev, nodes = e, [e]
for i, (row, kind, var) in enumerate(SAVED):
    x = 288 + i * 416
    st = g.get('Settings', x - 64, 288)
    val = g.get(var, x - 64, 192, class_path=SG_C)
    g.link(st, 'Settings', val, 'self')
    src = (val, var)
    if kind == 'switch_bool':
        c = g.call(f'{KML}:Conv_BoolToInt', x + 160, 288); g.link(val, var, c, 'InBool'); src = (c, 'ReturnValue')
        nodes.append(c)
    rw = g.get(row, x + 64, 96)
    setter = g.call(f'{SL_C if kind == "slider" else SW_C}:{"SetRowValue" if kind == "slider" else "SetRowIndex"}',
                    x + 128, 0)
    g.link(prev, 'then', setter, 'execute'); g.link(rw, row, setter, 'self')
    g.link(src[0], src[1], setter, 'NewValue' if kind == 'slider' else 'NewIndex')
    prev = setter
    nodes += [st, val, rw, setter]
g.comment('Saved rows', 'Audio, controls and accessibility from the "Settings" slot', nodes, C_DATA)

# Handlers: one tiny function per row
deferred_caps = None
for (row, kind, how, setter_fn, pin), h in zip(GRAPHICS, handlers[:len(GRAPHICS)]):
    g, e = fn(h)
    gus = g.get('GUS', 224, 192)
    arg = (e, 'Value' if kind == 'slider' else 'Index')
    extra = []
    if how == 'gus_enum':
        c = g.call(f'{KML}:Conv_IntToByte', 224, 288); g.link(e, 'Index', c, 'InInt'); arg = (c, 'ReturnValue'); extra.append(c)
    elif how == 'gus_bool':
        c = g.call(f'{KML}:EqualEqual_IntInt', 224, 288, B=1); g.link(e, 'Index', c, 'A'); arg = (c, 'ReturnValue')
        extra.append(c)
    elif how == 'gus_cap':
        mk = g.node('Utilities|Array|MakeArray', 96, 288)
        g.ed.add_node_pin(mk); g.ed.add_node_pin(mk); g.ed.add_node_pin(mk)
        getv = g.call('/Script/Engine.KismetArrayLibrary:Array_Get', 352, 288)
        g.link(e, 'Index', getv, 'Index'); arg = (getv, 'Item'); extra += [mk, getv]
        deferred_caps = (mk, getv)
    elif how == 'gus_res':
        rs = g.get('Resolutions', 96, 288)
        getv = g.call('/Script/Engine.KismetArrayLibrary:Array_Get', 352, 288)
        g.link(rs, 'Resolutions', getv, 'TargetArray'); g.link(e, 'Index', getv, 'Index'); arg = (getv, 'Item')
        extra += [rs, getv]
    call = g.call(f'{GUS}:{setter_fn}', 640, 0)
    if how == 'gus_cap':
        g.link(arg[0], arg[1], call, pin)
        g.link(deferred_caps[0], 'Array', deferred_caps[1], 'TargetArray')
        for i, v in enumerate(FRAME_CAPS):
            g.default(deferred_caps[0], f'[{i}]', v)
    gus2 = g.get('GUS', 896, 192)
    apply_ = g.call(f'{GUS}:ApplySettings', 960, 0, bCheckForCommandLineOverrides='false')
    g.exec_chain(e, call, apply_)
    g.link(gus, 'GUS', call, 'self'); g.link(gus2, 'GUS', apply_, 'self')
    if how != 'gus_cap':
        g.link(arg[0], arg[1], call, pin)
    g.comment(words(h), f'{setter_fn} then ApplySettings (also writes GameUserSettings.ini)', [e, gus, call, gus2, apply_] + extra,
              C_DATA)
for (row, kind, var), h in zip(SAVED, handlers[len(GRAPHICS):]):
    g, e = fn(h)
    st = g.get('Settings', 224, 192)
    setv = g.set(var, 288, 0, class_path=SG_C)
    g.link(st, 'Settings', setv, 'self')
    if kind == 'switch_bool':
        c = g.call(f'{KML}:EqualEqual_IntInt', 96, 288, B=1); g.link(e, 'Index', c, 'A'); g.link(c, 'ReturnValue', setv, var)
        extra = [c]
    else:
        g.link(e, 'Value' if kind == 'slider' else 'Index', setv, var); extra = []
    ap = g.call(self_call(P_, 'ApplySaved'), 608, 0)
    g.exec_chain(e, setv, ap)
    g.comment(words(h), f'Store {var}, apply and save', [e, st, setv, ap] + extra, C_DATA)

# Event graph: Construct -> host, settings, load rows, bind tabs / back / rows, first page, focus
g = Graph(P_).clear()
con = g.event('Construct', 0, 0)
find, cast, seth = host_lookup(g, FE_C, 256, 0)
gget = g.call(f'{GUS}:GetGameUserSettings', 1024, 160)
setg = g.set('GUS', 1088, 0)
load = g.call(f'{LIB}:LoadSettings', 1344, 160)
sets = g.set('Settings', 1408, 0)
lg = g.call(self_call(P_, 'LoadGraphicsRows'), 1664, 0)
ls = g.call(self_call(P_, 'LoadSavedRows'), 1984, 0)
g.link(con, 'then', find, 'execute'); g.exec_chain(seth, gget, setg, load, sets, lg, ls)  # both impure: wired
g.link(gget, 'ReturnValue', setg, 'GUS'); g.link(load, 'Settings', sets, 'Settings')
g.comment('Read current settings', 'GameUserSettings for graphics, the save slot for the rest',
          [con, find, cast, seth, gget, setg, load, sets, lg, ls], C_EVENT)
prev, binds, x = ls, [], 2304
tab_events = []
for btn, idx in TABS + (('Btn_Back', -1),):
    src = g.get(btn, x - 64, 192)
    b, ev = bind_event(g, src, btn, 'OnSandClicked', f'On{btn[4:]}Clicked', x, 0)
    g.link(prev, 'then', b, 'execute'); prev = b; binds += [src, b]; tab_events.append((ev, idx)); x += 384
for (row, kind, *_), h in zip(GRAPHICS + SAVED, handlers):
    src = g.get(row, x - 64, 192)
    disp = 'OnRowValueChanged' if kind == 'slider' else 'OnRowIndexChanged'
    b, mk = bind_function(g, src, row, disp, h, x, 0)
    g.link(prev, 'then', b, 'execute'); prev = b; binds += [src, b, mk]; x += 384
page0 = g.call(self_call(P_, 'ShowPage'), x, 0, Index=0)
tab0 = g.get('Btn_TabGraphics', x + 256, 192)
foc = g.call(f'{SB_C}:FocusButton', x + 320, 0)
g.link(prev, 'then', page0, 'execute'); g.link(page0, 'then', foc, 'execute'); g.link(tab0, 'Btn_TabGraphics', foc, 'self')
g.comment('Bind tabs and rows', 'Each row change runs its own small apply function', binds + [page0, tab0, foc],
          C_EVENT)
hn = []
for i, (ev, idx) in enumerate(tab_events):
    y = 512 + i * 160
    g.at(ev, 0, y)
    if idx >= 0:
        call = g.call(self_call(P_, 'ShowPage'), 384, y, Index=idx)
        g.link(ev, 'then', call, 'execute'); hn += [ev, call]
    else:
        host = g.get('Host', 320, y + 96)
        call = g.call(f'{FE_C}:CloseOverlay', 384, y)
        g.link(ev, 'then', call, 'execute'); g.link(host, 'Host', call, 'self'); hn += [ev, host, call]
g.comment('Tabs and Back', 'Pages switch in place; Back closes the overlay', hn, C_LOGIC)
# Back remains available while a row or tab has focus.
g = override_graph(P_, 'OnKeyDown')
assert g is not None, 'Create the OnKeyDown override through Hayba before wiring Settings'
e = g.at(entry_node(g), 0, 0)
key = g.call('/Script/Engine.KismetInputLibrary:GetKey', 224, 192)
esc = g.call('/Script/Engine.KismetInputLibrary:EqualEqual_KeyKey', 480, 160)
pad = g.call('/Script/Engine.KismetInputLibrary:EqualEqual_KeyKey', 480, 288)
either = g.call(f'{KML}:BooleanOR', 736, 192); branch = g.branch(992, 0)
host = g.get('Host', 1216, 192); close = g.call(f'{FE_C}:CloseOverlay', 1280, 0)
yes = g.call('/Script/UMG.WidgetBlueprintLibrary:Handled', 1568, 192)
no = g.call('/Script/UMG.WidgetBlueprintLibrary:Unhandled', 1568, 384)
ret = g.at(g.ed.list_nodes_of_class(unreal.K2Node_FunctionResult)[0], 1856, 0)
ret_no = g.at(g.ed.add_return_node(), 1856, 320)
g.link(e, 'InKeyEvent', key, 'Input'); g.link(key, 'ReturnValue', esc, 'A'); g.link(key, 'ReturnValue', pad, 'A')
assert PIN.set_pin_value(g.pin(esc,'B','in'), 'Escape')
assert PIN.set_pin_value(g.pin(pad,'B','in'), 'Gamepad_FaceButton_Right')
g.link(esc, 'ReturnValue', either, 'A'); g.link(pad, 'ReturnValue', either, 'B')
g.link(either, 'ReturnValue', branch, 'Condition'); g.exec_chain(e, branch)
g.link(host, 'Host', close, 'self'); g.link(branch, 'True', close, 'execute'); g.exec_chain(close, ret)
g.link(yes, 'ReturnValue', ret, 'ReturnValue'); g.link(branch, 'False', ret_no, 'execute')
g.link(no, 'ReturnValue', ret_no, 'ReturnValue')
g.comment('Settings Back key', '', [e, key, esc, pad, either, branch, host, close, yes, no, ret, ret_no], C_EVENT)
compile_save(P_, defaults={'bIsFocusable': True})
