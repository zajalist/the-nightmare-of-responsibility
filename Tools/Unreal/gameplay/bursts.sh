#!/usr/bin/env bash
# Integration bursts in consecutive PIE windows (each <= 55 s of PIE), with the QA log check before and after:
#   A  boot -> menu -> Wake up -> (skip the wake-up) -> T0 ... T7
#   B  boot -> T0 -> T7 -> T8 -> T9 -> T10 -> walk out -> FailDay -> new morning (skip) -> pause -> quit to title
#   bash Tools/Unreal/gameplay/bursts.sh [A|B|AB]
# Outputs: Saved/Integration/burst_{A,B}_run.txt (+ _timeline.json, _bp_errors.csv), Saved/Devlog/integration_burst_*.mp4,
# Saved/Integration/qa_logs_{before,after}.txt
cd /p/FoA
export MSYS_NO_PATHCONV=1 FOA_AGENT=gameplay HAYBA_AGENT_ID=gameplay
WHICH=${1:-AB}
BOOT='0.3:viewmode lit|0.5:ke * OnSplashFinished|1.0:ke * OnTitleConfirmed|1.5:ke * WakeUp|6.5:ke * SkipWakeUp|WAIT:T0:6'
A="$BOOT|1.0:ke * ReportEvent PhoneWakeUp|WAIT:T1:3|1.0:ke * ReportEvent FirstSteps|WAIT:T2:3|1.0:ke * ReportEvent Searched|WAIT:T3:2|1.0:ke * ReportEvent KeyTaken|WAIT:T4:2|1.0:ke * ReportEvent KeySnapped|WAIT:T5:2|1.0:ke * ReportEvent LatchFreed|WAIT:T6:2|1.0:ke * ReportEvent WardrobeLanded|WAIT:T7:2|3.0:END"
B="$BOOT|1.0:ke * ReportEvent WardrobeLanded|WAIT:T7:3|3.0:ke * ReportEvent ShirtTaken|WAIT:T8:3|3.0:ke * ReportEvent EncounterWon|WAIT:T9:3|WAIT:T10:6|2.0:ke * ReportEvent WalkedOut|3.0:ke * FailDay|4.5:ke * SkipWakeUp|WAIT:T0:5|1.0:ke * TogglePause|1.0:ke * RequestQuitToTitle|1.0:ke * ConfirmPending|1.5:END"
python Tools/QA/foa_qa.py logs > Saved/Integration/qa_logs_before.txt 2>&1
case $WHICH in *A*) bash Tools/Unreal/gameplay/record_loop.sh burst_A "$A" > Saved/Integration/burst_A_run.txt 2>&1 ;; esac
case $WHICH in *B*) bash Tools/Unreal/gameplay/record_loop.sh burst_B "$B" > Saved/Integration/burst_B_run.txt 2>&1 ;; esac
python Tools/QA/foa_qa.py logs > Saved/Integration/qa_logs_after.txt 2>&1
tail -5 Saved/Integration/qa_logs_before.txt Saved/Integration/qa_logs_after.txt
echo bursts done
