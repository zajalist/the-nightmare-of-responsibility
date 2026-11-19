#!/usr/bin/env bash
# One playthrough burst (EXCLUSIVE, PIE window, PIE up <= 58 s): pie_play.py plan A|B|C|D from cold boot.
#   bash Tools/Unreal/gameplay/play_burst.sh A
# -> Saved/Integration/play_<plan>.json (steps + per-beat system state), Saved/Integration/play_<plan>_frames/*.png
cd /p/FoA
export MSYS_NO_PATHCONV=1 FOA_AGENT=gameplay HAYBA_AGENT_ID=gameplay PYTHONUNBUFFERED=1
PLAN=${1:-A}
F=Saved/Integration/play_${PLAN}_frames; SHOTS=Saved/Screenshots/WindowsEditor
D() { timeout 25 python Tools/Unreal/integration/run_read.py "$@" 2>&1 | grep -v '^\s*$' | tail -1; }
PIE=0
stop() {
  [ "$PIE" = 1 ] && python Tools/Unreal/hayba_call.py editor_stop_pie '{}' | head -c 100; echo
  echo "PIE_END $(date +%T) up $(( $(date +%s) - T0 )) s"
  python Tools/Unreal/editor_lock.py release gameplay
  rm -rf "$F"; mkdir -p "$F"
  find "$SHOTS" -name '*Shot*.png' -newer Saved/Integration/.playmark -exec mv {} "$F/" \;
  echo "frames $(ls $F | wc -l) -> $F"
}
python Tools/Unreal/editor_lock.py acquire gameplay --ttl 120 --wait 1500 || exit 1
trap stop EXIT
touch Saved/Integration/.playmark
T0=$(date +%s); PIE=1
echo "PIE_START $(date +%T)"
python Tools/Unreal/hayba_call.py editor_start_pie '{}' | head -c 120; echo
for i in $(seq 1 20); do python Tools/Unreal/hayba_call.py editor_pie_actor_list '{}' >/dev/null 2>&1 && break; sleep 0.5; done
sleep 2
rm -f Saved/Integration/play_$PLAN.json
D Tools/Unreal/gameplay/pie_play.py FOA_PLAN=$PLAN FOA_CAP=$(( 56 - ($(date +%s) - T0) ))
until [ -f Saved/Integration/play_$PLAN.json ] || [ $(( $(date +%s) - T0 )) -ge 58 ]; do sleep 1; done
python - <<PY
import json
for e in json.load(open('P:/FoA/Saved/Integration/play_$PLAN.json')):
    k=e['kind']
    if k in ('beat','miss','interact','end','turn','phone'):
        print(e['t'], k, {x: e.get(x) for x in ('beat','want','focus','prompt','verb','move','why','screen','view','day','knows','garments','phone','mpc','battle','ambience') if e.get(x) not in (None, [], {})})
PY
