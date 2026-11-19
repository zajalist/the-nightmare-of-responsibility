#!/usr/bin/env bash
# ui lane: the phone proof (first-person stills: lock, list, Mom's message, notes; the raise at 30 fps), one PIE burst.
#   bash Tools/Unreal/ui/aaa_phone_proof.sh [run name]   default rec_phone_r1
set -u
cd /p/FoA
export FOA_AGENT=ui HAYBA_AGENT_ID=ui MSYS_NO_PATHCONV=1
D=Saved/UIShots/aaa
R=${1:-rec_phone_r1}
until ! python Tools/Unreal/editor_lock.py status 2>&1 | grep -q "MAINTENANCE" \
      && python Tools/Unreal/hayba_call.py editor_get_state '{}' 2>/dev/null | grep -q '"pie_running": false'; do sleep 10; done
python Tools/Unreal/ui/sweep_intro.py P:/FoA/$D/$R phone > $D/$R.log 2>&1
python Tools/QA/foa_qa.py logs > $D/${R}_qalogs.txt 2>&1
python Tools/Unreal/ui/analyze_sweep.py $D/$R >> $D/$R.log 2>&1
python Tools/Unreal/ui/focus_sheet.py $D/$R >> $D/$R.log 2>&1
python Tools/Unreal/ui/qa_phone_raise.py $D/$R > $D/${R}_raise_qa.txt 2>&1  # letterbox, smear, readable at rest
echo done-phone >> $D/$R.log
