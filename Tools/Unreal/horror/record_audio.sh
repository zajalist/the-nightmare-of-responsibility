#!/usr/bin/env bash
# Audio lane: one sound-on PIE burst (Hayba restart 10). EXCLUSIVE only in the PIE window, 55 s cap, released on exit.
#   bash Tools/Unreal/horror/record_audio.sh <name>          driver: FOA_DRIVER (default pie_audio_beats.py)
# - Background audio: editor_set_background_audio(true) before PIE (the editor mutes everything without focus); the
#   previous value it returns is written to Saved/HorrorShots/<name>_bg.json and restored on EVERY exit path (trap).
# - Recording: audio_recording_start/stop with world "pie" (PIE has its own audio device) ->
#   Saved/BouncedWavFiles/HorrorShots/<name>_mix.wav, result (peak, silent) in Saved/HorrorShots/<name>_rec.json.
# - Sampler: sample_audio.sh logs audio_active_sounds on the PIE world every FOA_SAMPLE_S s to <name>_audio.jsonl and
#   stops when <name>_audio.stop appears.
# Outputs also: <name>_timeline.json (driver), <name>_frames/, <name>_bp_errors.csv. This script's PID: record.pid.
set -u
cd /p/FoA
export FOA_AGENT=horror HAYBA_AGENT_ID=horror MSYS_NO_PATHCONV=1
NAME=${1:-audio}
CAP=${FOA_PIE_CAP:-55}
DRIVER=${FOA_DRIVER:-Tools/Unreal/horror/pie_audio_beats.py}
SHOTS=Saved/Screenshots/WindowsEditor
H() { python Tools/Unreal/hayba_call.py "$@" 2>/dev/null; }
D() { timeout 25 python Tools/Unreal/integration/run_read.py "$@" 2>&1 | grep -v '^\s*$' | tail -1; }
mkdir -p Saved/HorrorShots "$SHOTS"
echo $$ > Saved/HorrorShots/record.pid
PIE=0
REC=0
SAMPLER=
restore_bg() {
  [ -f "Saved/HorrorShots/${NAME}_bg.json" ] || return 0
  ARGS=$(python -c "import json;p=json.load(open('Saved/HorrorShots/${NAME}_bg.json'))['previous'];print(json.dumps({'enabled':p['allow_background_audio'],'unfocused_volume_multiplier':p['unfocused_volume_multiplier']}))")
  H editor_set_background_audio "$ARGS" > "Saved/HorrorShots/${NAME}_bg_restored.json"
  python -c "import json;t=open('Saved/HorrorShots/${NAME}_bg_restored.json').read();d=json.loads(t[t.find('{'):])['data'];print('background audio restored to', d['enabled'], 'unfocused', d['unfocused_volume_multiplier'], 'verified', d.get('verified'))"
}
stop_rec() {
  [ "$REC" = 1 ] || return 0
  REC=0
  H audio_recording_stop "{\"world\":\"pie\",\"filename\":\"${NAME}_mix\",\"relative_path\":\"HorrorShots\"}" > "Saved/HorrorShots/${NAME}_rec.json"
  python -c "import json;t=open('Saved/HorrorShots/${NAME}_rec.json').read();d=json.loads(t[t.find('{'):]);d=d.get('data',d);print('recording', {k:d.get(k) for k in ('wav_path','duration_seconds','peak','peak_dbfs','silent','error')})"
}
cleanup() {
  touch "Saved/HorrorShots/${NAME}_audio.stop"
  stop_rec
  [ "$PIE" = 1 ] && D Tools/Unreal/ui/pie_call.py FOA_CALL=END
  restore_bg
  python Tools/Unreal/editor_lock.py release horror
  rm -f Saved/HorrorShots/record.pid
}
trap cleanup EXIT
trap 'exit 1' TERM INT HUP
python Tools/Unreal/editor_lock.py acquire horror --ttl 120 --wait 1500 > Saved/HorrorShots/.acquire.txt 2>&1
cat Saved/HorrorShots/.acquire.txt
grep -q "old exclusive lock" Saved/HorrorShots/.acquire.txt && { echo "abort: Hayba leases not answering"; exit 1; }
python Tools/Unreal/editor_lock.py status 2>/dev/null | grep -q "^horror: exclusive" || { echo "abort: no EXCLUSIVE"; exit 1; }
H editor_set_background_audio '{"enabled":true}' > "Saved/HorrorShots/${NAME}_bg.json.tmp"
python -c "import json;t=open('Saved/HorrorShots/${NAME}_bg.json.tmp').read();d=json.loads(t[t.find('{'):])['data'];json.dump(d,open('Saved/HorrorShots/${NAME}_bg.json','w'));print('background audio on; previous', d['previous'])"
touch Saved/HorrorShots/.shotmark
rm -f "Saved/HorrorShots/${NAME}_timeline.json"
SINCE=$(date -u +%H.%M.%S)
T0=$(date +%s)
PIE=1
D Tools/Unreal/ui/pie_call.py FOA_CALL=BEGIN
sleep 4
bash Tools/Unreal/horror/sample_audio.sh "$NAME" "${FOA_SAMPLE_S:-1.2}" &
SAMPLER=$!
H audio_recording_start '{"world":"pie","expected_duration":60}' | grep -o '"recording_state": "[a-z]*"'
python -c "import time;print(time.time())" > "Saved/HorrorShots/${NAME}_recstart.txt"
REC=1
D "$DRIVER" "FOA_RUN=$NAME"
until [ -f "Saved/HorrorShots/${NAME}_timeline.json" ] || [ $(( $(date +%s) - T0 )) -ge "$CAP" ]; do sleep 1; done
touch "Saved/HorrorShots/${NAME}_audio.stop"
stop_rec
D Tools/Unreal/ui/pie_call.py FOA_CALL=END
PIE=0
restore_bg
rm -f "Saved/HorrorShots/${NAME}_bg.json"
python Tools/Unreal/editor_lock.py release horror
echo "pie burst $(( $(date +%s) - T0 )) s"
sleep 2
F=Saved/HorrorShots/${NAME}_frames; rm -rf "$F"; mkdir -p "$F"
find "$SHOTS" -name 'ScreenShot*.png' -newer Saved/HorrorShots/.shotmark -exec mv {} "$F/" \;
echo "frames $(ls "$F" | wc -l) -> $F"
python Tools/Unreal/integration/bp_errors.py --since "$SINCE" --csv "Saved/HorrorShots/${NAME}_bp_errors.csv" | sed -n '/--- by/,$p'
echo "since $SINCE done"
