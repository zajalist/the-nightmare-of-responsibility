#!/usr/bin/env bash
# Logs Hayba audio_active_sounds (name, class, volume) every ~1.5 s to Saved/HorrorShots/<name>_audio.jsonl until killed.
# Started by record_audio.sh; stops when Saved/HorrorShots/<name>_audio.stop appears (a bash PID kill left an orphan in au9).
cd /p/FoA
export MSYS_NO_PATHCONV=1
OUT=Saved/HorrorShots/${1:-audio}_audio.jsonl
: > "$OUT"
rm -f "Saved/HorrorShots/${1:-audio}_audio.stop"
while [ ! -f "Saved/HorrorShots/${1:-audio}_audio.stop" ]; do
  python Tools/Unreal/hayba_call.py audio_active_sounds '{"limit":64,"world":"pie"}' 2>/dev/null | python -c "
import json,sys,time
t=sys.stdin.read()
try:
    d=json.loads(t[t.find('{'):]); d=d.get('data',d)
except Exception:
    sys.exit()
names=[(s.get('sound_path') or '').split('.')[-1] + '@' + str(s.get('owner')) + '#' + str(s.get('instance_id')) + ('' if s.get('playing_audio', True) and not s.get('paused') else '!') for s in d.get('sounds',[])]
print(json.dumps({'epoch':round(time.time(),2),'count':d.get('active_sound_count'),'voices':d.get('active_voice_count'),'sounds':names}))" >> "$OUT"
  sleep ${2:-1.2}
done
