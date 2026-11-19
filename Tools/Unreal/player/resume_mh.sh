#!/usr/bin/env bash
# Player lane: after P10's run_steps finishes, wire the MetaHuman in one lease (build_protagonist FOA_STEP=all),
# then P11 (BP_Nightmare). WAIT_PID=<pid> waits for a running run_steps first.
cd /p/FoA || exit 1
R=Tools/Unreal/player/run_steps.sh
L=${LOG:?}
N=/Game/FoA/Characters/Player/BP_Nightmare
if [ -n "${WAIT_PID:-}" ]; then while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 5; done; fi
tail -1 "$L" | grep -q "ALL OK" || { echo "P10 did not finish OK"; exit 1; }
echo "P10 DONE $(date +%T)"
FOA_AREAS=/Game/FoA/Characters/Player,/Game/FoA/Characters/Protagonist bash $R "build_protagonist.py FOA_STEP=all" || exit 1
echo "PROTAGONIST DONE $(date +%T)"
FOA_AREAS=/Game/FoA/Characters/Hero bash $R "compat_skeleton.py FOA_MESH=/Game/FoA/Characters/Hero/SK_Hero FOA_PHYSICS=1" || exit 1
HAYBA_AGENT_ID=player timeout 60 python Tools/Unreal/hayba_call.py blueprint_create \
  "{\"name\": \"BP_Nightmare\", \"package_path\": \"$N\", \"parent_class_path\": \"/Script/Engine.Character\"}" | head -c 300; echo
bash $R "build_nightmare.py FOA_STEP=vars" "compile_bp.py FOA_BPS=$N" "build_nightmare.py FOA_STEP=graphs" \
        "compile_bp.py FOA_BPS=$N" "build_nightmare.py FOA_STEP=api" "compile_bp.py FOA_BPS=$N" \
        "build_nightmare.py FOA_STEP=defaults" "compile_bp.py FOA_BPS=$N" || exit 1
echo "RESUME DONE $(date +%T)"
