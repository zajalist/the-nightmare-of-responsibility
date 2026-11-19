#!/bin/bash
# Story lane: apply and prove both reworked transitions (the user's picks, 2026-11-10) once the editor is up.
#   bash Tools/Unreal/flow/apply_transitions.sh [apply|prove|all]
cd /p/FoA
export MSYS_NO_PATHCONV=1 HAYBA_AGENT_ID=story FOA_AGENT=story FOA_CALLER=story
step=${1:-all}
if [ "$step" != prove ]; then
  python Tools/Unreal/flow/patch_wont_come.py || exit 1
  FOA_AREAS=/Game/FoA/Cinematics/Wardrobe python Tools/Unreal/ue_remote.py Tools/Unreal/flow/build_wardrobe_fall.py | grep -E "BATTLE_INTRO|rror" || exit 1
  FOA_AREAS=/Game/FoA/Gameplay python Tools/Unreal/ue_remote.py Tools/Unreal/flow/add_wardrobe_var.py | grep -E "WARDROBE_VAR|rror" || exit 1
  python Tools/Unreal/flow/patch_wardrobe_fall.py || exit 1
fi
if [ "$step" != apply ]; then
  python Tools/Unreal/flow/prove_defeat_run.py wont_come wardrobe_fall
  for n in wont_come wardrobe_fall; do python Tools/Unreal/flow/proof_media.py $n 20 12; done
fi
