"""qa lane, read-only: the beat data assets (DA_Beat_T0..T10) as the director reads them -> Saved/QA/beats.json."""
import json

import unreal

out = []
for i in range(11):
    a = unreal.load_asset(f'/Game/FoA/Gameplay/Beats/DA_Beat_T{i}')
    row = {}
    for k in ('Id', 'Objective', 'Event', 'Events', 'AdvanceOn', 'Tier', 'bShowPhone', 'Learns', 'TickTask', 'Hint'):
        try:
            v = a.get_editor_property(k)
            row[k] = v if isinstance(v, (int, float, bool)) else str(v)
        except Exception:  # not a property of PDA_Beat
            pass
    out.append(row)
json.dump(out, open('P:/FoA/Saved/QA/beats.json', 'w', encoding='utf-8'), indent=1)
print(json.dumps(out)[:3000])
