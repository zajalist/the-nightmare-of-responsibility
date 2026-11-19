#!/usr/bin/env bash
# T8 proof: one EXCLUSIVE PIE burst (PIE up <= 58 s, PIE window only), in game context: boot -> Wake up -> skip ->
# T7 -> ShirtTaken (the director starts the fight) -> pie_fight.py plays it in-engine (no exec round trips).
#   bash Tools/Unreal/encounter/pie_burst.sh win|lose
#   -> Saved/EncounterCaptures/fight_<mode>.json, drive_<mode>.log (MARK lines), t8_<mode>.mp4 + MARK stills (make_video)
# lose ends in BP_BeatDirector.FailDay, so it also shows the day rollover. PIE is always stopped and the lease released.
cd /p/FoA
export MSYS_NO_PATHCONV=1 FOA_AGENT=gameplay HAYBA_AGENT_ID=gameplay PYTHONUNBUFFERED=1
MODE=${1:-win}
OUT=Saved/EncounterCaptures; mkdir -p $OUT
BOOT='0.2:viewmode lit|0.3:ke * OnSplashFinished|0.6:ke * OnTitleConfirmed|0.8:ke * WakeUp|5.0:ke * SkipWakeUp|WAIT:T0:4|0.5:ke * ReportEvent WardrobeLanded|WAIT:T7:3|1.0:ke * ReportEvent ShirtTaken|WAIT:T8:3'  # no END: pie_loop's END stops PIE
D() { timeout 25 python Tools/Unreal/integration/run_read.py "$@" 2>&1 | grep -v '^\s*$' | tail -1; }
PIE=0
stop() {
  [ "$PIE" = 1 ] && python Tools/Unreal/hayba_call.py editor_stop_pie '{}' | head -c 120; echo
  echo "PIE_END $(date +%T) up $(( $(date +%s) - T0 )) s"
  python Tools/Unreal/editor_lock.py release gameplay
}
python Tools/Unreal/editor_lock.py acquire gameplay --ttl 120 --wait 1500 || exit 1
trap stop EXIT
T0=$(date +%s); PIE=1
echo "PIE_START $(date +%T)"
python Tools/Unreal/hayba_call.py editor_start_pie '{}' | head -c 200; echo
for i in $(seq 1 20); do python Tools/Unreal/hayba_call.py editor_pie_actor_list '{}' >/dev/null 2>&1 && break; sleep 0.5; done
sleep 2
rm -f Saved/Integration/t8_boot_timeline.json $OUT/fight_$MODE.json
D Tools/Unreal/integration/pie_loop.py FOA_RUN=t8_boot "FOA_CHAIN=$BOOT" FOA_SHOT=0
until [ -f Saved/Integration/t8_boot_timeline.json ] || [ $(( $(date +%s) - T0 )) -ge 28 ]; do sleep 1; done
echo "booted to T8 at $(( $(date +%s) - T0 )) s"
D Tools/Unreal/encounter/pie_fight.py FOA_MODE=$MODE FOA_SPEED=${SPEED:-4} FOA_CAP=$(( 55 - ($(date +%s) - T0) ))
until [ -f $OUT/fight_$MODE.json ] || [ $(( $(date +%s) - T0 )) -ge 57 ]; do sleep 1; done
if [ "$MODE" = lose ] && [ -f $OUT/fight_lose.json ]; then  # keep filming: FailDay, the rollover card, the new morning
  rm -f Saved/Integration/t8_rollover_timeline.json
  D Tools/Unreal/integration/pie_loop.py FOA_RUN=t8_rollover "FOA_CHAIN=9.0:ke * SkipWakeUp|WAIT:T0:6"
  until [ -f Saved/Integration/t8_rollover_timeline.json ] || [ $(( $(date +%s) - T0 )) -ge 57 ]; do sleep 1; done
  echo "rollover filmed to $(( $(date +%s) - T0 )) s"
fi
python -c "
import json,sys
d=json.load(open('$OUT/fight_$MODE.json'))
for k,v in sorted(d['marks'].items(), key=lambda kv: kv[1]): print('MARK', 0, v, k)
for e in d['log']: print(e)
print('RESULT', d['result'], 'turns', d['turns'])" > $OUT/drive_$MODE.log 2>&1
cat $OUT/drive_$MODE.log | cut -c1-240
