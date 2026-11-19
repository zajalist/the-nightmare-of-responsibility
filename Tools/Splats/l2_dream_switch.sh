#!/usr/bin/env bash
# Map switch for the Level 2 test map, the reference for docs/agents/editor-rules.md "Map switches" (world lane):
#   bash Tools/Splats/l2_dream_switch.sh build            open (or create) L_L2_DreamTest, fill it, save it
#   bash Tools/Splats/l2_dream_switch.sh shots '<chain>'  open it, PIE with a perf_driver chain, stop PIE
# One EXCLUSIVE hold (a PIE window, 60 s or less): refuse if the bedroom has unsaved changes or PIE runs, count the
# bedroom, open the test map, work, reopen the bedroom, check it came back whole, release. Any exit reopens the bedroom.
set -u
cd /p/FoA
export FOA_AGENT=world HAYBA_AGENT_ID=world MSYS_NO_PATHCONV=1
MODE=$1; CHAIN=${2:-}
DRIVER=${FOA_DRIVER:-C:/Users/Admin/AppData/Local/Temp/claude/47e10ba54099b5a9/f6b57ca2-9e47-4dcd-a55a-de7f221fc83c/scratchpad/perf_driver.py}
OUTD=Saved/WorldShots/perf; mkdir -p "$OUTD"
LOCK="$OUTD/.world_burst.lock"
mkdir "$LOCK" 2>/dev/null || { echo "abort: another world burst holds $LOCK"; exit 1; }
echo $$ > "$LOCK/pid"
R() { timeout 40 python Tools/Unreal/integration/run_read.py "$@" 2>&1 | grep -a "L2MAP\|Error\|perf chain" | tail -3; }
M() { R Tools/Splats/l2_dream_map.py "FOA_L2MAP=$1" "FOA_L2WORLD=${FOA_L2WORLD:-dream}"; }
state() { timeout 10 python Tools/Unreal/hayba_call.py editor_get_state '{}' 2>&1; }
SWITCHED=0; PIE=0
cleanup() {
  [ "$PIE" = 1 ] && R Tools/Unreal/ui/pie_call.py FOA_CALL=END && sleep 2
  [ "$SWITCHED" = 1 ] && M back
  python Tools/Unreal/editor_lock.py release world
  rm -rf "$LOCK"
}
trap cleanup EXIT
trap 'exit 1' TERM INT HUP
python Tools/Unreal/editor_lock.py acquire world --ttl 60 --wait 1500 || exit 1
python Tools/Unreal/editor_lock.py status 2>/dev/null | grep -q "^world: exclusive" || { echo "abort: no EXCLUSIVE"; exit 1; }
S=$(state)
echo "$S" | grep -q '"pie_running": false' || { echo "abort: PIE is running"; exit 1; }
DIRTY=$(echo "$S" | python -c "import sys,json;d=json.load(sys.stdin)['data'];print(' '.join(p for p in d['dirty_packages'] if 'L_Tutorial_Bedroom' in p or '__External' in p or '/Maps/' in p))")
[ -n "$DIRTY" ] && { echo "abort: the bedroom has unsaved changes (not ours to save or drop): $DIRTY"; exit 1; }
BEFORE=$(M count | grep "L2MAP count"); echo "before: $BEFORE"
echo "$BEFORE" | grep -q "L_Tutorial_Bedroom" || { echo "abort: the open map is not the bedroom"; exit 1; }
T0=$(date +%s)
SWITCHED=1; M open
if [ "$MODE" = build ]; then
  M build
else
  rm -f "$OUTD/${MODE}_timeline.json"; touch "$OUTD/.mark_$MODE"
  PIE=1; R Tools/Unreal/ui/pie_call.py FOA_CALL=BEGIN
  for i in 1 2 3 4 5 6 7 8; do state | grep -q '"pie_running": true' && break; sleep 1; done
  sleep 1
  R "$DRIVER" "FOA_RUN=$MODE" "FOA_CHAIN=$CHAIN"
  until [ -f "$OUTD/${MODE}_timeline.json" ] || [ $(( $(date +%s) - T0 )) -ge 40 ]; do sleep 1; done
  R Tools/Unreal/ui/pie_call.py FOA_CALL=END; sleep 2; PIE=0
fi
M back; SWITCHED=0
AFTER=$(M count | grep "L2MAP count"); echo "after:  $AFTER"
[ "$(echo "$BEFORE" | cut -d' ' -f3-)" = "$(echo "$AFTER" | cut -d' ' -f3-)" ] && echo "VERIFY OK" || echo "VERIFY FAILED"
echo "hold $(( $(date +%s) - T0 )) s"
if [ "$MODE" != build ]; then   # frames and CSV captures of this run
  F="$OUTD/${MODE}_frames"; rm -rf "$F"; mkdir -p "$F"
  find Saved/Screenshots -name '*.png' -newer "$OUTD/.mark_$MODE" -exec mv {} "$F/" \;
  find Saved/Profiling/CSV -name '*.csv' -newer "$OUTD/.mark_$MODE" -exec cp {} "$F/" \;
  ls "$F"
fi
