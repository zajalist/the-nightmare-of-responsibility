#!/usr/bin/env bash
# Coordinator playtest: one recorded PIE burst of Tools/Unreal/gameplay/pie_play.py plan <A|B|C|D> (real interactions),
# under the EXCLUSIVE lease, frames -> Saved/Devlog/playtest_<plan>.mp4 and Saved/QA/playtest_<plan>_frames/.
#   bash Tools/QA/playtest_plan.sh A [cap_seconds]
set -u
cd /p/FoA
export FOA_AGENT=main-qa HAYBA_AGENT_ID=main-qa MSYS_NO_PATHCONV=1
PLAN=${1:-A}; CAP=${2:-90}
SHOTS=Saved/Screenshots/WindowsEditor
D() { timeout 25 python Tools/Unreal/integration/run_read.py "$@" 2>&1 | grep -v '^\s*$' | tail -1; }
PIE=0
cleanup() { [ "$PIE" = 1 ] && D Tools/Unreal/ui/pie_call.py FOA_CALL=END; python Tools/Unreal/editor_lock.py release main-qa; }
trap cleanup EXIT
python Tools/Unreal/editor_lock.py acquire main-qa --ttl $((CAP + 60)) --wait 1500 | tail -1
python Tools/Unreal/editor_lock.py status 2>/dev/null | grep -q "^main-qa: exclusive" || { echo "abort: no EXCLUSIVE"; exit 1; }
touch Saved/QA/.shotmark; rm -f "Saved/Integration/play_${PLAN}.json"
T0=$(date +%s); PIE=1
D Tools/Unreal/ui/pie_call.py FOA_CALL=BEGIN
sleep 4
D Tools/Unreal/gameplay/pie_play.py "FOA_PLAN=$PLAN" "FOA_CAP=$CAP"
until [ -f "Saved/Integration/play_${PLAN}.json" ] || [ $(( $(date +%s) - T0 )) -ge $((CAP + 15)) ]; do sleep 1; done
D Tools/Unreal/ui/pie_call.py FOA_CALL=END; PIE=0
python Tools/Unreal/editor_lock.py release main-qa
echo "burst $(( $(date +%s) - T0 )) s"; sleep 2
F=Saved/QA/playtest_${PLAN}_frames; rm -rf "$F"; mkdir -p "$F"
find "$SHOTS" -name 'ScreenShot*.png' -newer Saved/QA/.shotmark -exec mv {} "$F/" \;
echo "frames $(ls $F | wc -l)"
python Tools/Unreal/integration/bp_errors.py --since 0 2>/dev/null | tail -3
