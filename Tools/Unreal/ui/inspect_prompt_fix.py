"""level1 lane review, 2026-11-18 (via the coordinator). In place, idempotent, compile and save inside one lease:
  python Tools/Unreal/ui/inspect_prompt_fix.py inspect   BP_ItemInspect: the inspected object read as a flat white blob
      (A1 run_20261118_0007 f04182: 1.1% of the key region at 250+/255). The item is on lighting channel 1 only, so its
      two rect lights are all its light: KeyLight 6 -> 1.5 cd, RimLight 10 -> 1.5 cd; the inspect post-process takes
      exposure -0.7 -> -1.6, bloom to 0.2 and f/1.4 -> f/2.8 so the whole key is sharp and keeps its form.
  python Tools/Unreal/ui/inspect_prompt_fix.py prompt    WBP_HUD.HandleFocusChanged: with Look selected the E line said
      "E  Inspect" for everything. It now says the target's own Look prompt ("E  Look at the boot", from the
      DT_Interactions Look row via BP_Interactable.Resolve), and the Q line offers the same words; "Inspect" stays
      the fallback when a target has no Look row.
  python Tools/Unreal/ui/inspect_prompt_fix.py primary   With Look selected the interactor's Prompt is the Look prompt,
      so the Q line read "Q  Look at the bed" twice over (A1 run_20261118_0159 f02220). The Q line now names the
      primary action (the target's Use row, else its Take row, else Prompt): "Q  Get back into bed"."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, graph, ok, save  # noqa: E402

INSPECT = '/Game/FoA/UI/Game/BP_ItemInspect'
HUD = '/Game/FoA/UI/Game/WBP_HUD'
INTERACTABLE = '/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'
ROW = '/Game/FoA/Gameplay/S_Interaction.S_Interaction'
KML, KTL, KSTR = '/Script/Engine.KismetMathLibrary', '/Script/Engine.KismetTextLibrary', '/Script/Engine.KismetStringLibrary'
STEP = sys.argv[1] if len(sys.argv) > 1 else ''


def step_inspect():
    bpc = INSPECT + '.BP_ItemInspect_C'
    for comp, props in (('KeyLight', {'Intensity': 1.5}), ('RimLight', {'Intensity': 1.5}),
                        ('PP', {'Settings': '(bOverride_AutoExposureBias=True,AutoExposureBias=-1.6,bOverride_BloomIntensity=True,'
                                            'BloomIntensity=0.2,bOverride_VignetteIntensity=True,VignetteIntensity=0.6,'
                                            'bOverride_DepthOfFieldFocalDistance=True,DepthOfFieldFocalDistance=35.0,'
                                            'bOverride_DepthOfFieldFstop=True,DepthOfFieldFstop=2.8)'})):
        r = hc.call('object_set_property', {'path': f'{bpc}:{comp}_GEN_VARIABLE', 'properties': props})
        print(comp, (r.get('data') or {}).get('applied'), r.get('error') or '')
        assert r.get('ok'), r
    compile_bp(INSPECT)
    print('inspect', save(INSPECT))


def step_prompt():
    if 'LookPrompt' not in {v['name'] for v in hc.call('blueprint_get_info', {'path': HUD})['data'].get('variables', [])}:
        ok(hc.call('blueprint_add_variable', {'path': HUD, 'variable_name': 'LookPrompt', 'variable_type': 'text',
                                               'default_value': '', 'category': 'HUD|Prompt'}), 'var')
        compile_bp(HUD, widget=True)
    nodes, edges = graph(HUD, 'HandleFocusChanged')
    if any(n['title'].startswith('Set LookPrompt') for n in nodes):
        print('already done')
        return
    by = {n['node_id']: n for n in nodes}
    e = next(n['node_id'] for n in nodes if n['title'] == 'HandleFocusChanged')
    first = next(x for x in edges if x['from_node'] == e and x['from_pin'] == 'then')
    e_inspect = next(n['node_id'] for n in nodes if n['title'] == 'SelectString'
                     and any(p['name'] == 'A' and p.get('default_value') == 'E  Inspect' for p in n['pins']))
    q_inspect = next(n['node_id'] for n in nodes if n['title'] == 'SelectString'
                     and any(p['name'] == 'B' and p.get('default_value') == '\nQ  Inspect' for p in n['pins']))
    # the break node's pins carry the user struct's GUID suffixes: add it alone first and read them
    brk = hc.call('blueprint_add_node', {'path': HUD, 'graph_name': 'HandleFocusChanged', 'node_type': 'break_struct',
                                         'struct_path': ROW, 'x': 600, 'y': 1900})['data']
    pin = lambda name: next(p['name'] for p in brk['pins'] if p['name'].split('_')[0] == name)  # noqa: E731
    cst = hc.call('blueprint_add_node', {'path': HUD, 'graph_name': 'HandleFocusChanged', 'node_type': 'cast',
                                         'class_path': INTERACTABLE, 'x': 300, 'y': 1700})['data']
    as_pin = next(p['name'] for p in cst['pins'] if p['direction'] == 'output' and p['name'].startswith('As'))
    b = B(HUD, 'HandleFocusChanged')
    b.refs.update({brk['node_id'], cst['node_id']})
    cast = cst['node_id']
    b.link(e, 'Target', cast, 'Object')
    res = b.fn(f'{INTERACTABLE}:Resolve', self=(cast, as_pin), Verb='Look', Held='None')
    b.link(res, 'Row', brk['node_id'], [p['name'] for p in brk['pins'] if p['direction'] == 'input'][0])
    found = b.set('LookPrompt', (brk['node_id'], pin('Prompt')))
    none = b.set('LookPrompt', '')
    b.ops.append(dict(op='disconnect', node_id=e, pin_name='then'))
    b.chain(e, cast, found, first['to_node'])
    b.chain((cast, 'CastFailed'), none, first['to_node'])
    look = b.fn(f'{KTL}:Conv_TextToString', InText=b.get('LookPrompt'))
    empty = b.fn(f'{KTL}:TextIsEmpty', InText=b.get('LookPrompt'))
    e_line = b.fn(f'{KML}:SelectString', A='E  Inspect', B=b.fn(f'{KSTR}:Concat_StrStr', A='E  ', B=look), bPickA=empty)
    q_line = b.fn(f'{KML}:SelectString', A='\nQ  Inspect', B=b.fn(f'{KSTR}:Concat_StrStr', A='\nQ  ', B=look), bPickA=empty)
    b.link(e_line, 'ReturnValue', e_inspect, 'A')
    b.link(q_line, 'ReturnValue', q_inspect, 'B')
    b.run()
    compile_bp(HUD, widget=True)
    print('prompt', save(HUD))


def step_primary():
    if 'PrimaryPrompt' not in {v['name'] for v in hc.call('blueprint_get_info', {'path': HUD})['data'].get('variables', [])}:
        ok(hc.call('blueprint_add_variable', {'path': HUD, 'variable_name': 'PrimaryPrompt', 'variable_type': 'string',
                                               'default_value': '', 'category': 'HUD|Prompt'}), 'var')
        compile_bp(HUD, widget=True)
    nodes, edges = graph(HUD, 'HandleFocusChanged')
    if any(n['title'].startswith('Set PrimaryPrompt') for n in nodes):
        print('already done')
        return
    e = next(n['node_id'] for n in nodes if n['title'] == 'HandleFocusChanged')
    cast = next(n for n in nodes if n['title'].startswith('Cast To BP_Interactable'))
    as_pin = next(p['name'] for p in cast['pins'] if p['direction'] == 'output' and p['name'].startswith('As'))
    sets = {x['from_pin']: x['to_node'] for x in edges if x['from_node'] == cast['node_id'] and x['from_pin'] in ('then', 'CastFailed')}
    branch = next(x['to_node'] for x in edges if x['from_node'] == sets['then'] and x['from_pin'] == 'then')
    own_str = {x['to_node'] for x in edges if x['from_node'] == e and x['from_pin'] == 'Prompt'}  # ToString(Prompt)
    q_append = next(n['node_id'] for n in nodes if n['title'] == 'Append'
                    and any(p['name'] == 'A' and p.get('default_value') == '\nQ  ' for p in n['pins'])
                    and any(x['to_node'] == n['node_id'] and x['to_pin'] == 'B' and x['from_node'] in own_str for x in edges))
    breaks = [hc.call('blueprint_add_node', {'path': HUD, 'graph_name': 'HandleFocusChanged', 'node_type': 'break_struct',
                                             'struct_path': ROW, 'x': 600, 'y': 2100 + 200 * i})['data'] for i in range(2)]
    pin = lambda brk, name: next(p['name'] for p in brk['pins'] if p['name'].split('_')[0] == name)  # noqa: E731
    b = B(HUD, 'HandleFocusChanged')
    b.refs.update({x['node_id'] for x in breaks} | {cast['node_id'], e, sets['then'], sets['CastFailed'], branch, q_append})
    prompts, found = [], []
    for brk, verb in zip(breaks, ('Use', 'Take')):
        res = b.fn(f'{INTERACTABLE}:Resolve', self=(cast['node_id'], as_pin), Verb=verb, Held='None')
        b.link(res, 'Row', brk['node_id'], [p['name'] for p in brk['pins'] if p['direction'] == 'input'][0])
        prompts.append(b.fn(f'{KTL}:Conv_TextToString', InText=(brk['node_id'], pin(brk, 'Prompt'))))
        found.append((res, 'bFound'))
    own = b.fn(f'{KTL}:Conv_TextToString', InText=(e, 'Prompt'))
    primary = b.fn(f'{KML}:SelectString', A=prompts[0], B=b.fn(f'{KML}:SelectString', A=prompts[1], B=own, bPickA=found[1]),
                   bPickA=found[0])
    hit = b.set('PrimaryPrompt', primary)
    miss = b.set('PrimaryPrompt', b.fn(f'{KTL}:Conv_TextToString', InText=(e, 'Prompt')))
    for src in (sets['then'], sets['CastFailed']):
        b.ops.append(dict(op='disconnect', node_id=src, pin_name='then'))
    b.chain(sets['then'], hit, branch)
    b.chain(sets['CastFailed'], miss, branch)
    b.ops.append(dict(op='disconnect', node_id=q_append, pin_name='B'))
    b.link(b.get('PrimaryPrompt')[0], 'PrimaryPrompt', q_append, 'B')
    b.run()
    compile_bp(HUD, widget=True)
    print('primary', save(HUD))


if __name__ == '__main__':
    target = {'inspect': INSPECT, 'prompt': HUD, 'primary': HUD}[STEP]
    token = editor_lock.acquire('ui', wait_s=900, ttl=180, areas=[target])
    try:
        assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
        {'inspect': step_inspect, 'prompt': step_prompt, 'primary': step_primary}[STEP]()
    finally:
        if token:
            hc.release('ui', token)
            editor_lock.forget('ui', token)
