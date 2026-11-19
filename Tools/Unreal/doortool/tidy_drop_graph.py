"""Door-tool lane: TickToolScrewDrop's three groups side by side (the tink and stop groups overlapped the fall group).
Moves only, refits the comment boxes, saves. Hold a lease on BP_Door first.
  $env:HAYBA_AGENT_ID='doortool'; python Tools/Unreal/doortool/tidy_drop_graph.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal']
from hayba_call import call  # noqa: E402

DOOR, G = '/Game/FoA/Gameplay/BP_Door', 'TickToolScrewDrop'
rects, offset = {}, 0
while offset is not None:
    d = call('blueprint_measure_nodes', dict(path=DOOR, graph_name=G, offset=offset, limit=50))['data']
    for n in d['nodes']:
        rects[n['node_id']] = (n['title'], n['rect'], n.get('comment'))
    offset = (d.get('page') or {}).get('next_offset')
tink = [k for k, (t, r, c) in rects.items() if not c and (3450 <= r[0] < 4440 or t.startswith('Play Sound'))
        and not t.startswith('Set Relative') and 'Drop Screw' not in t]
stop = [k for k, (t, r, c) in rects.items() if not c and r[0] >= 4440 and k not in tink]
fall_right = max(r[0] + r[2] for k, (t, r, c) in rects.items() if not c and k not in tink and k not in stop)
dx1 = fall_right + 200 - min(rects[k][1][0] for k in tink)
dx2 = max(rects[k][1][0] + rects[k][1][2] for k in tink) + dx1 + 200 - min(rects[k][1][0] for k in stop)
moves = [dict(node_id=k, x=rects[k][1][0] + dx1, y=rects[k][1][1]) for k in tink]
moves += [dict(node_id=k, x=rects[k][1][0] + dx2, y=rects[k][1][1]) for k in stop]
print('tink', [rects[k][0] for k in tink], 'stop', [rects[k][0] for k in stop], dx1, dx2)
r = call('blueprint_move_nodes', dict(path=DOOR, graph_name=G, moves=moves, fit_comments=True))
print('moved', r.get('ok'), (r.get('data') or {}).get('moved'), (r.get('data') or {}).get('fit_error'))
print('saved', call('asset_save', dict(asset_paths=[DOOR])).get('ok'))
