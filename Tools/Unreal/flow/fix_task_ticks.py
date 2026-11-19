"""Story lane (UI's note, main 2026-11-10): the beats' TickTask data matches the story. Tasks are 0 Wake up, 1 Get
dressed, 2 Leave the house. CompleteBeat ticks a beat's TickTask when that beat completes:
  T0 (the phone, PhoneWakeUp)   -> 0 Wake up            (was -1: nothing)
  T8 (the battle, EncounterWon) -> 1 Get dressed        (unchanged: the victory line is "You're dressed.")
  T9 (the suit, PayoffEnded)    -> -1 nothing           (was 0: Wake up, a beat late)
  T10 (WalkedOut)               -> 2 Leave the house    (unchanged)
build_flow_data.ROWS matches.  ue_remote.py Tools/Unreal/flow/fix_task_ticks.py  (FOA_AREAS=/Game/FoA/Gameplay/Beats)"""
import sys
import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
from flow_common import BEATS  # noqa: E402

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'PIE running'
WANT = {'T0': 0, 'T8': 1, 'T9': -1, 'T10': 2}
out = {}
for rid in ('T0', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10'):
    da = unreal.load_asset(f'{BEATS}/DA_Beat_{rid}')
    before = da.get_editor_property('TickTask')
    want = WANT.get(rid, -1)
    if before != want:
        da.set_editor_property('TickTask', want)
        assert unreal.EditorAssetLibrary.save_loaded_asset(da, False), rid
    out[rid] = (before, da.get_editor_property('TickTask'))
print('task ticks (before, after)', out)
