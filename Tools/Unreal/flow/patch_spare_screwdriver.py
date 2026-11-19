"""The refilled screwdriver can be looked at, not taken (main, 2026-11-10). At T7 StageWrongWall runs RefillDrawer
(ResetForNewDay on Screwdriver_DeskDrawer): the screwdriver is back on the desk, the uncanny part. Its job ended at
LatchFreed (ToolsDone took it out of the carried set), and T7 always comes after the latch, so RefillDrawer now leaves
the pickup in State 'Spare': visible, Look only ("It's back. I didn't put it back."), no Take row, so no inspect view
and no new item. A new morning's ResetForNewDay makes it Available again.
  1. DT_Interactions: data_rows.SPARE_ROW (name Screwdriver_Spare_Look) inserted before the first Screwdriver row, so it
     wins over the wildcard Look row (rows match in table order).   ue_remote, FOA_STEP=row
  2. BP_BeatDirector.RefillDrawer: after ResetForNewDay, SetState('Spare', instant).   Hayba
  python Tools/Unreal/flow/patch_spare_screwdriver.py"""
import json
import os
import sys

DT = '/Game/FoA/Gameplay/DT_Interactions'
P = '/Game/FoA/Gameplay/BP_BeatDirector'

if os.environ.get('FOA_STEP') == 'row':
    import unreal
    sys.path.insert(0, 'P:/FoA/Tools/Unreal/gameplay')
    import importlib
    import data_rows
    importlib.reload(data_rows)
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None, 'PIE running'
    lib = unreal.DataTableFunctionLibrary
    table = unreal.load_asset(DT)
    rows = json.loads(lib.export_data_table_to_json_string(table))
    new = dict(data_rows.SPARE_ROW)
    if any(r['Name'] == new['Name'] for r in rows):
        print('spare row kept')
    else:
        at = next(i for i, r in enumerate(rows) if r['Interactable'] == 'Screwdriver')
        template = rows[at]
        row = {k: (new[k] if k in new else template[k]) for k in template}
        row['Name'] = new['Name']
        rows.insert(at, row)
        assert lib.fill_data_table_from_json_string(table, json.dumps(rows))
        after = [r['Name'] for r in json.loads(lib.export_data_table_to_json_string(table))]
        assert after.index(new['Name']) == at and len(after) == len(rows), after[at - 1:at + 2]
        assert unreal.EditorAssetLibrary.save_loaded_asset(table, False)
        print('spare row inserted at', at, 'before', after[at + 1])
    sys.exit(0)

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import subprocess  # noqa: E402
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

BASE = '/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'
os.environ['HAYBA_AGENT_ID'] = 'story'


def refill():
    ns, es = inspect(P, 'RefillDrawer')
    if any(n['title'] == 'SetState' for n in ns):
        return 'kept'
    reset = find(ns, 'ResetForNewDay')
    actor = find(ns, 'Get RefillActor')
    b = Batch(P, 'RefillDrawer')
    b.node('pickup', 'cast', 700, 0, class_path=BASE)
    b.link(actor, 'RefillActor', 'pickup', 'Object')
    b.fn('spare', BASE + ':SetState', 1000, 0, NewState='Spare', bInstant='true')
    b.link('pickup', 'AsBP Interactable', 'spare', 'self')
    b.link(reset, 'then', 'pickup', 'execute')
    b.chain('pickup', 'spare')
    b.comment('Back on the desk, but spent', ['pickup', 'spare'])
    b.run()
    return 'RefillDrawer leaves it Spare (look only)'


if __name__ == '__main__':
    assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    env = dict(os.environ, FOA_AGENT='story', HAYBA_AGENT_ID='story', FOA_AREAS=DT, FOA_STEP='row', MSYS_NO_PATHCONV='1')
    out = subprocess.run([sys.executable, 'P:/FoA/Tools/Unreal/ue_remote.py', os.path.abspath(__file__), 'FOA_STEP=row'], env=env,
                         capture_output=True, text=True, timeout=600)
    print(out.stdout[-600:], out.stderr[-600:])
    assert 'spare row' in out.stdout, 'row step failed'
    token = h.lease_acquire('story', ['asset:' + P], ttl_s=240, wait_s=240)
    try:
        print('refill', refill())
    finally:
        h.release('story', token)
