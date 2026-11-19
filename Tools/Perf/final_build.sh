#!/usr/bin/env bash
# Final build chain (perf lane, 11-18): reference check -> Development package -> cooked PSO recordings at Low, Medium,
# High, Epic -> bundled PSO cache -> Shipping package -> true first boot -> F-key check. Stops at the first failure.
#   bash Tools/Perf/final_build.sh          log: Saved/Perf/pack/final_<stamp>.log
# Game processes run only from P:/FoA-Builds (never against P:/FoA) and never while a user's Standalone Game runs.
set -uo pipefail
export MSYS_NO_PATHCONV=1
cd /p/FoA
LOG="Saved/Perf/pack/final_$(date +%Y%m%d_%H%M).log"
exec > >(tee -a "$LOG") 2>&1
step() { echo "== $(date +%T) $*"; }
die() { echo "!! $(date +%T) FAILED: $*"; exit 1; }
user_game() {  # a Standalone Game the user started from the editor, or a packaged FoA we did not start
  powershell -NoProfile -Command "@(Get-CimInstance Win32_Process | Where-Object { (\$_.Name -like 'UnrealEditor*' -and \$_.CommandLine -match ' -game' -and \$_.CommandLine -notmatch 'FoA-PerfMirror') -or \$_.Name -like 'FoA*' }).Count" | tr -d '\r'
}
guard() { [ "$(user_game)" = "0" ] || die "a game process is running (user's Standalone Game?): not launching"; }

step "reference check"
python Tools/Perf/ref_check.py --hours 12 || echo "   (review the list above; the cook decides)"

step "Development package"
bash Tools/Perf/pack.sh Development | tee /dev/stderr | grep -q "BUILD SUCCESSFUL" || die "Development package"
DEV=$(ls -d /p/FoA-Builds/Development_* | sort | tail -1)
echo "   DEV=$DEV"

for q in 0 1 2 3; do
  step "PSO recording, preset $q"
  guard
  python Tools/Perf/cooked_driver.py --build "$DEV" --plan steps --presets "$q" --logpso --tag "pso_final_q$q" || die "PSO recording q$q"
done
ls "$DEV/Windows/FoA/Saved/CollectedPSOs/"*.rec.upipelinecache >/dev/null 2>&1 || die "no PSO recordings in $DEV"

step "PSO cache"
python Tools/Perf/pso_cache.py --build "$DEV" | tee /dev/stderr | grep -q "stable PSOs" || die "pso_cache"

step "Shipping package"
bash Tools/Perf/pack.sh Shipping | tee /dev/stderr | grep -q "BUILD SUCCESSFUL" || die "Shipping package"
SHIP=$(ls -d /p/FoA-Builds/Shipping_* | sort | tail -1)
echo "   SHIP=$SHIP"
grep -h "Wrote [0-9]* binary PSOs.*SM6" Saved/Perf/pack/uat_Shipping_*.log | tail -1

step "Development package with the final PSO cache (for the quiet-window re-measure; Shipping has no CSV profiler)"
bash Tools/Perf/pack.sh Development | tee /dev/stderr | grep -q "BUILD SUCCESSFUL" || die "Development package 2"
DEV2=$(ls -d /p/FoA-Builds/Development_* | sort | tail -1)
echo "   DEV2=$DEV2"

step "true first boot"
guard
python Tools/Perf/cooked_driver.py --build "$SHIP" --plan smoke --res 1920x1080 --tag final_firstboot --firstboot || die "first boot"

step "F-key check (F6 F7 F8 F9 F10 must do nothing)"
guard
python Tools/Perf/cooked_driver.py --build "$SHIP" --plan fkeys --res 1280x720 --tag final_fkeys --firstboot || die "F-key check"

step "done: SHIP=$SHIP (zip: $SHIP.zip) DEV2=$DEV2 (re-measure) DEV=$DEV (PSO recordings)"
