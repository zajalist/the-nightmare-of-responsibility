"""AAA pass, HUD (Hayba, in place). Steps, run in order:
  mat    MI_UI_SandText_HUD (instance of M_UI_SandText) and neutral Ink on every sand-text instance (monochrome rule)
  tree   Ret_Objective (RetainerBox, the sand material) around Txt_Objective; neutral text colours; subtitle halo
  graph  ObjectiveStep: the objective forms from sand over 0.8 s, then quiets to half brightness after 6 s;
         SubStep: each subtitle line rises 6 px and fades in over 0.26 s
Reparenting is MCP-only (ui_reparent_element), so 'tree' prints the MCP call to make between its two halves.
  python Tools/Unreal/ui/aaa_hud.py mat|tree|tree2|graph"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

HUD = '/Game/FoA/UI/Game/WBP_HUD'
MAT = '/Game/FoA/UI/Materials'
KML = '/Script/Engine.KismetMathLibrary'
KSL = '/Script/Engine.KismetSystemLibrary'
INK = [0.9, 0.9, 0.9, 1.0]          # neutral paper: UMG draws after the mono post-process, so warm ink would show
OBJ = [0.87, 0.87, 0.87, 1.0]       # #F0F0F0 in linear
REST = [0.26, 0.26, 0.26, 1.0]      # #8C8C8C in linear: the hint row at rest


def c(cmd, **p):
    r = hc.call(cmd, p)
    d = r.get('data') or {}
    print(cmd, p.get('widget_name') or p.get('param_name') or p.get('graph_name') or '', r.get('ok'),
          d.get('succeeded', d.get('applied')), d.get('failed_properties') or d.get('error') or r.get('error') or '',
          json.dumps(d.get('compile'))[:160] if d.get('compile') else '')
    return d


def mat():
    if not (hc.call('material_get_info', {'path': f'{MAT}/MI_UI_SandText_HUD'}).get('ok')):
        c('material_create_instance', parent_material_path=f'{MAT}/M_UI_SandText', package_path=MAT, name='MI_UI_SandText_HUD')
    for k, v in (('Scale', 2.5), ('Calm', [0.12, 0.12, 0.3, 0.3]), ('Reveal', 1.0), ('Ink', INK)):
        c('material_set_param', instance_path=f'{MAT}/MI_UI_SandText_HUD', param_name=k, value=v)
    for mi in ('MI_UI_SandText_Menu', 'MI_UI_SandText_Title'):
        c('material_set_param', instance_path=f'{MAT}/{mi}', param_name='Ink', value=INK)


def tree():
    names = [w['name'] for w in hc.call('ui_query', {'path': HUD, 'flatten': True})['data']['matches']]
    if 'Ret_Objective' not in names:
        c('ui_add_element', widget_blueprint_path=HUD, child_class='RetainerBox', parent_widget_name='Ovl_Frame',
          name='Ret_Objective', slot_props={'horizontal_alignment': 'Left', 'vertical_alignment': 'Top',
                                            'padding': [24, 22, 0, 0]})
    if 'Ovl_Objective' not in names:
        c('ui_add_element', widget_blueprint_path=HUD, child_class='Overlay', parent_widget_name='Ret_Objective',
          name='Ovl_Objective')
    print('NOW (MCP): ui_reparent_element', json.dumps({
        'widget_blueprint_path': HUD, 'widget_name': 'Txt_Objective', 'new_parent_name': 'Ovl_Objective',
        'slot_props': {'padding': '(Left=24,Top=16,Right=32,Bottom=28)', 'horizontal_alignment': 'HAlign_Left',
                       'vertical_alignment': 'VAlign_Top'}}))


def tree2():
    c('ui_set_widget_properties', widget_blueprint_path=HUD, widget_name='Ret_Objective',
      properties={'EffectMaterial': f'{MAT}/MI_UI_SandText_HUD.MI_UI_SandText_HUD', 'TextureParameter': 'Texture',
                  'Visibility': 'HitTestInvisible'})
    # Txt_Objective sits in Ovl_Objective (a RetainerBox child has no padding), padded (24,16,32,28) by the MCP
    # reparent: room for grains blown in from the left and the echo trailing down
    c('ui_set_text_style', widget_blueprint_path=HUD, widget_name='Txt_Objective', typeface='SemiBold', size=28, color=OBJ)
    c('ui_set_text_style', widget_blueprint_path=HUD, widget_name='Txt_PhoneHint', color=[0.45, 0.45, 0.45, 1.0])
    c('ui_set_text_style', widget_blueprint_path=HUD, widget_name='Txt_Narration', color=OBJ)
    # subtitles over a soft halo instead of a box (Silent Hill 2 and TLOU2 style): the soft dot stretched under the line
    c('ui_set_widget_properties', widget_blueprint_path=HUD, widget_name='Brd_Narration',
      properties={'Background': {'ResourceObject': '/Game/FoA/UI/Textures/T_UI_SoftDot.T_UI_SoftDot', 'DrawAs': 'Image',
                                 'TintColor': {'SpecifiedColor': [0, 0, 0, 1]}},
                  'BrushColor': [0.0, 0.0, 0.0, 0.62], 'Padding': [72, 22, 72, 22]})
    c('ui_compile_widget', widget_blueprint_path=HUD)
    c('ui_save_widget', widget_blueprint_path=HUD)


def nodes_of(graph):
    out, off = [], 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': HUD, 'graph_name': graph, 'offset': off})['data']
        out += d['nodes']
        off = d['page']['nodes']['next_offset']
    return out


def edges_of(graph):
    out, off = [], 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': HUD, 'graph_name': graph, 'edge_offset': off})['data']
        out += d['edges']
        off = d['page']['edges']['next_offset']
    return out


def stepper(fn, var, ops_body, nodes_body):
    """fn(): var += 1/60 (60 Hz timer that catches up), then the body; fn's own timer stops once Done is true."""
    c('blueprint_add_variable', path=HUD, variable_name=var, variable_type='real', default_value='0.0',
      category='HUD|Motion', update_existing=True)
    if fn not in hc.call('blueprint_get_info', {'path': HUD})['data']['functions']:
        c('blueprint_add_function', path=HUD, function_name=fn)
    entry = next(n['node_id'] for n in nodes_of(fn) if n['title'] == fn)
    if len(nodes_of(fn)) > 1:
        print(fn, 'already built')
        return
    ops = [
        {'op': 'add_node', 'ref': 'get', 'node_type': 'variable_get', 'variable_name': var, 'x': 160, 'y': 200},
        {'op': 'add_node', 'ref': 'add', 'node_type': 'call_function', 'function_name': f'{KML}:Add_DoubleDouble', 'x': 352, 'y': 200},
        {'op': 'set_pin', 'node_id': 'add', 'pin_name': 'B', 'value': '0.0167'},
        {'op': 'add_node', 'ref': 'set', 'node_type': 'variable_set', 'variable_name': var, 'x': 560, 'y': 0},
        {'op': 'connect', 'from_node': 'get', 'from_pin': var, 'to_node': 'add', 'to_pin': 'A'},
        {'op': 'connect', 'from_node': 'add', 'from_pin': 'ReturnValue', 'to_node': 'set', 'to_pin': var},
        {'op': 'connect', 'from_node': entry, 'from_pin': 'then', 'to_node': 'set', 'to_pin': 'execute'},
    ] + ops_body + [
        {'op': 'add_node', 'ref': 'stop', 'node_type': 'call_function', 'function_name': f'{KSL}:K2_ClearTimer', 'x': 2600, 'y': 0},
        {'op': 'set_pin', 'node_id': 'stop', 'pin_name': 'FunctionName', 'value': fn},
        {'op': 'connect', 'from_node': 'br', 'from_pin': 'then', 'to_node': 'stop', 'to_pin': 'execute'},
        {'op': 'comment', 'title': fn.replace('Step', ' motion'), 'node_ids': [entry, 'get', 'add', 'set', 'stop'] + nodes_body,
         'color': [0.30, 0.22, 0.10]},
        {'op': 'fit_comments'},
    ]
    c('blueprint_graph_batch', path=HUD, graph_name=fn, ops=ops)


