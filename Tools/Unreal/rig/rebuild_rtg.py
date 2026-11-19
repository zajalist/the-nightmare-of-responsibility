"""After the rig-fix reimport: the FoA_MannyAligned target pose re-aligned to the new finger joints, and the finger rules
(metacarpals fed only by metacarpals, phalanges One-to-One). The new lowerarm_twist_01 bones get no chain: the Manny
clips carry no twist keys, so ABP_FoA_TeenPost drives them from the hand. Idempotent.
  $env:FOA_AREAS='Characters'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/rebuild_rtg.py"""
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
from finger_chains import fix_fingers  # noqa: E402  (shared finger rules, anim lane's module)

P = "/Game/FoA/Characters/Player/Retarget/"
SOT = unreal.RetargetSourceOrTarget


def run():
    rtg = unreal.load_asset(P + "RTG_Mannequin_to_Teen")
    r = unreal.IKRetargeterController.get_controller(rtg)
    r.set_current_retarget_pose("FoA_MannyAligned", SOT.TARGET)
    r.reset_retarget_pose("FoA_MannyAligned", [], SOT.TARGET)  # empty list: every bone back to the new reference
    r.auto_align_all_bones(SOT.TARGET)
    unmapped, one_to_one = fix_fingers(r)
    unreal.EditorAssetLibrary.save_loaded_asset(rtg, False)
    print("RTG_REBUILT metacarpals unmapped", unmapped, "one-to-one", one_to_one)


run()
