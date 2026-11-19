#!/usr/bin/env bash
# level2 lane, round 3: the order the editor steps run in (each takes its own short lease).
set -e
cd /p/FoA/Tools/Unreal/level2
export MSYS_NO_PATHCONV=1 PYTHONUNBUFFERED=1 HAYBA_AGENT_ID=level2 FOA_AGENT=level2
python -B build_l2_round3.py selftest card declare
(cd /p/FoA && FOA_AREAS=asset:/Game/FoA/Level2/Journey/BP_L2Journey python Tools/Unreal/ue_remote.py Tools/Unreal/level2/build_l2_round3.py FOA_R3_STEP=templates)
python -B build_l2_round3.py graphs hooks
FOA_SAND=1 python -B build_l2_ending.py journey threshold
echo ALL_DONE
