#!/usr/bin/env bash
# One short EXCLUSIVE PIE burst (in a PIE window, < 40 s): reads the real player body (players-only, no scratch assets): the twist probe runs in the game world, where the
# post-process ABP certainly ticks. Root PID in Saved/RigShots/audit/pie_twist.pid.
set -u
cd /p/FoA
export FOA_AGENT=rig HAYBA_AGENT_ID=rig MSYS_NO_PATHCONV=1 FOA_EXCLUSIVE=1 FOA_CALLER=rig
echo $$ > Saved/RigShots/audit/pie_twist.pid
R() { python Tools/Unreal/ue_remote.py "$@" 2>&1 | grep -v '^\s*$' | tail -2; }
trap 'python Tools/Unreal/editor_lock.py release rig; rm -f Saved/RigShots/audit/pie_twist.pid' EXIT
python Tools/Unreal/editor_lock.py acquire rig --ttl 60 --wait 1500 || { echo "no lease"; exit 1; }
rm -f Saved/RigShots/audit/twist_verify.json
R Tools/Unreal/ui/pie_call.py FOA_CALL=BEGIN
sleep 6
R Tools/Unreal/rig/twist_verify.py FOA_WORLD=pie
T0=$(date +%s)
until [ -f Saved/RigShots/audit/twist_verify.json ] || [ $(( $(date +%s) - T0 )) -ge 20 ]; do sleep 1; done
R Tools/Unreal/ui/pie_call.py FOA_CALL=END
cat Saved/RigShots/audit/twist_verify.json 2>/dev/null || echo "no result"
