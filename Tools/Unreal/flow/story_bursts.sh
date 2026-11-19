#!/usr/bin/env bash
# Story lane PIE proofs (each burst is one EXCLUSIVE PIE window, 55 s at most; record_story.sh waits for the window).
#   bash Tools/Unreal/flow/story_bursts.sh lines_a|lines_b|lines_c|handoff|t0|intro
# lines_a: skip the intro, skip the wake-up (the skip hand-off, shot every 0.12 s), then T1-T6 with a pause per thought.
# lines_b: fast-forward to T7, then T7-T10 thoughts, the battle, the payoff and "Day one." on the end black.
# handoff: skip the intro, let LS_WakeUp play to the end (the first gameplay view after normal completion), the T0 phone
#          opening on the list, then the T6 thought.
# lines_c: straight to T9 (events skip ahead), the payoff, T10 with the phone put away, WalkedOut and the end card.
# t0: skip the wake-up, then a fine strip of the hand-off fade-up, the room, and the T0 phone rising on the list.
# intro: the intro from Wake up to the wake-up's black.
cd /p/FoA
MENU='0:viewmode lit|0.5:ke * OnSplashFinished|1.0:ke * OnTitleConfirmed|1.5:ke * WakeUp|6.5:ke * OnStoryFinished'
case "$1" in
lines_a) FOA_SHOT=0.12 FOA_PIE_CAP=55 bash Tools/Unreal/flow/record_story.sh lines_a "$MENU|3.0:ke * SkipWakeUp|WAIT:T0:8|1.0:ke * ReportEvent PhoneWakeUp|0.5:ke * ClosePhone|WAIT:T1:3|4.5:ke * ReportEvent FirstSteps|WAIT:T2:3|6.0:ke * ReportEvent Searched|WAIT:T3:3|4.5:ke * ReportEvent KeyTaken|WAIT:T4:3|1.0:ke * ReportEvent KeySnapped|WAIT:T5:3|6.0:ke * ReportEvent LatchFreed|WAIT:T6:3|4.5:END" ;;
lines_b) FOA_PIE_CAP=55 bash Tools/Unreal/flow/record_story.sh lines_b "$MENU|2.5:ke * SkipWakeUp|WAIT:T0:8|0.8:ke * ReportEvent PhoneWakeUp|0.3:ke * ClosePhone|0.5:ke * ReportEvent FirstSteps|0.5:ke * ReportEvent Searched|0.5:ke * ReportEvent KeyTaken|0.5:ke * ReportEvent KeySnapped|0.5:ke * ReportEvent LatchFreed|0.5:ke * ReportEvent WardrobeLanded|WAIT:T7:3|11:ke * ReportEvent ShirtTaken|WAIT:T8:3|2.0:ke * ReportEvent EncounterWon|WAIT:T9:3|WAIT:T10:6|5.0:ke * ReportEvent WalkedOut|6.5:END" ;;
handoff) FOA_PIE_CAP=55 bash Tools/Unreal/flow/record_story.sh handoff "$MENU|WAIT:T0:32|3.5:ke * ReportEvent PhoneWakeUp|0.5:ke * ClosePhone|0.4:ke * ReportEvent FirstSteps|0.4:ke * ReportEvent Searched|0.4:ke * ReportEvent KeyTaken|0.4:ke * ReportEvent KeySnapped|0.4:ke * ReportEvent LatchFreed|WAIT:T6:3|5.0:END" ;;
lines_c) FOA_PIE_CAP=50 bash Tools/Unreal/flow/record_story.sh lines_c "$MENU|2.5:ke * SkipWakeUp|WAIT:T0:8|0.8:ke * ReportEvent PhoneWakeUp|0.3:ke * ClosePhone|0.5:ke * ReportEvent FirstSteps|0.5:ke * ReportEvent Searched|0.5:ke * ReportEvent KeyTaken|0.5:ke * ReportEvent KeySnapped|0.5:ke * ReportEvent LatchFreed|1.0:ke * ReportEvent EncounterWon|WAIT:T9:3|WAIT:T10:6|1.5:ke * ClosePhone|4.5:ke * ReportEvent WalkedOut|6.5:END" ;;
t0) FOA_SHOT=0.12 FOA_PIE_CAP=40 bash Tools/Unreal/flow/record_story.sh t0_phone "$MENU|2.5:ke * SkipWakeUp|WAIT:T0:8|6.5:END" ;;
intro) FOA_PIE_CAP=50 bash Tools/Unreal/flow/record_story.sh intro_v3b '0:viewmode lit|0.5:ke * OnSplashFinished|1.0:ke * OnTitleConfirmed|1.5:ke * WakeUp|29:END' ;;
esac
