# Rebuilds BP_BeatDirector end to end, then captures the mech_flow graphs. Every run declares the two assets it edits
# (FOA_AREAS), so each takes a short asset lease and releases it; nothing here ever needs EXCLUSIVE.
#   powershell -File Tools/Unreal/flow/run_director.ps1
# Order: declare -> compile -> function graphs -> event graph -> compile + error report -> class defaults -> captures.
$env:FOA_AGENT = 'gameplay'; $env:HAYBA_AGENT_ID = 'gameplay'
$env:FOA_AREAS = '/Game/FoA/Gameplay/BP_BeatDirector,/Game/FoA/Gameplay/GI_FoA'
Set-Location P:\FoA
$compile = 'Tools/Unreal/flow/compile_bp.py'
foreach ($step in @(@('Tools/Unreal/flow/build_director.py', 'FOA_STEP=declare'), @($compile), @('Tools/Unreal/flow/build_director.py', 'FOA_STEP=funcs'),
                    @('Tools/Unreal/flow/build_director.py', 'FOA_STEP=events'), @($compile), @('Tools/Unreal/flow/build_director.py', 'FOA_STEP=defaults'),
                    @('Tools/Unreal/flow/capture_flow.py'))) {
    Write-Output "=== $($step -join ' ')"
    python Tools/Unreal/ue_remote.py @step 2>&1 | Select-String -NotMatch '^\s*$|^requested ' | Select-Object -Last 12
    if ($LASTEXITCODE -ne 0) { Write-Output "FAILED: $($step -join ' ')"; exit 1 }
}
# The guarded Python transport may refuse saves (save_loaded_asset -> False); Hayba's C++ compile saves reliably.
Set-Content -Path P:/FoA/Saved/flow_compile_params.json -Value '{"path": "/Game/FoA/Gameplay/BP_BeatDirector"}'
python Tools/Unreal/hayba_call.py blueprint_compile '@P:/FoA/Saved/flow_compile_params.json'
if ($LASTEXITCODE -ne 0) { Write-Output 'FAILED: Hayba blueprint_compile'; exit 1 }
Write-Output 'DIRECTOR OK'
