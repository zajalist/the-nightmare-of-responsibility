#!/usr/bin/env bash
# Player lane resume after an editor (re)start: waits for the PSP hotfix line and Hayba, then runs P10, the
# protagonist wiring and P11 in order. Each ue_remote run leases only what it edits, for its own duration.
# START=<n> skips the first n P10 steps (they are idempotent anyway; skipping just saves queue time).
cd /p/FoA || exit 1
R=Tools/Unreal/player/run_steps.sh
P=/Game/FoA/Characters/Player
B=$P/BP_FoAPlayer
N=$P/BP_Nightmare
MHC=/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist
until grep -q "Hayba PSP hotfix: patched" Saved/Logs/FoA.log 2>/dev/null && \
      timeout 15 python Tools/Unreal/hayba_call.py ping 2>/dev/null | grep -q '"ok": true'; do sleep 15; done
echo "editor ready $(date +%T)"
# P10: BP_FoAPlayer API (look-at fix, cinematic, sand, PlayerPos, garments, Equip/UnequipAll)
P10=("build_modular.py FOA_STEP=components" "compile_bp.py FOA_BPS=$B" "build_player_bp.py FOA_STEP=assets"
     "compile_bp.py FOA_BPS=$B" "build_player_bp.py FOA_STEP=graphs" "compile_bp.py FOA_BPS=$B"
     "build_modular.py FOA_STEP=graphs" "compile_bp.py FOA_BPS=$B" "build_modular.py FOA_STEP=equip"
     "compile_bp.py FOA_BPS=$B")
bash $R "${P10[@]:${START:-0}}" || exit 1
echo "P10 DONE $(date +%T)"
# Protagonist: body skeleton compatible with SK_Mannequin, then face/grooms/outfit, leader pose, body mesh
FOA_AREAS=/Game/FoA/Characters/Protagonist bash $R "compat_skeleton.py FOA_MESH=$MHC/Body/SKM_MHC_Protagonist_BodyMesh" || exit 1
bash $R "build_protagonist.py FOA_STEP=components" "compile_bp.py FOA_BPS=$B" "build_protagonist.py FOA_STEP=leader" \
        "compile_bp.py FOA_BPS=$B" "build_protagonist.py FOA_STEP=mesh" "compile_bp.py FOA_BPS=$B" || exit 1
echo "PROTAGONIST DONE $(date +%T)"
# P11: BP_Nightmare (SK_Hero, compatible skeleton + physics asset first)
FOA_AREAS=/Game/FoA/Characters/Hero bash $R "compat_skeleton.py FOA_MESH=/Game/FoA/Characters/Hero/SK_Hero FOA_PHYSICS=1" || exit 1
HAYBA_AGENT_ID=player timeout 60 python Tools/Unreal/hayba_call.py blueprint_create \
  "{\"name\": \"BP_Nightmare\", \"package_path\": \"$N\", \"parent_class_path\": \"/Script/Engine.Character\"}" | head -c 300; echo
bash $R "build_nightmare.py FOA_STEP=vars" "compile_bp.py FOA_BPS=$N" "build_nightmare.py FOA_STEP=graphs" \
        "compile_bp.py FOA_BPS=$N" "build_nightmare.py FOA_STEP=api" "compile_bp.py FOA_BPS=$N" \
        "build_nightmare.py FOA_STEP=defaults" "compile_bp.py FOA_BPS=$N" || exit 1
echo "RESUME DONE $(date +%T)"