def ease(ref, x, y, func, exp, alpha_from):
    return [
        {'op': 'add_node', 'ref': ref, 'node_type': 'call_function', 'function_name': f'{KML}:Ease', 'x': x, 'y': y},
        {'op': 'set_pin', 'node_id': ref, 'pin_name': 'A', 'value': '0.0'},
        {'op': 'set_pin', 'node_id': ref, 'pin_name': 'B', 'value': '1.0'},
        {'op': 'set_pin', 'node_id': ref, 'pin_name': 'EasingFunc', 'value': func},
        {'op': 'set_pin', 'node_id': ref, 'pin_name': 'BlendExp', 'value': exp},
        {'op': 'connect', 'from_node': alpha_from, 'from_pin': 'ReturnValue', 'to_node': ref, 'to_pin': 'Alpha'},
    ]


def ramp(ref, x, y, src, src_pin, start, span):
    """clamp((src - start) / span, 0, 1)"""
    return [
        {'op': 'add_node', 'ref': ref + 's', 'node_type': 'call_function', 'function_name': f'{KML}:Subtract_DoubleDouble', 'x': x, 'y': y},
        {'op': 'set_pin', 'node_id': ref + 's', 'pin_name': 'B', 'value': str(start)},
        {'op': 'add_node', 'ref': ref + 'd', 'node_type': 'call_function', 'function_name': f'{KML}:Divide_DoubleDouble', 'x': x + 180, 'y': y},
        {'op': 'set_pin', 'node_id': ref + 'd', 'pin_name': 'B', 'value': str(span)},
        {'op': 'add_node', 'ref': ref, 'node_type': 'call_function', 'function_name': f'{KML}:FClamp', 'x': x + 360, 'y': y},
        {'op': 'set_pin', 'node_id': ref, 'pin_name': 'Min', 'value': '0.0'},
        {'op': 'set_pin', 'node_id': ref, 'pin_name': 'Max', 'value': '1.0'},
        {'op': 'connect', 'from_node': src, 'from_pin': src_pin, 'to_node': ref + 's', 'to_pin': 'A'},
        {'op': 'connect', 'from_node': ref + 's', 'from_pin': 'ReturnValue', 'to_node': ref + 'd', 'to_pin': 'A'},
        {'op': 'connect', 'from_node': ref + 'd', 'from_pin': 'ReturnValue', 'to_node': ref, 'to_pin': 'Value'},
    ]


