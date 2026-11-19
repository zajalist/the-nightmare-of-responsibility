# The second half of run_director.ps1 (events -> compile -> defaults -> captures -> Hayba compile), for when only the
# event graph changed or an events step failed after declare/funcs succeeded. Same leases (two assets, never EXCLUSIVE).
#   powershell -File Tools/Unreal/flow/run_director_events.ps1
$env:FOA_AGENT = 'gameplay'; $env:HAYBA_AGENT_ID = 'gameplay'
$env:FOA_AREAS = '/Game/FoA/Gameplay/BP_BeatDirector,/Game/FoA/Gameplay/GI_FoA'
Set-Location P:\FoA
$compile = 'Tools/Unreal/flow/compile_bp.py'
foreach ($step in @(@('Tools/Unreal/flow/build_director.py', 'FOA_STEP=events'), @($compile),
                    @('Tools/Unreal/flow/build_director.py', 'FOA_STEP=defaults'), @('Tools/Unreal/flow/capture_flow.py'))) {
    Write-Output "=== $($step -join ' ')"
    python Tools/Unreal/ue_remote.py @step 2>&1 | Select-String -NotMatch '^\s*$|^requested ' | Select-Object -Last 12
    if ($LASTEXITCODE -ne 0) { Write-Output "FAILED: $($step -join ' ')"; exit 1 }
}
Set-Content -Path P:/FoA/Saved/flow_compile_params.json -Value '{"path": "/Game/FoA/Gameplay/BP_BeatDirector"}'
python Tools/Unreal/hayba_call.py blueprint_compile '@P:/FoA/Saved/flow_compile_params.json'
if ($LASTEXITCODE -ne 0) { Write-Output 'FAILED: Hayba blueprint_compile'; exit 1 }
Write-Output 'DIRECTOR OK'
