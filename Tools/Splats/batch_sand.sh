#!/usr/bin/env bash
# Editor-Python part of a sandvfx hold (run INSIDE your own editor_lock hold; ue_remote reuses it via FOA_AGENT).
# Usage: bash Tools/Splats/batch_sand.sh meshes|goo|place|all
set -u
cd /p/FoA
export FOA_AGENT=sandvfx MSYS_NO_PATHCONV=1
R="timeout 240 python Tools/Unreal/ue_remote.py"
step=${1:-all}
if [ "$step" = code ] || [ "$step" = all ]; then
  $R Tools/Splats/push_hlsl.py FOA_SPLAT_PHASE=all 2>&1 | tail -4
fi
if [ "$step" = meshes ] || [ "$step" = all ]; then
  for m in SM_SandMoundSplats_B SM_SandMoundSplats_C SM_TheNightMare; do
    $R Tools/Splats/import_sand_vfx.py FOA_SPLAT_MESH=$m 2>&1 | grep -v "^$" | tail -1
  done
  $R Tools/Splats/rename_sand_vfx.py 2>&1 | tail -2          # separate run from the import (editor-rules)
fi
if [ "$step" = goo ]; then
  for m in SM_SandBurst SM_SandFaceDrift; do
    $R Tools/Splats/import_sand_vfx.py FOA_SPLAT_MESH=$m 2>&1 | grep -v "^$" | tail -1
  done
  $R Tools/Splats/sand_instances.py 2>&1 | tail -11
  $R Tools/Splats/sand_stencil.py 2>&1 | tail -1
fi
if [ "$step" = place ] || [ "$step" = all ]; then
  $R Tools/Splats/sand_instances.py 2>&1 | tail -8
  $R Tools/Splats/place_sand_vfx.py 2>&1 | tail -2
fi
