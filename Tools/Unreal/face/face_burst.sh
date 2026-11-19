#!/usr/bin/env bash
# Face lane: one PIE burst under the Hayba EXCLUSIVE lease (granted only in the PIE window, minutes :x0-:x2), 60 s cap.
#   bash Tools/Unreal/face/face_burst.sh <run> play|cine [KEY=VALUE ...]   (FOA_DRIVER=<script> swaps the PIE driver)
# Steps inside the burst go through run_read.py (no second lease). Settings.sav is restored afterwards.
# Waits instead of starting while the user plays PIE. Outputs: Saved/FaceShots/<run>/ (pie_face_shots.py).
set -u
cd /p/FoA
export FOA_AGENT=face HAYBA_AGENT_ID=face MSYS_NO_PATHCONV=1
RUN=${1:?run name}; MODE=${2:-play}; shift 2 || true
CAP=${FOA_PIE_CAP:-56}
DRV=${FOA_DRIVER:-Tools/Unreal/face/pie_face_shots.py}
echo $$ > Saved/FaceShots/.burst.pid  # root PID: stop this chain with taskkill /T /F /PID <it>, nothing by name
D() { timeout 25 python Tools/Unreal/integration/run_read.py "$@" 2>&1 | grep -v '^\s*$' | tail -2; }
pie() { python Tools/Unreal/hayba_call.py editor_get_state '{}' 2>/dev/null | grep -q '"pie_running": true'; }
while pie; do echo "user is playing PIE; waiting"; sleep 15; done
PREF=Saved/SaveGames/Settings.sav; BAK=Saved/FaceShots/.settings.sav.bak
[ -f "$PREF" ] && cp "$PREF" "$BAK"
PIE=0
cleanup() {
  [ "$PIE" = 1 ] && D Tools/Unreal/ui/pie_call.py FOA_CALL=END
  python Tools/Unreal/editor_lock.py release face
  if [ -f "$BAK" ]; then cp "$BAK" "$PREF"; rm -f "$BAK"; fi
}
trap cleanup EXIT
trap 'exit 1' TERM INT HUP
python Tools/Unreal/editor_lock.py acquire face --ttl 75 --wait 1500 > Saved/FaceShots/.acquire.txt 2>&1
cat Saved/FaceShots/.acquire.txt
python Tools/Unreal/editor_lock.py status 2>/dev/null | grep -q "^face: exclusive" || { echo "abort: no EXCLUSIVE"; exit 1; }
for i in 1 2 3 4 5 6 7 8; do pie || break; sleep 3; done  # a previous holder may still be ending its PIE
pie && { echo "abort: PIE started by someone else"; exit 1; }
rm -f "Saved/FaceShots/$RUN/shots.json"
T0=$(date +%s)
PIE=1
D Tools/Unreal/ui/pie_call.py FOA_CALL=BEGIN
sleep 4
pie || { PIE=0; echo "abort: PIE did not start"; exit 1; }  # refused (e.g. a Blueprint failing to compile): free the window now
D "$DRV" "FOA_RUN=$RUN" "FOA_MODE=$MODE" "$@"
until [ -f "Saved/FaceShots/$RUN/shots.json" ] || [ $(( $(date +%s) - T0 )) -ge "$CAP" ]; do sleep 1; done
D Tools/Unreal/ui/pie_call.py FOA_CALL=END
PIE=0
python Tools/Unreal/editor_lock.py release face
echo "pie burst $(( $(date +%s) - T0 )) s"
sleep 2
ls "Saved/FaceShots/$RUN" | wc -l
python -c "import json;d=json.load(open('Saved/FaceShots/$RUN/shots.json'));print(d['reason'],len(d['shots']),'shots');print(d['error'] or '')" 2>&1 | tail -15
