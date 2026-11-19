#!/usr/bin/env bash
# atmosphere lane: push pp_face_blur.hlsl into M_PP_FaceBlur safely (editor-rules 9): take it off PP_DreamMono, set
# the Custom node's code, validate, compile, save, put it back, save the level. One lease, released on every exit.
#   bash Tools/Unreal/face/apply_face_blur_code.sh
set -u
cd /p/FoA
export HAYBA_AGENT_ID=atmosphere FOA_AGENT=atmosphere MSYS_NO_PATHCONV=1
M=/Game/FoA/PostProcess/FaceBlur/M_PP_FaceBlur
OFF=0
cleanup() {
  [ "$OFF" = 1 ] && FOA_AREAS=PostProcess FOA_ACTORS=PP_DreamMono python Tools/Unreal/ue_remote.py Tools/Unreal/face/swap_face_blendable.py FOA_ACTORS=PP_DreamMono | grep -E "before|after|FOA_"
  python Tools/Unreal/editor_lock.py release atmosphere
  python Tools/Unreal/editor_lock.py save_level atmosphere
}
trap cleanup EXIT
python Tools/Unreal/face/build_face_blur.py code
python Tools/Unreal/editor_lock.py acquire atmosphere --areas PostProcess --assets $M --actors PP_DreamMono --ttl 300 || exit 1
FOA_AREAS=PostProcess FOA_ACTORS=PP_DreamMono python Tools/Unreal/ue_remote.py Tools/Unreal/face/swap_face_blendable.py FOA_OFF=1 FOA_ACTORS=PP_DreamMono | grep -E "before|after"
OFF=1
python Tools/Unreal/hayba_call.py --batch Saved/FaceShots/face_blur_code.jsonl > Saved/QA/atmosphere/face_blur_code_result.json
python -c "
import json,re
t=open('Saved/QA/atmosphere/face_blur_code_result.json').read()
print(t[-1500:])
"
if grep -q '"has_errors": true' Saved/QA/atmosphere/face_blur_code_result.json; then
  echo "COMPILE ERRORS: rolling back to the previous code"
  python Tools/Unreal/hayba_call.py --batch Saved/QA/atmosphere/face_blur_rollback.jsonl | tail -3
  exit 1
fi
FOA_AREAS=PostProcess python Tools/Unreal/ue_remote.py Tools/Unreal/save_assets.py FOA_ASSETS=$M | grep FOA_SAVE
