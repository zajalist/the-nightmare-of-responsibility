"""Wire the recorded UI sound set (/Game/FoA/Audio/SFX/UI, SoundWaves on SC_UI), Hayba, in place. One sound per event:
  focus or hover  SFX_UI_Hover_A     every SandButton (class default, and the instances that were silenced)
  activate        SFX_UI_Confirm_A   SandButton class default; the front end's SndConfirm (dialog confirm)
  Esc or B        SFX_UI_Back_A      front end SndBack (HandleBack), now also on the bare menu's Back to title
  overlay open    SFX_UI_Open_A      front end OpenOverlay; buttons that open an overlay stay silent on click
  overlay close   SFX_UI_Close_A     the click of buttons that close one (dialog Stay, Credits Back)
  pages           SFX_UI_PageTurn_A  WBP_Settings.ShowPage when the page actually changes; tab clicks silent
  value steps     SFX_UI_SliderTick_A  slider HandleSliderChanged and switcher Step, at most one per 50 ms
  pause           SFX_UI_PauseIn_A / SFX_UI_PauseOut_A  front end SndPauseIn / SndPauseOut
  phone           SFX_UI_PhoneBuzz_A on BP_Phone.OpenPhone; SFX_UI_PhoneTap_A on its navigation functions
All new plays are PlaySound2D with bIsUISound, so they play while paused.
  python Tools/Unreal/ui/aaa_sounds.py"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

A = '/Game/FoA/Audio/SFX/UI'
S = lambda n: f'{A}/{n}.{n}'  # noqa: E731
OBJ = lambda n: f"/Script/Engine.SoundWave'{S(n)}'"  # noqa: E731
FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
GS = '/Script/Engine.GameplayStatics'
KML = '/Script/Engine.KismetMathLibrary'


def c(cmd, **p):
    r = hc.call(cmd, p)
    d = r.get('data') or {}
    tag = p.get('graph_name') or p.get('widget_name') or ''
    print(cmd, p.get('path', p.get('widget_blueprint_path', '')).rsplit('/', 1)[-1], tag, r.get('ok'),
          d.get('applied', d.get('succeeded', '')), d.get('error') or r.get('error') or '')
    return d


def graph(bp, g):
    nodes, edges, off = [], [], 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': bp, 'graph_name': g, 'offset': off})['data']
        nodes += d['nodes']
        off = d['page']['nodes']['next_offset']
    off = 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': bp, 'graph_name': g, 'edge_offset': off})['data']
        edges += d['edges']
        off = d['page']['edges']['next_offset']
    return nodes, edges


def already(nodes, sound):
    return any(sound in str(p.get('default_value') or p.get('default_object') or '') for n in nodes for p in n['pins'])


def play_ops(ref, sound, x, y):
    return [{'op': 'add_node', 'ref': ref, 'node_type': 'call_function', 'function_name': f'{GS}:PlaySound2D', 'x': x, 'y': y},
            {'op': 'set_pin', 'node_id': ref, 'pin_name': 'Sound', 'value': S(sound)},
            {'op': 'set_pin', 'node_id': ref, 'pin_name': 'bIsUISound', 'value': 'true'}]


def after_entry(bp, g, sound, gate=None, compile_=False):
    """entry -> [gate branch] -> PlaySound2D(sound) -> old next. gate(nodes) returns (ops, cond_ref, extra_ids)."""
    nodes, edges = graph(bp, g)
    if already(nodes, sound):
        print(bp.rsplit('/', 1)[1], g, 'already plays', sound)
        return
    entry = next(n['node_id'] for n in nodes if n['title'].replace(' ', '') == g.replace(' ', ''))
    nxt = [e for e in edges if e['from_node'] == entry and e['from_pin'] == 'then']
    ops = [{'op': 'disconnect', 'node_id': entry, 'pin_name': 'then', 'to_node': e['to_node'], 'to_pin': e['to_pin']} for e in nxt]
    ops += play_ops('snd', sound, 200, -260)
    ids = ['snd']
    if gate:
        gops, cond, extra = gate(nodes)
        ops += gops + [{'op': 'add_node', 'ref': 'gb', 'node_type': 'branch', 'x': 40, 'y': -260},
                       {'op': 'connect', 'from_node': cond, 'from_pin': 'ReturnValue', 'to_node': 'gb', 'to_pin': 'Condition'},
                       {'op': 'connect', 'from_node': entry, 'from_pin': 'then', 'to_node': 'gb', 'to_pin': 'execute'},
                       {'op': 'connect', 'from_node': 'gb', 'from_pin': 'then', 'to_node': 'snd', 'to_pin': 'execute'}]
        ids += ['gb'] + extra
        tail = gate.tail if hasattr(gate, 'tail') else 'snd'
        for e in nxt:
            ops += [{'op': 'connect', 'from_node': 'gb', 'from_pin': 'else', 'to_node': e['to_node'], 'to_pin': e['to_pin']}]
    else:
        ops += [{'op': 'connect', 'from_node': entry, 'from_pin': 'then', 'to_node': 'snd', 'to_pin': 'execute'}]
        tail = 'snd'
    for e in nxt:
        ops += [{'op': 'connect', 'from_node': tail, 'from_pin': 'then', 'to_node': e['to_node'], 'to_pin': e['to_pin']}]
    ops += [{'op': 'comment', 'title': 'UI sound', 'node_ids': ids, 'color': [0.30, 0.22, 0.10]}]
    c('blueprint_graph_batch', path=bp, graph_name=g, ops=ops, compile=compile_, save=compile_)


def throttle(bp):
    """now - LastSoundT >= 0.05 -> play, then LastSoundT = now (at most 20 ticks a second)."""
    c('blueprint_add_variable', path=bp, variable_name='LastSoundT', variable_type='real', default_value='-1.0',
      category='Sound', update_existing=True)

    def gate(nodes):
        return ([{'op': 'add_node', 'ref': 'now', 'node_type': 'call_function', 'function_name': f'{GS}:GetRealTimeSeconds', 'x': -200, 'y': -120},
                 {'op': 'add_node', 'ref': 'last', 'node_type': 'variable_get', 'variable_name': 'LastSoundT', 'x': -200, 'y': -60},
                 {'op': 'add_node', 'ref': 'dt', 'node_type': 'call_function', 'function_name': f'{KML}:Subtract_DoubleDouble', 'x': -40, 'y': -120},
                 {'op': 'add_node', 'ref': 'ok', 'node_type': 'call_function', 'function_name': f'{KML}:GreaterEqual_DoubleDouble', 'x': -40, 'y': -60},
                 {'op': 'set_pin', 'node_id': 'ok', 'pin_name': 'B', 'value': '0.05'},
                 {'op': 'connect', 'from_node': 'now', 'from_pin': 'ReturnValue', 'to_node': 'dt', 'to_pin': 'A'},
                 {'op': 'connect', 'from_node': 'last', 'from_pin': 'LastSoundT', 'to_node': 'dt', 'to_pin': 'B'},
                 {'op': 'connect', 'from_node': 'dt', 'from_pin': 'ReturnValue', 'to_node': 'ok', 'to_pin': 'A'},
                 {'op': 'add_node', 'ref': 'stamp', 'node_type': 'variable_set', 'variable_name': 'LastSoundT', 'x': 420, 'y': -260},
                 {'op': 'connect', 'from_node': 'now', 'from_pin': 'ReturnValue', 'to_node': 'stamp', 'to_pin': 'LastSoundT'},
                 {'op': 'connect', 'from_node': 'snd', 'from_pin': 'then', 'to_node': 'stamp', 'to_pin': 'execute'}],
                'ok', ['now', 'last', 'dt', 'ok', 'stamp'])
    gate.tail = 'stamp'
    return gate


def page_changed(nodes):
    entry = next(n['node_id'] for n in nodes if n['title'] == 'ShowPage')
    return ([{'op': 'add_node', 'ref': 'sw', 'node_type': 'variable_get', 'variable_name': 'Switch_Pages', 'x': -200, 'y': -120},
             {'op': 'add_node', 'ref': 'cur', 'node_type': 'call_function', 'function_name': '/Script/UMG.WidgetSwitcher:GetActiveWidgetIndex', 'x': -200, 'y': -60},
             {'op': 'connect', 'from_node': 'sw', 'from_pin': 'Switch_Pages', 'to_node': 'cur', 'to_pin': 'self'},
             {'op': 'add_node', 'ref': 'ne', 'node_type': 'call_function', 'function_name': f'{KML}:NotEqual_IntInt', 'x': -40, 'y': -60},
             {'op': 'connect', 'from_node': entry, 'from_pin': 'Index', 'to_node': 'ne', 'to_pin': 'A'},
             {'op': 'connect', 'from_node': 'cur', 'from_pin': 'ReturnValue', 'to_node': 'ne', 'to_pin': 'B'}],
            'ne', ['sw', 'cur', 'ne'])


def instances():
    W = '/Game/FoA/UI/Widgets'
    plan = {f'{W}/Menus/WBP_MainMenu': {b: ('SFX_UI_Hover_A', None) for b in ('Btn_WakeUp', 'Btn_Settings', 'Btn_Credits', 'Btn_Quit')},
            f'{W}/Menus/WBP_Pause': {b: ('SFX_UI_Hover_A', None) for b in ('Btn_Resume', 'Btn_Settings', 'Btn_RestartDay', 'Btn_QuitToTitle')},
            f'{W}/Common/WBP_ConfirmDialog': {'Btn_Confirm': ('SFX_UI_Hover_A', None), 'Btn_Cancel': ('SFX_UI_Hover_A', 'SFX_UI_Close_A')},
            f'{W}/Menus/WBP_Settings': {b: ('SFX_UI_Hover_A', None) for b in ('Btn_TabGraphics', 'Btn_TabAudio', 'Btn_TabControls', 'Btn_TabAccess')},
            f'{W}/Menus/WBP_Credits': {'Btn_Back': ('SFX_UI_Hover_A', 'SFX_UI_Close_A')},
            '/Game/FoA/UI/Game/WBP_Phone': {'Btn_Action': ('SFX_UI_Hover_A', 'SFX_UI_PhoneTap_A')}}  # mouse path; keys tap via BP_Phone
    for wbp, btns in plan.items():
        for b, (hov, clk) in btns.items():
            c('ui_set_widget_properties', widget_blueprint_path=wbp, widget_name=b,
              properties={'HoverSound': OBJ(hov) if hov else 'None', 'ClickSound': OBJ(clk) if clk else 'None'})
        c('ui_compile_widget', widget_blueprint_path=wbp)
        c('ui_save_widget', widget_blueprint_path=wbp)


def graphs():
    after_entry(FE, 'OpenOverlay', 'SFX_UI_Open_A', compile_=True)
    after_entry('/Game/FoA/UI/Widgets/Common/WBP_SettingRow_Slider', 'HandleSliderChanged', 'SFX_UI_SliderTick_A',
                gate=throttle('/Game/FoA/UI/Widgets/Common/WBP_SettingRow_Slider'), compile_=True)
    after_entry('/Game/FoA/UI/Widgets/Common/WBP_SettingRow_Switcher', 'Step', 'SFX_UI_SliderTick_A',
                gate=throttle('/Game/FoA/UI/Widgets/Common/WBP_SettingRow_Switcher'), compile_=True)
    after_entry('/Game/FoA/UI/Widgets/Menus/WBP_Settings', 'ShowPage', 'SFX_UI_PageTurn_A', gate=page_changed, compile_=True)
    P = '/Game/FoA/UI/Game/BP_Phone'
    after_entry(P, 'OpenPhone', 'SFX_UI_PhoneBuzz_A')
    for f in ('PhoneConfirm', 'PhoneBack', 'PhoneNext', 'PhonePrevious', 'PhoneDown', 'PhoneUp'):
        after_entry(P, f, 'SFX_UI_PhoneTap_A')
    c('blueprint_compile', path=P)


def back_to_title():
    """The bare menu's Back to title plays SndBack too (HandleBack only sounded when it closed an overlay)."""
    nodes, edges = graph(FE, 'HandleBack')
    show = next(n['node_id'] for n in nodes if n['title'].replace(' ', '').startswith('ShowScreen'))
    if any(e['from_node'] == show and e['from_pin'] == 'then' for e in edges):
        print('HandleBack: ShowScreen already chained')
        return
    c('blueprint_graph_batch', path=FE, graph_name='HandleBack', compile=True, save=True, ops=[
        {'op': 'add_node', 'ref': 'sb', 'node_type': 'variable_get', 'variable_name': 'SndBack', 'x': 2400, 'y': 400},
        {'op': 'add_node', 'ref': 'pu', 'node_type': 'call_function', 'function_name': f'{FE}.BP_FoAFrontEnd_C:PlayUISound', 'x': 2480, 'y': 240},
        {'op': 'connect', 'from_node': 'sb', 'from_pin': 'SndBack', 'to_node': 'pu', 'to_pin': 'Cue'},
        {'op': 'connect', 'from_node': show, 'from_pin': 'then', 'to_node': 'pu', 'to_pin': 'execute'}])


instances()
graphs()
back_to_title()
