"""AAA pass, day rollover (Hayba, in place): the new day number gathers from the sand that buried the day.
  tree   Ret_New (RetainerBox, MI_UI_SandText_Title: clean at rest, echo 0) takes Txt_New's place in VB_Card;
         then the MCP call printed here moves Txt_New into it (ui_reparent_element is MCP-only)
  graph  StepRollover: right after Txt_New's opacity beat, Reveal = easeOut4(the same RolloverRamp(0.45, 0.35)),
         guarded by IsValid (the card removes itself with a hard cut)
  python Tools/Unreal/ui/aaa_rollover.py tree|graph"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

P = '/Game/FoA/UI/Game/WBP_DayRollover'
KML = '/Script/Engine.KismetMathLibrary'


def c(cmd, **p):
    r = hc.call(cmd, p)
    d = r.get('data') or {}
    print(cmd, r.get('ok'), d.get('applied', d.get('succeeded', '')), d.get('error') or r.get('error') or '',
          json.dumps(d.get('compile') or '')[:200])
    return d


def tree():
    names = [w['name'] for w in hc.call('ui_query', {'path': P, 'flatten': True})['data']['matches']]
    snap = hc.call('ui_layout_snapshot', {'widget_blueprint_path': P, 'screen_width': 1920, 'screen_height': 1080,
                                          'widget_names': ['Txt_New', 'VB_Card']})['data']['widgets']
    print([(w['name'], w['x'], w['y'], w['width'], w['height'], (w.get('text_info') or {}).get('font_size'),
            (w.get('text_info') or {}).get('justification')) for w in snap])
    if 'Ret_New' not in names:
        c('ui_add_element', widget_blueprint_path=P, child_class='RetainerBox', parent_widget_name='VB_Card', name='Ret_New')
        c('ui_move_element', widget_blueprint_path=P, widget_name='Ret_New', new_index=1)
    c('ui_set_widget_properties', widget_blueprint_path=P, widget_name='Ret_New',
      properties={'EffectMaterial': '/Game/FoA/UI/Materials/MI_UI_SandText_Title.MI_UI_SandText_Title',
                  'TextureParameter': 'Texture', 'Visibility': 'HitTestInvisible'})
    print('NOW (MCP): ui_reparent_element', json.dumps({'widget_blueprint_path': P, 'widget_name': 'Txt_New',
                                                          'new_parent_name': 'Ret_New'}))


def graph():
    nodes, edges, off = [], [], 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': 'StepRollover', 'offset': off})['data']
        nodes += d['nodes']
        off = d['page']['nodes']['next_offset']
    off = 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': 'StepRollover', 'edge_offset': off})['data']
        edges += d['edges']
        off = d['page']['edges']['next_offset']
    t = {n['node_id']: n['title'].replace('\n', ' ') for n in nodes}
    if any(v.startswith('Get Ret_New') for v in t.values()):
        sys.exit('already applied')
    getnew = next(k for k, v in t.items() if v == 'Get Txt_New')
    op = next(e['to_node'] for e in edges if e['from_node'] == getnew and e['to_pin'] == 'self')
    ramp = next(e['from_node'] for e in edges if e['to_node'] == op and e['to_pin'] == 'InOpacity')
    nxt = [e for e in edges if e['from_node'] == op and e['from_pin'] == 'then']
    ops = [{'op': 'disconnect', 'node_id': op, 'pin_name': 'then', 'to_node': e['to_node'], 'to_pin': e['to_pin']} for e in nxt]
    ops += [
        {'op': 'add_node', 'ref': 'ret', 'node_type': 'variable_get', 'variable_name': 'Ret_New', 'x': 0, 'y': 1500},
        {'op': 'add_node', 'ref': 'gem', 'node_type': 'call_function', 'function_name': '/Script/UMG.RetainerBox:GetEffectMaterial', 'x': 180, 'y': 1500},
        {'op': 'connect', 'from_node': 'ret', 'from_pin': 'Ret_New', 'to_node': 'gem', 'to_pin': 'self'},
        {'op': 'add_node', 'ref': 'valid', 'node_type': 'call_function', 'function_name': '/Script/Engine.KismetSystemLibrary:IsValid', 'x': 380, 'y': 1500},
        {'op': 'connect', 'from_node': 'gem', 'from_pin': 'ReturnValue', 'to_node': 'valid', 'to_pin': 'Object'},
        {'op': 'add_node', 'ref': 'vb', 'node_type': 'branch', 'x': 380, 'y': 1360},
        {'op': 'connect', 'from_node': 'valid', 'from_pin': 'ReturnValue', 'to_node': 'vb', 'to_pin': 'Condition'},
        {'op': 'connect', 'from_node': op, 'from_pin': 'then', 'to_node': 'vb', 'to_pin': 'execute'},
        {'op': 'add_node', 'ref': 'ease', 'node_type': 'call_function', 'function_name': f'{KML}:Ease', 'x': 380, 'y': 1640},
        {'op': 'set_pin', 'node_id': 'ease', 'pin_name': 'A', 'value': '0.0'},
        {'op': 'set_pin', 'node_id': 'ease', 'pin_name': 'B', 'value': '1.0'},
        {'op': 'set_pin', 'node_id': 'ease', 'pin_name': 'EasingFunc', 'value': 'EaseOut'},
        {'op': 'set_pin', 'node_id': 'ease', 'pin_name': 'BlendExp', 'value': '4.0'},
        {'op': 'connect', 'from_node': ramp, 'from_pin': 'Alpha', 'to_node': 'ease', 'to_pin': 'Alpha'},
        {'op': 'add_node', 'ref': 'ssp', 'node_type': 'call_function', 'function_name': '/Script/Engine.MaterialInstanceDynamic:SetScalarParameterValue', 'x': 600, 'y': 1360},
        {'op': 'set_pin', 'node_id': 'ssp', 'pin_name': 'ParameterName', 'value': 'Reveal'},
        {'op': 'connect', 'from_node': 'gem', 'from_pin': 'ReturnValue', 'to_node': 'ssp', 'to_pin': 'self'},
        {'op': 'connect', 'from_node': 'ease', 'from_pin': 'ReturnValue', 'to_node': 'ssp', 'to_pin': 'Value'},
        {'op': 'connect', 'from_node': 'vb', 'from_pin': 'then', 'to_node': 'ssp', 'to_pin': 'execute'},
    ]
    for e in nxt:
        ops += [{'op': 'connect', 'from_node': 'ssp', 'from_pin': 'then', 'to_node': e['to_node'], 'to_pin': e['to_pin']},
                {'op': 'connect', 'from_node': 'vb', 'from_pin': 'else', 'to_node': e['to_node'], 'to_pin': e['to_pin']}]
    ops += [{'op': 'comment', 'title': 'Day number gathers from sand', 'node_ids': ['ret', 'gem', 'valid', 'vb', 'ease', 'ssp'],
             'color': [0.30, 0.22, 0.10]}, {'op': 'fit_comments'}]
    c('blueprint_graph_batch', path=P, graph_name='StepRollover', ops=ops, compile=True, save=True)


{'tree': tree, 'graph': graph}[sys.argv[1]]()
