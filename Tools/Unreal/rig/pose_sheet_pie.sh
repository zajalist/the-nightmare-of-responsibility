#!/usr/bin/env bash
# One EXCLUSIVE PIE burst (PIE window, < 55 s): pose_sheet.py in the game world, where the PoseableMesh ticks and
# refreshes its bones. Root PID in Saved/RigShots/sheet_pie.pid.
set -u
cd /p/FoA
export FOA_AGENT=rig HAYBA_AGENT_ID=rig MSYS_NO_PATHCONV=1 FOA_EXCLUSIVE=1 FOA_CALLER=rig
echo $$ > Saved/RigShots/sheet_pie.pid
R() { python Tools/Unreal/ue_remote.py "$@" 2>&1 | grep -v '^\s*$' | tail -2; }
trap 'python Tools/Unreal/editor_lock.py release rig; rm -f Saved/RigShots/sheet_pie.pid' EXIT
python Tools/Unreal/editor_lock.py acquire rig --ttl 60 --wait 1500 || { echo "no lease"; exit 1; }
OUT=${FOA_SHEET_OUT:-Saved/RigShots/sheet}
rm -rf "$OUT"
R Tools/Unreal/ui/pie_call.py FOA_CALL=BEGIN
sleep 6
R Tools/Unreal/rig/pose_sheet.py FOA_WORLD=pie FOA_OUT=P:/FoA/$OUT "$@"
T0=$(date +%s)
until [ -f "$OUT/done.txt" ] || [ $(( $(date +%s) - T0 )) -ge 50 ]; do sleep 1; done
R Tools/Unreal/ui/pie_call.py FOA_CALL=END
cat "$OUT/done.txt" "$OUT/thumb_fit.json" 2>/dev/null || echo "sheet incomplete"
