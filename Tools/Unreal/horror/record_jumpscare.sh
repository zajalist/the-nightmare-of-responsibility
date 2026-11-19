#!/usr/bin/env bash
# Horror lane: one recorded PIE burst of the jumpscare (copy of Tools/Unreal/gameplay/record_loop.sh under the horror
# lease owner). EXCLUSIVE only in the PIE window (:x0-:x2), 55 s wall clock at most, released on exit.
#   bash Tools/Unreal/horror/record_jumpscare.sh <name>
# Steps inside the burst run through run_read.py (no second lease). Frames: in-engine 'Shot showui' (pie_jumpscare.py).
# Outputs: Saved/HorrorShots/<name>_frames/, Saved/HorrorShots/<name>_timeline.json, Saved/HorrorShots/<name>_bp_errors.csv.
# This script's PID goes to Saved/HorrorShots/record.pid: stop only that PID.
set -u
cd /p/FoA
export FOA_AGENT=horror HAYBA_AGENT_ID=horror MSYS_NO_PATHCONV=1
NAME=${1:-jumpscare}
CAP=${FOA_PIE_CAP:-55}
SHOTS=Saved/Screenshots/WindowsEditor
D() { timeout 25 python Tools/Unreal/integration/run_read.py "$@" 2>&1 | grep -v '^\s*$' | tail -1; }
mkdir -p Saved/HorrorShots "$SHOTS"
echo $$ > Saved/HorrorShots/record.pid
PIE=0
cleanup() {
  [ "$PIE" = 1 ] && D Tools/Unreal/ui/pie_call.py FOA_CALL=END
  python Tools/Unreal/editor_lock.py release horror
  rm -f Saved/HorrorShots/record.pid
}
trap cleanup EXIT
trap 'exit 1' TERM INT HUP
python Tools/Unreal/editor_lock.py acquire horror --ttl 120 --wait 1500 > Saved/HorrorShots/.acquire.txt 2>&1
cat Saved/HorrorShots/.acquire.txt
grep -q "old exclusive lock" Saved/HorrorShots/.acquire.txt && { echo "abort: Hayba leases not answering"; exit 1; }
python Tools/Unreal/editor_lock.py status 2>/dev/null | grep -q "^horror: exclusive" || { echo "abort: no EXCLUSIVE"; exit 1; }
touch Saved/HorrorShots/.shotmark
rm -f "Saved/HorrorShots/${NAME}_timeline.json"
SINCE=$(date -u +%H.%M.%S)
T0=$(date +%s)
PIE=1
D Tools/Unreal/ui/pie_call.py FOA_CALL=BEGIN
sleep 4
D Tools/Unreal/horror/pie_jumpscare.py "FOA_RUN=$NAME"
until [ -f "Saved/HorrorShots/${NAME}_timeline.json" ] || [ $(( $(date +%s) - T0 )) -ge "$CAP" ]; do sleep 1; done
D Tools/Unreal/ui/pie_call.py FOA_CALL=END
PIE=0
python Tools/Unreal/editor_lock.py release horror
echo "pie burst $(( $(date +%s) - T0 )) s"
sleep 2
F=Saved/HorrorShots/${NAME}_frames; rm -rf "$F"; mkdir -p "$F"
find "$SHOTS" -name 'ScreenShot*.png' -newer Saved/HorrorShots/.shotmark -exec mv {} "$F/" \;
echo "frames $(ls "$F" | wc -l) -> $F"
python Tools/Unreal/integration/bp_errors.py --since "$SINCE" --csv "Saved/HorrorShots/${NAME}_bp_errors.csv" | sed -n '/--- by/,$p'
echo "since $SINCE done"
