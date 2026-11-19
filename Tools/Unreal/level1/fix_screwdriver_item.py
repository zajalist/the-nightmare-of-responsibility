"""level1 lane: DT_Items' Screwdriver row pointed at /Game/FoA/Props/screwdriver/StaticMeshes/screwdriver, which no longer
exists (the perf lane's Shipping cook flagged the dangling reference; it was the only one in Content). It now points at
the mesh the level's Screwdriver_DeskDrawer actually uses, screwdriver_1k. Every other row and field is kept (export,
change one field, re-import, read back). Idempotent.
  FOA_AREAS=Gameplay python Tools/Unreal/ue_remote.py Tools/Unreal/level1/fix_screwdriver_item.py   (inside an asset lease on DT_Items)"""
import json

import unreal

NEW = '/Game/FoA/Props/screwdriver/screwdriver_1k/StaticMeshes/screwdriver_1k.screwdriver_1k'
dt = unreal.load_asset('/Game/FoA/Gameplay/DT_Items')
assert unreal.EditorAssetLibrary.does_asset_exist(NEW.split('.')[0]), NEW
rows = json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(dt))
row = next(r for r in rows if r['Name'] == 'Screwdriver')
if row['Mesh'] != NEW:
    before = json.dumps(rows, sort_keys=True)
    row['Mesh'] = NEW
    assert unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(dt, json.dumps(rows)), 'import failed'
    back = json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(dt))
    assert len(back) == len(rows) and next(r for r in back if r['Name'] == 'Screwdriver')['Mesh'] == NEW, 'read back'
    changed = [k for a, b in zip(json.loads(before), back) for k in a if a[k] != b[k]]
    assert changed == ['Mesh'], changed
    assert unreal.EditorAssetLibrary.save_loaded_asset(dt, False)
print('SCREWDRIVER_ITEM', next(r for r in json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(dt)) if r['Name'] == 'Screwdriver')['Mesh'])
