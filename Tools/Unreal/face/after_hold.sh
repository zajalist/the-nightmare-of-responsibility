#!/usr/bin/env bash
# Face lane: the staged editor steps, each in its own short declared run (no PIE): polo reimport, skin pass 2,
# blur compile. Stops at the first failure.
set -eu
cd /p/FoA
export FOA_AGENT=face HAYBA_AGENT_ID=face MSYS_NO_PATHCONV=1
python Tools/Unreal/hayba_call.py editor_get_state '{}' | grep -q '"pie_running": false' || { echo "PIE running: wait"; exit 1; }
timeout 110 python Tools/Unreal/ue_remote.py Tools/MPFB/ue_reimport_cm.py FOA_AREAS=Characters FOA_PIECE=Polo \
  FOA_SOURCE=P:/FoA-Assets/character/mpfb/export/teen_polo_drape/SK_Teen_Polo.fbx FOA_PRESERVE_REFERENCE=1 2>&1 | grep -E "TEEN_CM_PASS|Error|Traceback" | cut -c1-300
python Tools/Unreal/editor_lock.py acquire face --assets /Game/FoA/Characters/Teen/Materials --ttl 120 --wait 120
timeout 100 python Tools/Unreal/face/tune_teen_skin.py 2>&1 | tail -2 | cut -c1-300 || true
python Tools/Unreal/editor_lock.py release face
python Tools/Unreal/face/build_face_blur.py code
python Tools/Unreal/editor_lock.py acquire face --assets /Game/FoA/PostProcess/FaceBlur/M_PP_FaceBlur --ttl 120 --wait 120
python Tools/Unreal/hayba_call.py --batch Saved/FaceShots/face_blur_code.jsonl 2>&1 | python -c "
import sys, json
for l in sys.stdin:
    d = json.loads(l); r = d['response']; print(d['cmd'], r.get('ok'), json.dumps(r.get('data', {}))[:160])"
python Tools/Unreal/editor_lock.py release face
