"""Battle cards glitched in scale (the user's playtest, 11-19): TornStep sets each card's RenderScale every frame (hover
lift, flight shrink) and PulseCards overwrote the same widget at 30 Hz. PulseCards now scales the card's inner
TornSize_Act<i>, so the pulse multiplies the hover scale instead of fighting it. Idempotent, one lease, compiled and saved.
  python -B Tools/Unreal/encounter/patch_pulse_scale.py"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
os.environ.update(FOA_AGENT='main', HAYBA_AGENT_ID='main')
import editor_lock  # noqa: E402
from hayba_call import call  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

W = '/Game/FoA/Gameplay/Encounter/WBP_Encounter'
token = editor_lock.acquire('main', wait_s=600, ttl=180, areas=[W])
os.environ['FOA_LEASE'] = token or editor_lock.hayba_leases('main')[0][0]
try:
    assert not call('editor_get_state')['data']['pie_running'], 'PIE is running'
    for i in (0, 1):
        print('var', call('ui_set_variable', dict(widget_blueprint_path=W, widget_name=f'TornSize_Act{i}', is_variable=True)).get('ok'))
    nodes, edges = inspect(W, 'PulseCards')
    title = {n['node_id']: n['title'] for n in nodes}
    sets = [e for e in edges if title[e['to_node']] == 'SetRenderScale' and e['to_pin'] == 'self']
    if all(title[e['from_node']].startswith('Get TornSize') for e in sets):
        print('kept')
    else:
        b = Batch(W, 'PulseCards')
        gone = []
        for e in sets:
            child = next(n for n in nodes if n['node_id'] == e['from_node'])
            index = next((p.get('default_value') for p in child.get('pins', []) if p['name'] == 'Index'), '0') or '0'
            ref = 'size' + index
            src = next(x for x in edges if x['to_node'] == child['node_id'] and x['to_pin'] == 'self')
            b.get(ref, f'TornSize_Act{index}', 0, 0)
            b.link(ref, f'TornSize_Act{index}', e['to_node'], 'self')
            gone += [child['node_id'], src['from_node']]
        b.ops.append(dict(op='remove', node_ids=gone))
        b.run()
    print('dirty', call('editor_get_state')['data']['dirty_packages'])
finally:
    editor_lock.release('main')
