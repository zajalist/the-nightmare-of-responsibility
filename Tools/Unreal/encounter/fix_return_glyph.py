"""Replace the Return symbol (U+23CE, missing from Darker Grotesque: "Could not find Glyph" warnings) in the encounter's
string and text pins with the word "Enter" (UI text rule: no decorative symbols). Hayba only; idempotent; compiles 0/0.
  python Tools/Unreal/encounter/fix_return_glyph.py"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal/flow']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402
from story_text import plain  # noqa: E402

GLYPH = '\u23ce'
ASSETS = ('/Game/FoA/Gameplay/Encounter/BP_Encounter', '/Game/FoA/Gameplay/Encounter/WBP_Encounter')
os.environ['HAYBA_AGENT_ID'] = 'story'
names = json.loads(Path('P:/FoA/Saved/StoryShots/graph_names.json').read_text())


def fixed(v):
    v = plain(v)  # text pins export as NSLOCTEXT(...): write the display string back
    out = v.replace(' ' + GLYPH, ' Enter').replace(GLYPH + ' ', 'Enter ').replace(GLYPH, 'Enter')
    return out


assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + a for a in ASSETS], ttl_s=180, wait_s=180)
report = []
try:
    for path in ASSETS:
        for graph in names[path]:
            if not h.call('blueprint_inspect_graph', {'path': path, 'graph_name': graph}).get('ok'):
                continue
            ns, _ = inspect(path, graph)
            hits = [(n['node_id'], p['name'], p['default_value']) for n in ns for p in n['pins']
                    if GLYPH in (p.get('default_value') or '')]
            if hits:
                b = Batch(path, graph)
                for nid, pin, val in hits:
                    b.pin(nid, pin, fixed(val))
                    report.append(dict(asset=path, graph=graph, before=val, after=fixed(val)))
                b.run()
    Path('P:/FoA/Saved/StoryShots/return_glyph_fix.json').write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print('return glyph replaced', len(report), json.dumps(report, ensure_ascii=False)[:600])
finally:
    h.release('story', token)