def done(x, src, at):
    return [
        {'op': 'add_node', 'ref': 'ge', 'node_type': 'call_function', 'function_name': f'{KML}:GreaterEqual_DoubleDouble', 'x': x, 'y': 200},
        {'op': 'set_pin', 'node_id': 'ge', 'pin_name': 'B', 'value': str(at)},
        {'op': 'connect', 'from_node': 'set', 'from_pin': 'Output_Get', 'to_node': 'ge', 'to_pin': 'A'},
        {'op': 'add_node', 'ref': 'br', 'node_type': 'branch', 'x': x + 160, 'y': 0},
        {'op': 'connect', 'from_node': 'ge', 'from_pin': 'ReturnValue', 'to_node': 'br', 'to_pin': 'Condition'},
        {'op': 'connect', 'from_node': src, 'from_pin': 'then', 'to_node': 'br', 'to_pin': 'execute'},
    ]


def arm(graph, after_title, fn, var):
    """In `graph`, right after the node titled after_title: var = 0, then start fn's 60 Hz timer."""
    nodes, edges = nodes_of(graph), edges_of(graph)
    if any(n['title'].startswith('Set Timer') and any(p.get('default_value') == fn for p in n['pins']) for n in nodes):
        print(graph, 'already arms', fn)
        return
    src = next(n['node_id'] for n in nodes if n['title'].replace('\n', ' ').startswith(after_title))
    nxt = [e for e in edges if e['from_node'] == src and e['from_pin'] == 'then']
    ops = [{'op': 'add_node', 'ref': 'zero', 'node_type': 'variable_set', 'variable_name': var, 'x': 0, 'y': -260},
           {'op': 'set_pin', 'node_id': 'zero', 'pin_name': var, 'value': '0.0'},
           {'op': 'add_node', 'ref': 'tmr', 'node_type': 'call_function', 'function_name': f'{KSL}:K2_SetTimer', 'x': 240, 'y': -260},
           {'op': 'set_pin', 'node_id': 'tmr', 'pin_name': 'FunctionName', 'value': fn},
           {'op': 'set_pin', 'node_id': 'tmr', 'pin_name': 'Time', 'value': '0.0167'},
           {'op': 'set_pin', 'node_id': 'tmr', 'pin_name': 'bLooping', 'value': 'true'}]
    for e in nxt:
        ops.append({'op': 'disconnect', 'node_id': src, 'pin_name': 'then', 'to_node': e['to_node'], 'to_pin': e['to_pin']})
    ops += [{'op': 'connect', 'from_node': src, 'from_pin': 'then', 'to_node': 'zero', 'to_pin': 'execute'},
            {'op': 'connect', 'from_node': 'zero', 'from_pin': 'then', 'to_node': 'tmr', 'to_pin': 'execute'}]
    for e in nxt:
        ops.append({'op': 'connect', 'from_node': 'tmr', 'from_pin': 'then', 'to_node': e['to_node'], 'to_pin': e['to_pin']})
    ops.append({'op': 'comment', 'title': 'Start ' + fn.replace('Step', ' motion').lower(), 'node_ids': ['zero', 'tmr'],
                'color': [0.30, 0.22, 0.10]})
    c('blueprint_graph_batch', path=HUD, graph_name=graph, ops=ops)


