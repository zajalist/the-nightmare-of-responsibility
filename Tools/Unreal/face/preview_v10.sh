#!/usr/bin/env bash
# Preview the face blur v10 without touching the live one: build TMP_face_FaceBlurV10 (a copy of the M_PP_FaceBlur
# graph with the v10 HLSL; on a failed compile it gets the v8 code so nothing is left failing), then one PIE burst
# that shoots each view with v8 (live) and v10 (swapped in on the PIE volume copy only), the v10 mask and the clean
# frame. Waits while anyone plays PIE.   bash Tools/Unreal/face/preview_v10.sh [run [KEY=VALUE ...]]
set -u
cd /p/FoA
export FOA_AGENT=face HAYBA_AGENT_ID=face MSYS_NO_PATHCONV=1
TMP=/Game/FoA/PostProcess/FaceBlur/TMP_face_FaceBlurV10
while python Tools/Unreal/hayba_call.py editor_get_state '{}' | grep -q '"pie_running": true'; do sleep 15; done
if [ ! -f Content/FoA/PostProcess/FaceBlur/TMP_face_FaceBlurV10.uasset ]; then
  FOA_MAT=$TMP python Tools/Unreal/face/build_face_blur.py create
  B=Saved/FaceShots/face_blur_create_TMP_face_FaceBlurV10.jsonl
else
  FOA_MAT=$TMP python Tools/Unreal/face/build_face_blur.py code
  B=Saved/FaceShots/face_blur_code_TMP_face_FaceBlurV10.jsonl
fi
python Tools/Unreal/editor_lock.py acquire face --assets $TMP --ttl 120 --wait 600 >/dev/null
python Tools/Unreal/hayba_call.py --batch "$B" --keep-going > Saved/FaceShots/.preview_compile.jsonl
OK=$(python -c "
import json
rows = [json.loads(l) for l in open('Saved/FaceShots/.preview_compile.jsonl')]
c = rows[-1]['response'].get('data', {})
print('1' if c.get('compiled_clean') else '0', c.get('errors'), [r['cmd'] for r in rows if not r['response'].get('ok')], file=__import__('sys').stderr)
print('1' if c.get('compiled_clean') else '0')")
if [ "$OK" != "1" ]; then
  echo "v10 compile FAILED: putting the v8 code on the preview copy so nothing is left failing"
  FOA_MAT=$TMP python Tools/Unreal/face/build_face_blur.py rollback
  python Tools/Unreal/hayba_call.py --batch Saved/FaceShots/face_blur_rollback_TMP_face_FaceBlurV10.jsonl --keep-going | tail -1 | cut -c1-200
  python Tools/Unreal/editor_lock.py release face >/dev/null
  exit 1
fi
python Tools/Unreal/editor_lock.py release face >/dev/null
echo "v10 preview compiled clean"
RUN=${1:-v10_ab}  # the live material is shot as v8_<view>, the preview as v10_<view>
bash Tools/Unreal/face/face_burst.sh "$RUN" ab "${@:2}" > "Saved/FaceShots/.$RUN.log" 2>&1
tail -3 "Saved/FaceShots/.$RUN.log"
