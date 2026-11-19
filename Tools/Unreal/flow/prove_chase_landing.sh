#!/usr/bin/env bash
# Story lane: PIE proof of the moved final chase landing (bay floor below the windowsill vase). Takes EXCLUSIVE in a
# PIE window, runs pie_chase_final.py through run_chase_final.py (straight to stage 6, the landing flight, the normal
# Scan and a real E on the shirt; vase, shatter, boss), then releases. Output: Saved/StoryShots/chase_final.json
# and Saved/StoryShots/chase_final/*.png.   bash Tools/Unreal/flow/prove_chase_landing.sh
cd /p/FoA
export FOA_AGENT=story HAYBA_AGENT_ID=story MSYS_NO_PATHCONV=1
trap 'python Tools/Unreal/editor_lock.py release story' EXIT
python Tools/Unreal/editor_lock.py acquire story --ttl 56 --wait 1500 | tail -1
python Tools/Unreal/editor_lock.py status 2>/dev/null | grep -q "^story: exclusive" || { echo "abort: no EXCLUSIVE"; exit 1; }
timeout 62 python Tools/Unreal/flow/run_chase_final.py ${1:-pie_chase_final} 2>&1 | tail -40
