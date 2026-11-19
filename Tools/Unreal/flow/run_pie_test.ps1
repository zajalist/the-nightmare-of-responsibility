# mech_flow PIE test, recorded, in two EXCLUSIVE bursts of 45 s or less (editor-rules: PIE takes a short EXCLUSIVE).
#   powershell -File Tools/Unreal/flow/run_pie_test.ps1
# Burst 1: clean save, Wake Up (front end -> BeginMorning -> the wake-up cinematic), beats to T7 (top-down, the door
#          moves), T8, FailDay: the rollover (mare, fade) into day 19.
# Burst 2: a fresh PIE loads the save (day 19, knowledge, notebook), T0 straight away (skips the cinematic), knowledge
#          shortcuts skip T3 and T4-T5, T7 again (shorter hold, the moved door lit from under), then the save is reset.
# Out: Saved/Recordings/flow_pie.mp4 (both bursts, desktop at 30 fps), Saved/GraphShots/flow_pie_*.png, the STATE lines.
$env:FOA_AGENT = 'mech_flow'; $env:HAYBA_AGENT_ID = 'mech_flow'
Remove-Item Env:FOA_AREAS -ErrorAction SilentlyContinue  # runs reuse the burst's EXCLUSIVE hold
Set-Location P:\FoA
$rec = 'P:/FoA/Saved/Recordings'
New-Item -ItemType Directory -Force $rec | Out-Null
function Pie([string]$cmds) { python Tools/Unreal/ue_remote.py Tools/Unreal/flow/pie_flow.py "FOA_PIE=$cmds" 2>&1 | Select-String 'STATE|wake via|Error|Traceback|assert|PIE' }
function Shot([string]$name) { powershell -File Tools/Capture/capture_window.ps1 -Title 'Unreal Editor' -Out "P:/FoA/Saved/GraphShots/flow_pie_$name.png" | Out-Null; "shot $name" }
function Record([string]$out, [int]$secs) {
    Start-Process ffmpeg -PassThru -WindowStyle Hidden -ArgumentList @('-y', '-hide_banner', '-loglevel', 'error', '-f', 'gdigrab',
        '-framerate', '30', '-draw_mouse', '0', '-t', "$secs", '-i', 'desktop', '-vf', 'scale=1920:-2', '-c:v', 'libx264',
        '-preset', 'ultrafast', '-crf', '24', '-pix_fmt', 'yuv420p', $out)
}
function Burst([string]$name, [scriptblock]$body) {
    # No areas = EXCLUSIVE, which only starts in a PIE window (minutes :x0-:x2); the Pie runs below reuse this hold.
    python Tools/Unreal/editor_lock.py acquire mech_flow --ttl 120 --wait 1800
    if ($LASTEXITCODE -ne 0) { throw "no EXCLUSIVE for $name" }
    $r = Record "$rec/flow_pie_$name.mp4" 50
    $t = Get-Date
    try { & $body } finally {
        Pie 'stop'
        python Tools/Unreal/editor_lock.py release mech_flow
        "$name took $([int]((Get-Date) - $t).TotalSeconds) s"
        Wait-Process -Id $r.Id -Timeout 60 -ErrorAction SilentlyContinue
    }
}
Burst 'burst1' {
    Pie 'start'; Start-Sleep -Seconds 6
    Pie 'reset;wake;state'; Start-Sleep -Seconds 17; Shot '01_morning_day18'
    Pie 'state;ev:PhoneWakeUp;ev:FirstSteps;ev:Searched;ev:KeyTaken;ev:KeySnapped;ev:LatchFreed;ev:WardrobeLanded;state'
    Start-Sleep -Seconds 3; Shot '02_T7_topdown_door_moved'
    Pie 'ev:ShirtTaken;state;fail;state'; Start-Sleep -Seconds 1; Shot '03_rollover'
    Start-Sleep -Seconds 3; Pie 'state'
}
Burst 'burst2' {
    Pie 'start'; Start-Sleep -Seconds 6
    Pie 'state'; Shot '04_reload_day19'
    Pie 'beats;ev:PhoneWakeUp;ev:FirstSteps;ev:KeyTaken;state;ev:LatchFreed;state;ev:WardrobeLanded;state'
    Start-Sleep -Seconds 3; Shot '05_T7_day19_door_lit'
    Pie 'reset;state'
}
Set-Content -Path "$rec/flow_pie_list.txt" -Value "file 'flow_pie_burst1.mp4'`nfile 'flow_pie_burst2.mp4'"
ffmpeg -y -hide_banner -loglevel error -f concat -safe 0 -i "$rec/flow_pie_list.txt" -c copy "$rec/flow_pie.mp4"
Get-Item "$rec/flow_pie.mp4" | Select-Object FullName, Length
