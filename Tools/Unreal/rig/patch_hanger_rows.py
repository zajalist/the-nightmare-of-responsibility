"""Rig lane: the hanger rows' Montage fields only (main's go 2026-11-11; story told which rows), in place.
  FOA_AREAS=Gameplay python Tools/Unreal/ue_remote.py Tools/Unreal/rig/patch_hanger_rows.py
Door/Locked/Use/Hanger -> LatchFree (requires Knows.KeySnaps) and Door/KeyJammed/Use/Hanger -> LatchFree: AM_FoA_HangerDoor;
Bed/ClothingSnag/Use/Hanger: AM_FoA_HangerBed. Every other row and field is preserved (read back and compared).
gameplay/data_rows.py carries the same change so a table rebuild keeps it."""
import json
from pathlib import Path

import unreal

assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None, 'PIE running'
M = '/Game/FoA/Characters/Player/Montages/'
DOOR, BED = M + 'AM_FoA_HangerDoor.AM_FoA_HangerDoor', M + 'AM_FoA_HangerBed.AM_FoA_HangerBed'
table = unreal.load_asset('/Game/FoA/Gameplay/DT_Interactions')
original = json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(table))
rows = json.loads(json.dumps(original))
want = {('Door', 'Locked', 'LatchFree'): DOOR, ('Door', 'KeyJammed', 'LatchFree'): DOOR, ('Bed', 'ClothingSnag', 'ClothingFreed'): BED}
hit = {}
for r in rows:
    k = (r['Interactable'], r['State'], r['NextState'])
    if r['Verb'] == 'Use' and r['Item'] == 'Hanger' and k in want:
        hit.setdefault(k, []).append(r['Name'])
        r['Montage'] = want[k]
assert all(len(hit.get(k, [])) == 1 for k in want), hit
assert unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(table, json.dumps(rows))
observed = json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(table))
changed = [b['Name'] for a, b in zip(original, observed) if a != b]
diff = [k for a, b in zip(original, observed) for k in a if a[k] != b[k]]
assert len(observed) == len(original) and len(changed) <= 3 and set(diff) <= {'Montage'}, (changed, diff)
assert all(b['Montage'].split('.')[0].endswith(('HangerDoor', 'HangerBed')) for b in observed if b['Name'] in sum(hit.values(), [])), 'readback'
unreal.EditorAssetLibrary.save_loaded_asset(table, False)
Path('P:/FoA/Saved/RigShots/hanger_use/rows_patch.json').write_text(json.dumps(dict(changed=changed, rows=hit), indent=1))
print('ROWS', changed, 'preserved', len(rows) - len(changed))
