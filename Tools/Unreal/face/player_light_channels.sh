#!/usr/bin/env bash
# Apply player_light_channels.py under a narrow lease on BP_FoAPlayer, compile (must be clean: 0 errors, 0 warnings),
# revert and recompile on any failure, then save. Never leaves the Blueprint failing to compile in memory.
#   bash Tools/Unreal/face/player_light_channels.sh
set -u
cd /p/FoA
export FOA_AGENT=face HAYBA_AGENT_ID=face MSYS_NO_PATHCONV=1
BP=/Game/FoA/Characters/Player/BP_FoAPlayer
H() { python Tools/Unreal/hayba_call.py "$@"; }
python Tools/Unreal/hayba_call.py editor_get_state '{}' | grep -q '"pie_running": true' && { echo "PIE running: not now"; exit 1; }
python Tools/Unreal/editor_lock.py acquire face --assets $BP --ttl 120 --wait 600 || exit 1
H editor_get_state '{}' | python -c "import json,sys; d=json.load(sys.stdin)['data']; assert '$BP' not in d['dirty_packages'], 'BP_FoAPlayer has unsaved edits by someone else'" || { python Tools/Unreal/editor_lock.py release face; exit 1; }
compile() { H blueprint_compile "{\"path\":\"$BP\"}" | python -c "
import json,sys; r=json.load(sys.stdin); d=r.get('data',{}); print('compile', r.get('ok'), d.get('compiled'), 'errors', d.get('errors'), 'warnings', d.get('warnings'))
raise SystemExit(0 if r.get('ok') and d.get('compiled') and not d.get('errors') and not d.get('warnings') else 1)"; }
compile || { echo "BP_FoAPlayer does not compile clean BEFORE any change: stopping"; python Tools/Unreal/editor_lock.py release face; exit 1; }
timeout 60 python Tools/Unreal/ue_remote.py Tools/Unreal/face/player_light_channels.py 2>&1 | grep -E "FOA_CHANNELS|Error|Traceback|Assert"
if compile; then
  H asset_save "{\"asset_paths\":[\"$BP\"]}" | python -c "import json,sys; d=json.load(sys.stdin)['data']; print('saved', d.get('saved'), d.get('failed'))"
else
  echo "compile not clean: reverting the channels"
  timeout 60 python Tools/Unreal/ue_remote.py Tools/Unreal/face/player_light_channels.py FOA_OP=revert 2>&1 | grep -E "FOA_CHANNELS|Error"
  compile
fi
python Tools/Unreal/editor_lock.py release face
