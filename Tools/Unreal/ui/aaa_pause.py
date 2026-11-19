"""AAA pass, pause (Hayba, in place).
  mat    M_UI_Scrim gains Tear (default 0): rows of the frozen frame are torn by dark bars that jump at 15 Hz
         (Custom "Scrim tear", hlsl/scrim_tear.hlsl); Opacity = max(gradient, tear). Every scrim instance keeps Tear 0.
  graph  WBP_Pause Tick (world timers stop while paused; widget Tick does not, and it only runs while the menu shows):
         a real-time gap over 0.25 s marks a fresh pause, PauseT restarts; for 0.8 s the scrim tear settles over 0.3 s
         (ease out), header and goal fade in from 0.1 s, and the four words form from sand 50 ms apart.
  python Tools/Unreal/ui/aaa_pause.py mat|graph"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

M = '/Game/FoA/UI/Materials/M_UI_Scrim'
P = '/Game/FoA/UI/Widgets/Menus/WBP_Pause'
KML = '/Script/Engine.KismetMathLibrary'
SB = '/Game/FoA/UI/Widgets/Common/WBP_SandButton.WBP_SandButton_C:SetReveal'
BTNS = ('Btn_Resume', 'Btn_Settings', 'Btn_RestartDay', 'Btn_QuitToTitle')


def c(cmd, **p):
    r = hc.call(cmd, p)
    d = r.get('data') or {}
    print(cmd, r.get('ok'), d.get('node_id') or d.get('applied') or '', d.get('failed_index') if 'failed_index' in d else '',
          d.get('error') or r.get('error') or '', json.dumps(d.get('compile') or d.get('stats') or '')[:220])
    return d


def mat():
    info = hc.call('material_get_info', {'path': M})['data']
    if any(n.get('parameter_name') == 'Tear' for n in info['expressions']):
        print('already has Tear')
        return
    code = open('P:/FoA/Tools/Unreal/ui/hlsl/scrim_tear.hlsl').read()
    assert not any(ch in code for ch in "'\"`") and '//' not in code
    tear = c('material_add_node', material_path=M, expression_class='MaterialExpressionScalarParameter', node_pos=[-720, 360],
             properties={'ParameterName': 'Tear', 'DefaultValue': 0.0})['node_id']
    time = c('material_add_node', material_path=M, expression_class='MaterialExpressionTime', node_pos=[-720, 280])['node_id']
    cus = c('material_add_node', material_path=M, expression_class='MaterialExpressionCustom', node_pos=[-480, 280],
            properties={'Description': 'Scrim tear', 'OutputType': 'CMOT_Float1', 'Code': code,
                        'Inputs': [{'InputName': 'UV'}, {'InputName': 'T'}, {'InputName': 'Tear'}]})['node_id']
    mx = c('material_add_node', material_path=M, expression_class='MaterialExpressionMax', node_pos=[-200, 120])['node_id']
    c('material_connect_nodes', material_path=M, from_node='MaterialExpressionTextureCoordinate_0', to_node=cus, to_input='UV')
    c('material_connect_nodes', material_path=M, from_node=time, to_node=cus, to_input='T')
    c('material_connect_nodes', material_path=M, from_node=tear, to_node=cus, to_input='Tear')
    c('material_connect_nodes', material_path=M, from_node='MaterialExpressionLinearInterpolate_0', to_node=mx, to_input='A')
    c('material_connect_nodes', material_path=M, from_node=cus, to_node=mx, to_input='B')
    c('material_connect_nodes', material_path=M, from_node=mx, to_property='opacity')
    c('material_add_comment', material_path=M, text='Pause tear', node_pos=[-1200, 496], size=[580, 330])
    c('material_validate', material_path=M)
    c('material_compile', material_path=M)


def ramp(ref, x, y, src, start, span, exp='3.0'):
    """easeOut(clamp((src - start) / span))"""
    return [
        {'op': 'add_node', 'ref': ref + 's', 'node_type': 'call_function', 'function_name': f'{KML}:Subtract_DoubleDouble', 'x': x, 'y': y},
        {'op': 'set_pin', 'node_id': ref + 's', 'pin_name': 'B', 'value': str(start)},
        {'op': 'add_node', 'ref': ref + 'd', 'node_type': 'call_function', 'function_name': f'{KML}:Divide_DoubleDouble', 'x': x + 170, 'y': y},
        {'op': 'set_pin', 'node_id': ref + 'd', 'pin_name': 'B', 'value': str(span)},
        {'op': 'add_node', 'ref': ref + 'c', 'node_type': 'call_function', 'function_name': f'{KML}:FClamp', 'x': x + 340, 'y': y},
        {'op': 'set_pin', 'node_id': ref + 'c', 'pin_name': 'Min', 'value': '0.0'},
        {'op': 'set_pin', 'node_id': ref + 'c', 'pin_name': 'Max', 'value': '1.0'},
        {'op': 'add_node', 'ref': ref, 'node_type': 'call_function', 'function_name': f'{KML}:Ease', 'x': x + 510, 'y': y},
        {'op': 'set_pin', 'node_id': ref, 'pin_name': 'A', 'value': '0.0'},
        {'op': 'set_pin', 'node_id': ref, 'pin_name': 'B', 'value': '1.0'},
        {'op': 'set_pin', 'node_id': ref, 'pin_name': 'EasingFunc', 'value': 'EaseOut'},
        {'op': 'set_pin', 'node_id': ref, 'pin_name': 'BlendExp', 'value': exp},
        {'op': 'connect', 'from_node': src, 'from_pin': 'Output_Get', 'to_node': ref + 's', 'to_pin': 'A'},
        {'op': 'connect', 'from_node': ref + 's', 'from_pin': 'ReturnValue', 'to_node': ref + 'd', 'to_pin': 'A'},
        {'op': 'connect', 'from_node': ref + 'd', 'from_pin': 'ReturnValue', 'to_node': ref + 'c', 'to_pin': 'Value'},
        {'op': 'connect', 'from_node': ref + 'c', 'from_pin': 'ReturnValue', 'to_node': ref, 'to_pin': 'Alpha'},
    ], [ref + 's', ref + 'd', ref + 'c', ref]


def graph():
    for v in ('PauseT', 'LastTick'):
        c('blueprint_add_variable', path=P, variable_name=v, variable_type='real', default_value='0.0',
          category='Pause|Motion', update_existing=True)
    d = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': 'EventGraph'})['data']
    if any(n['title'].startswith('Event Tick') for n in d['nodes']):
        print('Tick already built')
        return
    X, ops, ids = 0, [], []
    ops += [
        {'op': 'add_event', 'ref': 'tick', 'event_name': 'Tick', 'x': X, 'y': 1600},
        {'op': 'add_node', 'ref': 'now', 'node_type': 'call_function', 'function_name': '/Script/Engine.GameplayStatics:GetRealTimeSeconds', 'x': 200, 'y': 1800},
        {'op': 'add_node', 'ref': 'last', 'node_type': 'variable_get', 'variable_name': 'LastTick', 'x': 200, 'y': 1880},
        {'op': 'add_node', 'ref': 'gap', 'node_type': 'call_function', 'function_name': f'{KML}:Subtract_DoubleDouble', 'x': 420, 'y': 1800},
        {'op': 'add_node', 'ref': 'fresh', 'node_type': 'call_function', 'function_name': f'{KML}:Greater_DoubleDouble', 'x': 620, 'y': 1800},
        {'op': 'set_pin', 'node_id': 'fresh', 'pin_name': 'B', 'value': '0.25'},
        {'op': 'add_node', 'ref': 'pt', 'node_type': 'variable_get', 'variable_name': 'PauseT', 'x': 420, 'y': 1960},
        {'op': 'add_node', 'ref': 'adv', 'node_type': 'call_function', 'function_name': f'{KML}:Add_DoubleDouble', 'x': 620, 'y': 1960},
        {'op': 'add_node', 'ref': 'sel', 'node_type': 'call_function', 'function_name': f'{KML}:SelectFloat', 'x': 820, 'y': 1880},
        {'op': 'set_pin', 'node_id': 'sel', 'pin_name': 'A', 'value': '0.0'},
        {'op': 'add_node', 'ref': 'setpt', 'node_type': 'variable_set', 'variable_name': 'PauseT', 'x': 1040, 'y': 1600},
        {'op': 'add_node', 'ref': 'setlast', 'node_type': 'variable_set', 'variable_name': 'LastTick', 'x': 1280, 'y': 1600},
        {'op': 'add_node', 'ref': 'live', 'node_type': 'call_function', 'function_name': f'{KML}:LessEqual_DoubleDouble', 'x': 1280, 'y': 1800},
        {'op': 'set_pin', 'node_id': 'live', 'pin_name': 'B', 'value': '0.8'},
        {'op': 'add_node', 'ref': 'br', 'node_type': 'branch', 'x': 1520, 'y': 1600},
        {'op': 'connect', 'from_node': 'now', 'from_pin': 'ReturnValue', 'to_node': 'gap', 'to_pin': 'A'},
        {'op': 'connect', 'from_node': 'last', 'from_pin': 'LastTick', 'to_node': 'gap', 'to_pin': 'B'},
        {'op': 'connect', 'from_node': 'gap', 'from_pin': 'ReturnValue', 'to_node': 'fresh', 'to_pin': 'A'},
        {'op': 'connect', 'from_node': 'pt', 'from_pin': 'PauseT', 'to_node': 'adv', 'to_pin': 'A'},
        {'op': 'connect', 'from_node': 'tick', 'from_pin': 'InDeltaTime', 'to_node': 'adv', 'to_pin': 'B'},
        {'op': 'connect', 'from_node': 'adv', 'from_pin': 'ReturnValue', 'to_node': 'sel', 'to_pin': 'B'},
        {'op': 'connect', 'from_node': 'fresh', 'from_pin': 'ReturnValue', 'to_node': 'sel', 'to_pin': 'bPickA'},
        {'op': 'connect', 'from_node': 'sel', 'from_pin': 'ReturnValue', 'to_node': 'setpt', 'to_pin': 'PauseT'},
        {'op': 'connect', 'from_node': 'tick', 'from_pin': 'then', 'to_node': 'setpt', 'to_pin': 'execute'},
        {'op': 'connect', 'from_node': 'now', 'from_pin': 'ReturnValue', 'to_node': 'setlast', 'to_pin': 'LastTick'},
        {'op': 'connect', 'from_node': 'setpt', 'from_pin': 'then', 'to_node': 'setlast', 'to_pin': 'execute'},
        {'op': 'connect', 'from_node': 'setpt', 'from_pin': 'Output_Get', 'to_node': 'live', 'to_pin': 'A'},
        {'op': 'connect', 'from_node': 'live', 'from_pin': 'ReturnValue', 'to_node': 'br', 'to_pin': 'Condition'},
        {'op': 'connect', 'from_node': 'setlast', 'from_pin': 'then', 'to_node': 'br', 'to_pin': 'execute'},
    ]
    clock = ['tick', 'now', 'last', 'gap', 'fresh', 'pt', 'adv', 'sel', 'setpt', 'setlast', 'live', 'br']
    # scrim tear settles: Tear = 1 - easeOut3(clamp(PauseT / 0.3))
    r, rid = ramp('tr', 1760, 1900, 'setpt', 0.0, 0.3)
    ops += r + [
        {'op': 'add_node', 'ref': 'inv', 'node_type': 'call_function', 'function_name': f'{KML}:Subtract_DoubleDouble', 'x': 2440, 'y': 1900},
        {'op': 'set_pin', 'node_id': 'inv', 'pin_name': 'A', 'value': '1.0'},
        {'op': 'connect', 'from_node': 'tr', 'from_pin': 'ReturnValue', 'to_node': 'inv', 'to_pin': 'B'},
        {'op': 'add_node', 'ref': 'img', 'node_type': 'variable_get', 'variable_name': 'Img_Scrim', 'x': 1760, 'y': 1760},
        {'op': 'add_node', 'ref': 'dyn', 'node_type': 'call_function', 'function_name': '/Script/UMG.Image:GetDynamicMaterial', 'x': 1760, 'y': 1600},
        {'op': 'connect', 'from_node': 'img', 'from_pin': 'Img_Scrim', 'to_node': 'dyn', 'to_pin': 'self'},
        {'op': 'connect', 'from_node': 'br', 'from_pin': 'then', 'to_node': 'dyn', 'to_pin': 'execute'},
        {'op': 'add_node', 'ref': 'ssp', 'node_type': 'call_function', 'function_name': '/Script/Engine.MaterialInstanceDynamic:SetScalarParameterValue', 'x': 2640, 'y': 1600},
        {'op': 'set_pin', 'node_id': 'ssp', 'pin_name': 'ParameterName', 'value': 'Tear'},
        {'op': 'connect', 'from_node': 'dyn', 'from_pin': 'ReturnValue', 'to_node': 'ssp', 'to_pin': 'self'},
        {'op': 'connect', 'from_node': 'inv', 'from_pin': 'ReturnValue', 'to_node': 'ssp', 'to_pin': 'Value'},
        {'op': 'connect', 'from_node': 'dyn', 'from_pin': 'then', 'to_node': 'ssp', 'to_pin': 'execute'},
    ]
    tear = rid + ['inv', 'img', 'dyn', 'ssp']
    # header and goal fade in from 0.1 s over 0.3 s
    r, hid = ramp('hd', 2900, 1900, 'setpt', 0.1, 0.3)
    ops += r
    prev, txt = 'ssp', hid
    for i, w in enumerate(('Txt_Header', 'Txt_Objective')):
        ops += [
            {'op': 'add_node', 'ref': f't{i}', 'node_type': 'variable_get', 'variable_name': w, 'x': 3600 + i * 260, 'y': 1760},
            {'op': 'add_node', 'ref': f'o{i}', 'node_type': 'call_function', 'function_name': '/Script/UMG.Widget:SetRenderOpacity', 'x': 3600 + i * 260, 'y': 1600},
            {'op': 'connect', 'from_node': f't{i}', 'from_pin': w, 'to_node': f'o{i}', 'to_pin': 'self'},
            {'op': 'connect', 'from_node': 'hd', 'from_pin': 'ReturnValue', 'to_node': f'o{i}', 'to_pin': 'InOpacity'},
            {'op': 'connect', 'from_node': prev, 'from_pin': 'then', 'to_node': f'o{i}', 'to_pin': 'execute'},
        ]
        prev = f'o{i}'
        txt += [f't{i}', f'o{i}']
    # the four words form from sand, 50 ms apart, 0.42 s each, from 0.12 s
    words = []
    for i, b in enumerate(BTNS):
        r, wid = ramp(f'w{i}', 4200 + i * 760, 1900, 'setpt', round(0.12 + 0.05 * i, 2), 0.42)
        ops += r + [
            {'op': 'add_node', 'ref': f'b{i}', 'node_type': 'variable_get', 'variable_name': b, 'x': 4200 + i * 760, 'y': 1760},
            {'op': 'add_node', 'ref': f'sr{i}', 'node_type': 'call_function', 'function_name': SB, 'x': 4200 + i * 760, 'y': 1600},
            {'op': 'connect', 'from_node': f'b{i}', 'from_pin': b, 'to_node': f'sr{i}', 'to_pin': 'self'},
            {'op': 'connect', 'from_node': f'w{i}', 'from_pin': 'ReturnValue', 'to_node': f'sr{i}', 'to_pin': 'Alpha'},
            {'op': 'connect', 'from_node': prev, 'from_pin': 'then', 'to_node': f'sr{i}', 'to_pin': 'execute'},
        ]
        prev = f'sr{i}'
        words += wid + [f'b{i}', f'sr{i}']
    ops += [
        {'op': 'comment', 'title': 'Pause clock', 'node_ids': clock, 'color': [0.10, 0.20, 0.35]},
        {'op': 'comment', 'title': 'Frame tears, then settles', 'node_ids': tear, 'color': [0.30, 0.22, 0.10]},
        {'op': 'comment', 'title': 'Header fades in', 'node_ids': txt, 'color': [0.30, 0.22, 0.10]},
        {'op': 'comment', 'title': 'Words form from sand', 'node_ids': words, 'color': [0.30, 0.22, 0.10]},
        {'op': 'fit_comments'},
    ]
    c('blueprint_graph_batch', path=P, graph_name='EventGraph', ops=ops, compile=True, save=True)


{'mat': mat, 'graph': graph}[sys.argv[1]]()
