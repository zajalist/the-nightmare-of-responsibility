#!/usr/bin/env bash
# Face lane runbook after the 2026-11-10 playtest hold (sequential; each step logs to Saved/FaceShots/.ah2_<step>.log):
#  1 blur v10 live (recompile_live.sh v10: off the volume, compile, auto-rollback to v8 on failure, back on, save)
#  2 garments BEFORE battle burst   3 garments: textures + MIs (Hayba), slots (editor Python)
#  4 garments AFTER battle burst    5 v10 play burst with GPU profile (leak check + overlay sheet offline after)
# Deleting RetopologyBakedMaterial and T_SK_Garment_Shirt_basecolor is a separate EXCLUSIVE step after review.
#   bash Tools/Unreal/face/after_hold2.sh [first_step]
set -u
cd /p/FoA
export FOA_AGENT=face HAYBA_AGENT_ID=face MSYS_NO_PATHCONV=1
FIRST=${1:-1}
L=Saved/FaceShots/.ah2
step() { [ "$1" -ge "$FIRST" ] || return 0; echo "== step $1 $(date +%H:%M:%S)"; }
if step 1; then bash Tools/Unreal/face/recompile_live.sh v10 > ${L}_1.log 2>&1; tail -6 ${L}_1.log; grep -q "level_save: ok" ${L}_1.log || { echo "step 1 failed"; exit 1; }; fi
if step 2; then FOA_DRIVER=Tools/Unreal/face/pie_garments.py bash Tools/Unreal/face/face_burst.sh garments_before battle > ${L}_2.log 2>&1; tail -3 ${L}_2.log; fi
if step 3; then
  python Tools/Unreal/editor_lock.py acquire face --assets /Game/FoA/Characters/Garments --ttl 300 --wait 600 >/dev/null
  timeout 280 python Tools/Unreal/face/garments_apply.py > ${L}_3.log 2>&1; python Tools/Unreal/editor_lock.py release face >/dev/null
  tail -5 ${L}_3.log
  timeout 300 python Tools/Unreal/ue_remote.py Tools/Unreal/face/garments_assign.py FOA_AREAS=Characters >> ${L}_3.log 2>&1
  grep -c "FOA_GARMENT_MI" ${L}_3.log
fi
if step 4; then FOA_DRIVER=Tools/Unreal/face/pie_garments.py bash Tools/Unreal/face/face_burst.sh garments_after battle > ${L}_4.log 2>&1; tail -3 ${L}_4.log; fi
if step 5; then bash Tools/Unreal/face/face_burst.sh v10_play play FOA_PROF=1 > ${L}_5.log 2>&1; tail -3 ${L}_5.log; fi
echo "== done $(date +%H:%M:%S)"
