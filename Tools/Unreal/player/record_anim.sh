#!/usr/bin/env bash
# Anim lane: one EXCLUSIVE PIE burst (60 s cap, in a PIE window) proving the player animation in the game viewport.
#   bash Tools/Unreal/player/record_anim.sh [tag] [KEY=VALUE ...]   (e.g. FOA_PLAN=idle FOA_IDLE=30)
# Outputs in Saved/AnimShots/<tag>_*: still_back.png, still_front.png, loco.gif (12 s), interact.gif, idle.gif, plus
# frames_<tag>/ and the QA log scans before/after (qa_before.txt / qa_after.txt).
# FOA_PIE_SCRIPT=<path> runs another proof script (e.g. pie_screwdriver.py); every logged phase gets its own GIF.
set -u
cd /p/FoA
export FOA_AGENT=anim HAYBA_AGENT_ID=anim MSYS_NO_PATHCONV=1 FOA_EXCLUSIVE=1
TAG=${1:-proof}
shift || true
EXTRA=("$@")  # KEY=VALUE for anim_pie.py, e.g. FOA_PLAN=idle FOA_IDLE=30
OUT=Saved/AnimShots; SHOTS=Saved/Screenshots/WindowsEditor; LOG=Saved/Logs/FoA.log
# ue_remote renews our hold to 900 s; pull it straight back to 70 s so a crashed burst never blocks the others for long
R() { python Tools/Unreal/ue_remote.py "$@" 2>&1 | grep -v '^\s*$' | tail -1; python Tools/Unreal/editor_lock.py renew anim --ttl 70 > /dev/null 2>&1; }
# 2026-11-10 16:53: a driver that outlived its burst woke up inside world's PIE. Only self-guarding drivers run here:
# proof_guard.arm / live / done (they stand down when their own PIE ends and never act in anyone else's).
DRIVER=${FOA_PIE_SCRIPT:-Tools/Unreal/player/anim_pie.py}
grep -q "proof_guard" "$DRIVER" || { echo "refusing $DRIVER: it does not use proof_guard (Tools/Unreal/player/proof_guard.py)"; exit 1; }
mkdir -p "$OUT" "$SHOTS"
python Tools/QA/foa_qa.py logs > "$OUT/${TAG}_qa_before.txt" 2>&1
STARTED=0
cleanup() {
    if [ "$STARTED" -eq 1 ] && python Tools/Unreal/editor_lock.py status | grep -qi '^anim: exclusive'; then
        R Tools/Unreal/ui/pie_call.py FOA_CALL=END
    fi
    python Tools/Unreal/editor_lock.py release anim
}
trap cleanup EXIT
trap 'exit 1' TERM INT HUP
python Tools/Unreal/editor_lock.py acquire anim --ttl 60 --wait 900 || { echo "no lease"; exit 1; }
R Tools/QA/preflight_blueprints.py
python -c "import json; assert json.load(open('Saved/QA/preflight.json'))['ok'], 'Blueprint preflight failed'" || exit 1
touch "$OUT/.mark_$TAG"
DONE0=$(grep -a -c "\[anim\] done" "$LOG")
T0=$(date +%s)
R Tools/Unreal/ui/pie_call.py FOA_CALL=BEGIN
STARTED=1
sleep 3
OUTP=$(R "${FOA_PIE_SCRIPT:-Tools/Unreal/player/anim_pie.py}" "${EXTRA[@]}"); echo "$OUTP"
# EXCLUSIVE holds stay under 60 s (editor-rules): cap the burst at 45 s, and stop at once if the proof script failed
case "$OUTP" in *RuntimeError*) echo "proof script failed: ending PIE now";; *)
HEARTBEAT=$(date +%s)
until [ "$(grep -a -c "\[anim\] done" "$LOG")" -gt "$DONE0" ] || [ $(( $(date +%s) - T0 )) -ge 45 ]; do
    sleep 1
    if [ $(( $(date +%s) - HEARTBEAT )) -ge 20 ]; then
        python Tools/Unreal/editor_lock.py status | grep -qi '^anim: exclusive' || { echo 'lost EXCLUSIVE'; exit 1; }
        python Tools/Unreal/editor_lock.py renew anim --ttl 70 || exit 1
        HEARTBEAT=$(date +%s)
    fi
done;; esac
python Tools/Unreal/editor_lock.py status | grep -qi '^anim: exclusive' || { echo 'lost EXCLUSIVE'; exit 1; }
R Tools/Unreal/ui/pie_call.py FOA_CALL=END
STARTED=0
echo "pie burst $(( $(date +%s) - T0 )) s"
sleep 2
touch "$OUT/.end_$TAG"
python Tools/Unreal/editor_lock.py release anim
grep -a "\[anim\]" "$LOG" | tail -150 | sed 's/^.*\[anim\]/[anim]/' > "$OUT/${TAG}_events.txt"
cat "$OUT/${TAG}_events.txt"
mkdir -p "$OUT/frames_$TAG"
find "$SHOTS" -name 'ScreenShot*.png' -newer "$OUT/.mark_$TAG" ! -newer "$OUT/.end_$TAG" -exec mv {} "$OUT/frames_$TAG/" \;
python Tools/QA/foa_qa.py logs > "$OUT/${TAG}_qa_after.txt" 2>&1
if [ "$DRIVER" = 'Tools/Unreal/player/anim_pie.py' ]; then
    python Tools/Unreal/player/anim_gifs.py "$OUT" "$TAG"
fi
