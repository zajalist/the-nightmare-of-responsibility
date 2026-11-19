<#
.SYNOPSIS
  Starts editor B on P:\FoA-B and joins it to the Multi-User session FoA as FoA-B.

.DESCRIPTION
  Only the coordinator runs this. Before it, editor A must be running and joined to the FoA session,
  so that A holds Hayba port 52342 (B then takes 52343) and A no longer writes Content to disk.

  Steps: checks the ports, runs refresh_b.ps1 (which refuses if B is already open), then starts
  UnrealEditor.exe with the Multi-User auto-join flags. The flag names come from the engine's
  ConcertSyncClientModule.cpp; FoA is the server name in Config/DefaultEngine.ini (DefaultServerURL).

  -WaitForHayba waits up to 20 minutes for B's Hayba heartbeat and prints the port B took.
#>
[CmdletBinding()]
param([switch]$WaitForHayba)
$ErrorActionPreference = 'Stop'

$Editor = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$Project = 'P:\FoA-B\FoA.uproject'
$EditorArgs = @(
    "`"$Project`"",
    '-CONCERTAUTOCONNECT',
    '-CONCERTRETRYAUTOCONNECTONERROR',
    '-CONCERTSERVER=FoA',
    '-CONCERTSESSION=FoA',
    '-CONCERTDISPLAYNAME=FoA-B'
)

function Get-Listener([int]$Port) {
    Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
}

# Hayba takes the first free port from 52342, so A must already hold 52342 and 52343 must be free.
$a = Get-Listener 52342
if (-not $a) { throw "Nothing listens on port 52342. Start editor A first, so B's Hayba server takes 52343." }
$owner = Get-Process -Id $a.OwningProcess -ErrorAction SilentlyContinue
if (-not $owner -or $owner.ProcessName -notlike 'UnrealEditor*') {
    throw "Port 52342 is held by PID $($a.OwningProcess), which is not an Unreal Editor."
}
$b = Get-Listener 52343
if ($b) { throw "Port 52343 is already held by PID $($b.OwningProcess), so B's Hayba server would land on another port." }

& (Join-Path $PSScriptRoot 'refresh_b.ps1')

$p = Start-Process -FilePath $Editor -ArgumentList $EditorArgs -PassThru
Write-Host "Editor B started as PID $($p.Id): `"$Editor`" $($EditorArgs -join ' ')"
$heartbeat = "P:\FoA-B\Saved\HaybaMCP\instances\$($p.Id).json"
Write-Host "Log: P:\FoA-B\Saved\Logs\FoA.log"
Write-Host "Hayba heartbeat: $heartbeat"

if ($WaitForHayba) {
    $deadline = (Get-Date).AddMinutes(20)
    while (-not (Test-Path -LiteralPath $heartbeat)) {
        if ($p.HasExited) { throw "Editor B exited (code $($p.ExitCode)) before Hayba started. See P:\FoA-B\Saved\Logs\FoA.log." }
        if ((Get-Date) -gt $deadline) { throw "No Hayba heartbeat after 20 minutes. See P:\FoA-B\Saved\Logs\FoA.log." }
        Start-Sleep -Seconds 5
    }
    $port = (Get-Content -Raw -LiteralPath $heartbeat | ConvertFrom-Json).port
    if ($port -ne 52343) { Write-Warning "B's Hayba server took port $port, not 52343. Lanes using FOA_EDITOR=B expect 52343." }
    else { Write-Host "B's Hayba server is on port 52343." }
}
