#!/usr/bin/env bash
# Runs player-lane editor steps in order, each holding only /Game/FoA/Characters/Player for its own duration
# (editor-rules throughput rule), stopping at the first failure. Usage (from anywhere):
#   bash Tools/Unreal/player/run_steps.sh "build_modular.py FOA_STEP=components" "compile_bp.py FOA_BPS=/Game/..." ...
cd /p/FoA || exit 1
export MSYS_NO_PATHCONV=1 FOA_AGENT=player HAYBA_AGENT_ID=player FOA_AREAS=${FOA_AREAS:-/Game/FoA/Characters/Player}
for spec in "$@"; do
  set -- $spec
  echo "== $spec ($(date +%T))"
  out=$(python Tools/Unreal/ue_remote.py "Tools/Unreal/player/$1" "${@:2}" 2>&1)
  rc=$?
  echo "$out" | grep -v "^\s*$" | grep -v "Hayba leases unavailable" | tail -6
  if [ $rc -ne 0 ] || echo "$out" | grep -q "Traceback\|AssertionError"; then
    echo "STOP at: $spec (rc=$rc)"
    exit 1
  fi
done
echo "ALL OK ($(date +%T))"