def graph():
    # Objective: Reveal = easeOut4(clamp(t / 0.8)); opacity = 1 - 0.5 * easeInOut2(clamp((t - 6) / 0.9)); stop at 6.9 s
    body = (ramp('rv', 760, 200, 'set', 'Output_Get', 0.0, 0.8) + ease('rve', 1300, 200, 'EaseOut', '4.0', 'rv') + [
        {'op': 'add_node', 'ref': 'ret', 'node_type': 'variable_get', 'variable_name': 'Ret_Objective', 'x': 1300, 'y': 380},
        {'op': 'add_node', 'ref': 'gem', 'node_type': 'call_function', 'function_name': '/Script/UMG.RetainerBox:GetEffectMaterial', 'x': 1300, 'y': 460},
        {'op': 'connect', 'from_node': 'ret', 'from_pin': 'Ret_Objective', 'to_node': 'gem', 'to_pin': 'self'},
        {'op': 'add_node', 'ref': 'ssp', 'node_type': 'call_function', 'function_name': '/Script/Engine.MaterialInstanceDynamic:SetScalarParameterValue', 'x': 1560, 'y': 0},
        {'op': 'set_pin', 'node_id': 'ssp', 'pin_name': 'ParameterName', 'value': 'Reveal'},
        {'op': 'connect', 'from_node': 'gem', 'from_pin': 'ReturnValue', 'to_node': 'ssp', 'to_pin': 'self'},
        {'op': 'connect', 'from_node': 'rve', 'from_pin': 'ReturnValue', 'to_node': 'ssp', 'to_pin': 'Value'},
        {'op': 'connect', 'from_node': 'set', 'from_pin': 'then', 'to_node': 'ssp', 'to_pin': 'execute'},
    ] + ramp('qt', 760, 560, 'set', 'Output_Get', 6.0, 0.9) + ease('qte', 1300, 600, 'EaseInOut', '2.0', 'qt') + [
        {'op': 'add_node', 'ref': 'half', 'node_type': 'call_function', 'function_name': f'{KML}:Lerp', 'x': 1560, 'y': 600},
        {'op': 'set_pin', 'node_id': 'half', 'pin_name': 'A', 'value': '1.0'},
        {'op': 'set_pin', 'node_id': 'half', 'pin_name': 'B', 'value': '0.5'},
        {'op': 'connect', 'from_node': 'qte', 'from_pin': 'ReturnValue', 'to_node': 'half', 'to_pin': 'Alpha'},
        {'op': 'add_node', 'ref': 'txt', 'node_type': 'variable_get', 'variable_name': 'Txt_Objective', 'x': 1800, 'y': 380},
        {'op': 'add_node', 'ref': 'op', 'node_type': 'call_function', 'function_name': '/Script/UMG.Widget:SetRenderOpacity', 'x': 1960, 'y': 0},
        {'op': 'connect', 'from_node': 'txt', 'from_pin': 'Txt_Objective', 'to_node': 'op', 'to_pin': 'self'},
        {'op': 'connect', 'from_node': 'half', 'from_pin': 'ReturnValue', 'to_node': 'op', 'to_pin': 'InOpacity'},
        {'op': 'connect', 'from_node': 'ssp', 'from_pin': 'then', 'to_node': 'op', 'to_pin': 'execute'},
    ] + done(2200, 'op', 6.9))
    stepper('ObjectiveStep', 'ObjT', body, ['rvs', 'rvd', 'rv', 'rve', 'ret', 'gem', 'ssp', 'qts', 'qtd', 'qt', 'qte', 'half',
                                             'txt', 'op', 'ge', 'br'])
    # Subtitle line: a = easeOut3(clamp(t / 0.26)); opacity a, rises from 6 px below; stop at 0.26 s
    body = (ramp('a', 760, 200, 'set', 'Output_Get', 0.0, 0.26) + ease('ae', 1300, 200, 'EaseOut', '3.0', 'a') + [
        {'op': 'add_node', 'ref': 'brd', 'node_type': 'variable_get', 'variable_name': 'Brd_Narration', 'x': 1560, 'y': 380},
        {'op': 'add_node', 'ref': 'op', 'node_type': 'call_function', 'function_name': '/Script/UMG.Widget:SetRenderOpacity', 'x': 1560, 'y': 0},
        {'op': 'connect', 'from_node': 'brd', 'from_pin': 'Brd_Narration', 'to_node': 'op', 'to_pin': 'self'},
        {'op': 'connect', 'from_node': 'ae', 'from_pin': 'ReturnValue', 'to_node': 'op', 'to_pin': 'InOpacity'},
        {'op': 'connect', 'from_node': 'set', 'from_pin': 'then', 'to_node': 'op', 'to_pin': 'execute'},
        {'op': 'add_node', 'ref': 'rise', 'node_type': 'call_function', 'function_name': f'{KML}:Lerp', 'x': 1560, 'y': 520},
        {'op': 'set_pin', 'node_id': 'rise', 'pin_name': 'A', 'value': '6.0'},
        {'op': 'set_pin', 'node_id': 'rise', 'pin_name': 'B', 'value': '0.0'},
        {'op': 'connect', 'from_node': 'ae', 'from_pin': 'ReturnValue', 'to_node': 'rise', 'to_pin': 'Alpha'},
        {'op': 'add_node', 'ref': 'v2', 'node_type': 'call_function', 'function_name': f'{KML}:MakeVector2D', 'x': 1800, 'y': 520},
        {'op': 'connect', 'from_node': 'rise', 'from_pin': 'ReturnValue', 'to_node': 'v2', 'to_pin': 'Y'},
        {'op': 'add_node', 'ref': 'tr', 'node_type': 'call_function', 'function_name': '/Script/UMG.Widget:SetRenderTranslation', 'x': 1960, 'y': 0},
        {'op': 'connect', 'from_node': 'brd', 'from_pin': 'Brd_Narration', 'to_node': 'tr', 'to_pin': 'self'},
        {'op': 'connect', 'from_node': 'v2', 'from_pin': 'ReturnValue', 'to_node': 'tr', 'to_pin': 'Translation'},
        {'op': 'connect', 'from_node': 'op', 'from_pin': 'then', 'to_node': 'tr', 'to_pin': 'execute'},
    ] + done(2200, 'tr', 0.26))
    stepper('SubStep', 'SubT', body, ['as', 'ad', 'a', 'ae', 'brd', 'op', 'rise', 'v2', 'tr', 'ge', 'br'])
    arm('HandleBeatChanged', 'SetText', 'ObjectiveStep', 'ObjT')
    arm('HandleNarration', 'SetVisibility', 'SubStep', 'SubT')
    c('ui_compile_widget', widget_blueprint_path=HUD)
    c('ui_save_widget', widget_blueprint_path=HUD)


{'mat': mat, 'tree': tree, 'tree2': tree2, 'graph': graph}[sys.argv[1]]()
