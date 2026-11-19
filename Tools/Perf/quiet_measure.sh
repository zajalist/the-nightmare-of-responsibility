#!/usr/bin/env bash
# Clean re-measure for the coordinator's quiet window (no PIE or heavy viewport in the shared editor).
# (a) door portal hitches, (b) Level 2 impact frames, (c) Medium route p50/p95/over 16.7 ms; plus the Low fight.
#   bash Tools/Perf/quiet_measure.sh P:/FoA-Builds/Development_<final>      log: Saved/Perf/pack/quiet_<stamp>.log
# The build needs the final PSO cache (final_build.sh's DEV2). Runs are cooked, from P:/FoA-Builds, never P:/FoA.
set -uo pipefail
export MSYS_NO_PATHCONV=1
cd /p/FoA
DEV="${1:?usage: quiet_measure.sh <Development build>}"
LOG="Saved/Perf/pack/quiet_$(date +%Y%m%d_%H%M).log"
exec > >(tee -a "$LOG") 2>&1
rm -f "$DEV/Windows/FoA/Saved/Config/Windows/GameUserSettings.ini"  # fresh: no saved preset, the run's -ExecCmds sets it
for spec in "1 full" "0 15"; do
  set -- $spec
  q=$1; steps=$2
  echo "== $(date +%T) preset $q, steps $steps"
  extra=(); [ "$steps" != "full" ] && extra=(--steps "$steps")
  out=$(python Tools/Perf/cooked_driver.py --build "$DEV" --plan steps --presets "$q" --tag "quiet_q$q" "${extra[@]}" | grep '^out ' | cut -c5-)
  [ -n "$out" ] || { echo "!! no run dir for preset $q"; continue; }
  python - "$out" <<'EOF'
import json, sys
rows = json.load(open(sys.argv[1] + '/driver.json'))
print('   others_gpu:', [(r['at'], r['pct']) for r in rows if r['kind'] == 'others_gpu'])
EOF
  python Tools/Perf/route_frames.py "$out" | tail -2
  python Tools/Perf/split_steps.py "$out"
  python Tools/Perf/cooked_hitches.py "$out" --ms 50 | head -60
done
echo "== $(date +%T) done"
