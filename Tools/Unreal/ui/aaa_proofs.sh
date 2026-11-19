#!/usr/bin/env bash
# ui lane, AAA pass proof chain. One PIE burst per window (the sweeps wait for :x0-:x2 themselves).
#   bash Tools/Unreal/ui/aaa_proofs.sh [steps...]   default: graphs hud menufast inputfast perffast
# Stops before each step while a maintenance hold (user playtest, restart) is up or someone is in PIE.
set -u
cd /p/FoA
export FOA_AGENT=ui HAYBA_AGENT_ID=ui MSYS_NO_PATHCONV=1
D=Saved/UIShots/aaa
STEPS=${*:-graphs hud menufast inputfast perffast}
idle() {
  until ! python Tools/Unreal/editor_lock.py status 2>&1 | grep -q "MAINTENANCE" \
        && python Tools/Unreal/hayba_call.py editor_get_state '{}' 2>/dev/null | grep -q '"pie_running": false'; do sleep 10; done
}
for s in $STEPS; do
  idle
  echo "$(date +%T) step $s"
  case $s in
    graphs)
      timeout 60 python Tools/Unreal/ue_remote.py Tools/Unreal/ui/capture_aaa_graphs.py FOA_AREAS=UI FOA_STEP=capture | tail -1
      for i in $(seq 1 15); do [ -f Saved/GraphShots/aaa_wbp_pause_eventgraph.png ] && break; sleep 2; done
      sleep 3
      timeout 60 python Tools/Unreal/ue_remote.py Tools/Unreal/ui/capture_aaa_graphs.py FOA_AREAS=UI FOA_STEP=close | tail -1 ;;
    fast)
      python Tools/Unreal/ui/sweep_intro.py P:/FoA/$D/rec_fast_r4 fast > $D/rec_fast_r4.log 2>&1
      python Tools/Unreal/ui/analyze_sweep.py $D/rec_fast_r4 >> $D/rec_fast_r4.log 2>&1
      python Tools/Unreal/ui/qa_frames.py $D/rec_fast_r4 > $D/rec_fast_r4_qa.txt 2>&1 ;;
    hud)
      python Tools/Unreal/ui/sweep_intro.py P:/FoA/$D/rec_hud_r1 hud > $D/rec_hud_r1.log 2>&1
      python Tools/QA/foa_qa.py logs > $D/rec_hud_r1_qalogs.txt 2>&1
      python Tools/Unreal/ui/analyze_sweep.py $D/rec_hud_r1 >> $D/rec_hud_r1.log 2>&1
      python Tools/Unreal/ui/focus_sheet.py $D/rec_hud_r1 >> $D/rec_hud_r1.log 2>&1 ;;
    menufast|inputfast)
      python Tools/Unreal/ui/sweep_intro.py P:/FoA/$D/sweep_$s $s > $D/sweep_$s.log 2>&1
      python Tools/QA/foa_qa.py logs > $D/sweep_${s}_qalogs.txt 2>&1
      python Tools/Unreal/ui/analyze_sweep.py $D/sweep_$s >> $D/sweep_$s.log 2>&1
      python Tools/Unreal/ui/focus_sheet.py $D/sweep_$s >> $D/sweep_$s.log 2>&1 ;;
    perffast)
      python Tools/Unreal/ui/sweep_intro.py P:/FoA/$D/perf_after perffast > $D/perf_after.log 2>&1
      python Tools/Unreal/ui/perf_spikes.py $D/perf_after >> $D/perf_after.log 2>&1 ;;
  esac
  echo "$(date +%T) done $s"
done
echo all-done
