"""Find Blueprint pins whose default contains a substring, across every graph (read-only, Hayba).
  python Tools/Unreal/ui/bp_find_pin.py /Game/Path/BP "substring" """
import json, subprocess, sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

bp, needle = sys.argv[1], sys.argv[2]
info = hc.call('blueprint_get_info', {'path': bp}).get('data') or {}
graphs = [g if isinstance(g, str) else g.get('name') for g in
          (info.get('graphs') or []) + (info.get('functions') or []) + (info.get('event_graphs') or [])]
graphs = sorted({g for g in graphs if g} | {'EventGraph'})
for g in graphs:
    off = 0
    while off is not None:
        d = hc.call('blueprint_inspect_graph', {'path': bp, 'graph_name': g, 'offset': off}).get('data') or {}
        for n in d.get('nodes', []):
            for p in n.get('pins', []):
                v = str(p.get('default_value', p.get('default', '')) or '')
                if needle in v:
                    print(g, n['node_id'], n['title'].replace('\n', ' '), p['name'], repr(v))
        off = ((d.get('page') or {}).get('nodes') or {}).get('next_offset')
print('graphs searched:', graphs)
