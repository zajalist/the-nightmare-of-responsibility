#!/usr/bin/env bash
# Recompile the LIVE face blur safely (editor-rules 9): take M_PP_FaceBlur off PP_DreamMono, push the graph/HLSL and
# compile; on a failed compile roll back to the last good shader (v8) and compile that; put it back; save the level.
#   bash Tools/Unreal/face/recompile_live.sh [code|v10]   (default code). Waits while any PIE runs.
set -u
cd /p/FoA
export FOA_AGENT=face HAYBA_AGENT_ID=face MSYS_NO_PATHCONV=1
PHASE=${1:-code}
while python Tools/Unreal/hayba_call.py editor_get_state '{}' | grep -q '"pie_running": true'; do sleep 10; done
FOA_ACTORS=PP_DreamMono timeout 900 python Tools/Unreal/ue_remote.py Tools/Unreal/face/swap_face_blendable.py FOA_ACTORS=PP_DreamMono FOA_OFF=1 2>&1 | grep -E "^(before|after)|Error|Traceback"
python Tools/Unreal/face/build_face_blur.py "$PHASE" && python Tools/Unreal/face/build_face_blur.py rollback || exit 1
compile() {  # $1 = batch phase; prints compile clean True/False
  python Tools/Unreal/editor_lock.py acquire face --assets /Game/FoA/PostProcess/FaceBlur/M_PP_FaceBlur --ttl 120 --wait 300 >/dev/null
  python Tools/Unreal/hayba_call.py --batch "Saved/FaceShots/face_blur_$1.jsonl" --keep-going > Saved/FaceShots/.compile.jsonl
  python Tools/Unreal/editor_lock.py release face >/dev/null
  python -c "
import json
rows = [json.loads(l) for l in open('Saved/FaceShots/.compile.jsonl')]
bad = [r['cmd'] for r in rows if not r['response'].get('ok')]
c = rows[-1]['response'].get('data', {})
print('compile', '$1', c.get('compiled_clean'), c.get('errors'), 'failed calls', bad)
raise SystemExit(0 if c.get('compiled_clean') else 1)"
}
if ! compile "$PHASE"; then
  echo "rolling back to v8"
  compile rollback || { echo "ROLLBACK FAILED: M_PP_FaceBlur left off the volume"; exit 1; }
fi
FOA_ACTORS=PP_DreamMono timeout 900 python Tools/Unreal/ue_remote.py Tools/Unreal/face/swap_face_blendable.py FOA_ACTORS=PP_DreamMono 2>&1 | grep -E "^(before|after)|Error|Traceback"
timeout 600 python Tools/Unreal/editor_lock.py save_level face
