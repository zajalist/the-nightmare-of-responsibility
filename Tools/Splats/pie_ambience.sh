#!/usr/bin/env bash
# One BP_SandAmbience proof burst (EXCLUSIVE in a PIE window, PIE up <= 58 s): pie_ambience.py plan amb|fore|live.
#   bash Tools/Splats/pie_ambience.sh amb
# -> Saved/WorldShots/pie_<plan>.json + Saved/WorldShots/pie_<plan>_raw/*.png (whole editor window; crop with
#    Tools/Splats/pie_ambience_media.py <plan>)
cd /p/FoA
export MSYS_NO_PATHCONV=1 FOA_AGENT=world HAYBA_AGENT_ID=world PYTHONUNBUFFERED=1
PLAN=${1:-amb}
F=Saved/WorldShots/pie_${PLAN}_raw; SHOTS=Saved/Screenshots/WindowsEditor
PIE=0
stop() {
  [ "$PIE" = 1 ] && python Tools/Unreal/hayba_call.py editor_stop_pie '{}' | head -c 100; echo
  echo "PIE_END $(date +%T) up $(( $(date +%s) - T0 )) s"
  python Tools/Unreal/editor_lock.py release world
  rm -rf "$F"; mkdir -p "$F"
  find "$SHOTS" -name '*Shot*.png' -newer Saved/WorldShots/.piemark -exec mv {} "$F/" \;
  echo "frames $(ls $F | wc -l) -> $F"
}
python Tools/Unreal/editor_lock.py acquire world --ttl 120 --wait 1500 || exit 1
trap stop EXIT
touch Saved/WorldShots/.piemark
T0=$(date +%s); PIE=1
echo "PIE_START $(date +%T)"
python Tools/Unreal/hayba_call.py editor_start_pie '{}' | head -c 120; echo
for i in $(seq 1 20); do python Tools/Unreal/hayba_call.py editor_pie_actor_list '{}' >/dev/null 2>&1 && break; sleep 0.5; done
sleep 2
rm -f Saved/WorldShots/pie_$PLAN.json
timeout 25 python Tools/Unreal/integration/run_read.py Tools/Splats/pie_ambience.py WA_PLAN=$PLAN WA_CAP=$(( 55 - ($(date +%s) - T0) )) 2>&1 | tail -1
until [ -f Saved/WorldShots/pie_$PLAN.json ] || [ $(( $(date +%s) - T0 )) -ge 58 ]; do sleep 1; done
python - <<PY
import json
for e in json.load(open('P:/FoA/Saved/WorldShots/pie_$PLAN.json')):
    if e['kind'] != 'shot' or len(e) > 4:
        print(e)
PY
