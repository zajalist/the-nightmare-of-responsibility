# Runs the mech_flow builders in order inside the editor, stopping at the first failure. Hold the lock first:
#   $env:FOA_AGENT='mech_flow'; python Tools/Unreal/editor_lock.py acquire mech_flow --ttl 600
#   powershell -File Tools/Unreal/flow/run_build.ps1 [-From 2]
param([int]$From = 1)
$env:FOA_AGENT = 'mech_flow'
Set-Location P:\FoA
$steps = @(
    @('Tools/Unreal/flow/build_flow_data.py'),
    @('Tools/Unreal/flow/build_gi.py'),
    @('Tools/Unreal/flow/build_director.py', 'FOA_STEP=funcs'),
    @('Tools/Unreal/flow/build_director.py', 'FOA_STEP=events'),
    @('Tools/Unreal/flow/place_director.py')
)
for ($i = $From; $i -le $steps.Count; $i++) {
    $s = $steps[$i - 1]
    Write-Output "=== step $i : $($s -join ' ')"
    python Tools/Unreal/ue_remote.py @s
    if ($LASTEXITCODE -ne 0) { Write-Output "FAILED at step $i"; exit 1 }
}
Write-Output 'ALL STEPS OK'
