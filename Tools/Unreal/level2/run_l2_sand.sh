#!/usr/bin/env bash
# level2 lane: import the five Lux3D sand splats, then add them to the interview set and the job stops.
# Each editor step is short and takes its own lease (ue_remote: FOA_AREAS; builders: editor_lock).
set -e
cd /p/FoA
export MSYS_NO_PATHCONV=1 PYTHONUNBUFFERED=1 HAYBA_AGENT_ID=level2 FOA_AGENT=level2
for m in SM_SandBriefcase SM_SandBills SM_SandCrow SM_SandCalendar SM_SandNecktie; do
  FOA_AREAS=asset:/Game/FoA/Level2/Journey/Sand python Tools/Unreal/ue_remote.py Tools/Unreal/level2/import_l2_sand.py FOA_SPLAT_MESH=$m
done
cd Tools/Unreal/level2
python -B build_l2_sand_set.py components
(cd /p/FoA && FOA_AREAS=asset:/Game/FoA/Level2/Journey/BP_L2StopSet python Tools/Unreal/ue_remote.py Tools/Unreal/level2/build_l2_sand_set.py FOA_SAND_STEP=templates)
python -B build_l2_sand_set.py graphs
python -B build_l2_stop_sand.py components
(cd /p/FoA && FOA_AREAS=asset:/Game/FoA/Level2/Journey/BP_L2Journey python Tools/Unreal/ue_remote.py Tools/Unreal/level2/build_l2_stop_sand.py FOA_SAND_STEP=templates)
python -B build_l2_stop_sand.py graphs hooks
FOA_SAND=1 python -B build_l2_ending.py journey
echo ALL_DONE
