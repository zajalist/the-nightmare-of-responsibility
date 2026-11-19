#!/usr/bin/env bash
# story lane (copy of Tools/Unreal/gameplay/record_loop.sh under the story lease owner): one recorded PIE burst of the loop, 60 s wall clock at most, under the Hayba EXCLUSIVE lease
#   bash Tools/Unreal/flow/record_story.sh <name> [chain]
# Every step inside the burst (BEGIN, the driver, END) runs through run_read.py, which never requests a lease, so a
# step can't queue for a second EXCLUSIVE mid-burst. If the acquire falls back to the old file lock (Hayba not
# answering) the burst aborts instead of running. END is also in the exit trap.
# Frames come from in-engine 'Shot showui' requests (pie_loop.py, FOA_SHOT), so window focus doesn't matter.
# Outputs: Saved/Devlog/story_<name>.mp4, Saved/Integration/<name>_timeline.json (beats, state every 2 s,
# commands, misses), Saved/StoryShots/<name>_bp_errors.csv (Blueprint errors logged during the burst).
# Progress goes to GI_FoA's QA slot (proof_isolate.py), never the player's save.
# This script's PID goes to Saved/StoryShots/record_story.pid: stop only that PID, never anything matched by name.
set -u
cd /p/FoA
export FOA_AGENT=story HAYBA_AGENT_ID=story MSYS_NO_PATHCONV=1
NAME=${1:-loop}
CHAIN=${2:-}
CAP=${FOA_PIE_CAP:-55}
SHOTS=Saved/Screenshots/WindowsEditor
D() { timeout 25 python Tools/Unreal/integration/run_read.py "$@" 2>&1 | grep -v '^\s*$' | tail -1; }
mkdir -p Saved/Devlog Saved/Integration Saved/StoryShots "$SHOTS"
echo $$ > Saved/StoryShots/record_story.pid
PIE=0
cleanup() {
  [ "$PIE" = 1 ] && D Tools/Unreal/flow/proof_isolate.py FOA_PROOF=restore
  [ "$PIE" = 1 ] && D Tools/Unreal/ui/pie_call.py FOA_CALL=END
  python Tools/Unreal/editor_lock.py release story
  rm -f Saved/StoryShots/record_story.pid
}
trap cleanup EXIT
trap 'exit 1' TERM INT HUP
python Tools/Unreal/editor_lock.py acquire story --ttl 120 --wait 1500 > Saved/StoryShots/.acquire.txt 2>&1
cat Saved/StoryShots/.acquire.txt
grep -q "old exclusive lock" Saved/StoryShots/.acquire.txt && { echo "abort: Hayba leases not answering"; exit 1; }
python Tools/Unreal/editor_lock.py status 2>/dev/null | grep -q "^story: exclusive" || { echo "abort: no EXCLUSIVE"; exit 1; }
touch Saved/StoryShots/.shotmark
rm -f "Saved/Integration/${NAME}_timeline.json"
SINCE=$(date -u +%H.%M.%S)
T0=$(date +%s)
PIE=1
D Tools/Unreal/ui/pie_call.py FOA_CALL=BEGIN
sleep 4
D Tools/Unreal/flow/proof_isolate.py FOA_PROOF=isolate  # the player's save stays untouched (main's rule 2026-11-10)
if [ -n "$CHAIN" ]; then D Tools/Unreal/integration/pie_loop.py "FOA_RUN=$NAME" "FOA_CHAIN=$CHAIN" "FOA_SHOT=${FOA_SHOT:-0.25}"
else D Tools/Unreal/integration/pie_loop.py "FOA_RUN=$NAME" "FOA_SHOT=${FOA_SHOT:-0.25}"; fi
until [ -f "Saved/Integration/${NAME}_timeline.json" ] || [ $(( $(date +%s) - T0 )) -ge "$CAP" ]; do sleep 1; done
D Tools/Unreal/ui/pie_call.py FOA_CALL=END
PIE=0
python Tools/Unreal/editor_lock.py release story
echo "pie burst $(( $(date +%s) - T0 )) s"
sleep 2
F=Saved/StoryShots/${NAME}_frames; rm -rf "$F"; mkdir -p "$F"
find "$SHOTS" -name 'ScreenShot*.png' -newer Saved/StoryShots/.shotmark -exec mv {} "$F/" \;
python - "$F" "Saved/Devlog/story_${NAME}.mp4" <<'PY'
import glob, os, subprocess, sys
src, dst = sys.argv[1], sys.argv[2]
fs = sorted(glob.glob(f'{src}/*.png'), key=os.path.getmtime)
if not fs:
    sys.exit('no frames')
ts = [os.path.getmtime(f) for f in fs]
with open(f'{src}/list.txt', 'w') as fh:  # each frame holds until the next one landed: real time
    for i, f in enumerate(fs):
        d = (ts[i + 1] - ts[i]) if i + 1 < len(fs) else 0.5
        fh.write(f"file '{os.path.basename(f)}'\nduration {max(d, 0.02):.3f}\n")
    fh.write(f"file '{os.path.basename(fs[-1])}'\n")
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{src}/list.txt', '-vf',
                'scale=trunc(iw/2)*2:trunc(ih/2)*2,framerate=30,format=yuv420p', '-c:v', 'libx264', '-crf', '20',
                '-movflags', '+faststart', dst], check=True)
print('frames', len(fs), 'span', round(ts[-1] - ts[0], 1), 's ->', dst)
PY
python Tools/Unreal/integration/beat_report.py "Saved/Integration/${NAME}_timeline.json"
python Tools/Unreal/integration/bp_errors.py --since "$SINCE" --csv "Saved/StoryShots/${NAME}_bp_errors.csv" | sed -n '/--- by/,$p'
echo "since $SINCE done"
