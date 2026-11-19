"""qa lane, read-only: export DT_Interactions and DT_Items to Saved/QA/dt_*.json (the playtest's route is planned from
them).  python Tools/Unreal/integration/run_read.py Tools/QA/probe_rows.py"""
import unreal

for name in ('DT_Interactions', 'DT_Items'):
    dt = unreal.load_asset('/Game/FoA/Gameplay/' + name)
    with open(f'P:/FoA/Saved/QA/{name.lower()}.json', 'w', encoding='utf-8') as fh:
        fh.write(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(dt))
print('rows exported')
