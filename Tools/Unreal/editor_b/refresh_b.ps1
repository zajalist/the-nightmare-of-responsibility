<#
.SYNOPSIS
  Re-mirrors editor A's on-disk project (P:\FoA) into editor B's copy (P:\FoA-B).

.DESCRIPTION
  Run it only while editor B is closed. It refuses to run while an UnrealEditor process has
  P:\FoA-B\FoA.uproject open. launch_b.ps1 runs it before every start of B.

  Copied:  FoA.uproject. Config and Content with /MIR. Every real folder under Plugins with /MIR
           (its Intermediate is skipped, its Binaries are kept so B never tries to rebuild it).
  Linked:  every junction under P:\FoA\Plugins (HaybaMCPToolkit) is recreated in B with the same
           target. P:\FoA-B\Tools is a junction to P:\FoA\Tools, because Hayba on B only runs .py
           files inside B's own project folder.
  Skipped: Saved, Intermediate, DerivedDataCache, Binaries, .git and everything else at the root.

  After the Config mirror, the B-only block below is appended to P:\FoA-B\Config\DefaultEngine.ini.

  Content files that B changed or added on its own disk (a save made outside the Multi-User
  session) are copied to P:\FoA-B\Saved\RefreshRescue\<time>\ before the mirror overwrites them.
  Files deleted in A since the last refresh show up there too; they are only a copy.

  Exits with an error, and changes nothing, if B is open or the drive lacks the copy size plus 20 GB.
#>
[CmdletBinding()]
param(
    [string]$Source = 'P:\FoA',
    [string]$Dest = 'P:\FoA-B'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2

$Source = $Source.TrimEnd('\')
$Dest = $Dest.TrimEnd('\')
$SourceSlash = $Source.Replace('\', '/')

# Appended to B's DefaultEngine.ini after every Config mirror. Within one ini file a repeated section
# merges and a later Key=Value replaces an earlier one, so these win over anything A sets.
$BOverrides = @"

; Editor B only. Tools/Unreal/editor_b/refresh_b.ps1 appends this block on every refresh; change it there.
; Share A's virtual texture chunk cache, the only project-relative cache. The main DDC (the local Zen
; server and %LOCALAPPDATA%\UnrealEngine\Common\DerivedDataCache) is per user, so B already shares it.
[VirtualTextureChunkDDCCache]
Path=$SourceSlash/DerivedDataCache/VT

; Join the FoA session on every start, keep retrying, and never stop at a workspace prompt.
; In-memory changes at startup are noise on B; its real state comes from the session.
[/Script/ConcertClient.ConcertClientConfig]
bAutoConnect=True
bRetryAutoConnectOnError=True
SourceControlSettings=(ValidationMode=SoftAutoProceed)
"@

function Get-OpenBEditors {
    $needle = ($Dest + '\FoA.uproject').ToLowerInvariant()
    $aNeedle = ($Source + '\FoA.uproject').ToLowerInvariant()
    $hits = @{}
    $cmdLines = @{}
    foreach ($p in @(Get-CimInstance Win32_Process -Filter "Name LIKE 'UnrealEditor%'")) {
        $cmdLines[[int]$p.ProcessId] = $p.CommandLine
        if ($null -eq $p.CommandLine) {
            $hits[[int]$p.ProcessId] = "PID $($p.ProcessId): command line not readable (run this as the same user, elevated if that editor is)"
        } elseif ($p.CommandLine.Replace('/', '\').ToLowerInvariant().Contains($needle)) {
            $hits[[int]$p.ProcessId] = "PID $($p.ProcessId): $($p.CommandLine)"
        }
    }
    # An editor started from inside P:\FoA-B with a relative path still leaves a Hayba heartbeat there.
    $hbDir = Join-Path $Dest 'Saved\HaybaMCP\instances'
    foreach ($f in @(Get-ChildItem -LiteralPath $hbDir -Filter '*.json' -File -ErrorAction SilentlyContinue)) {
        try { $hbPid = [int](Get-Content -Raw -LiteralPath $f.FullName | ConvertFrom-Json).pid } catch { continue }
        if (-not $cmdLines.ContainsKey($hbPid) -or $hits.ContainsKey($hbPid)) { continue }
        $cl = $cmdLines[$hbPid]
        if ($cl -and $cl.Replace('/', '\').ToLowerInvariant().Contains($aNeedle)) { continue }  # PID reused by editor A
        $hits[$hbPid] = "PID ${hbPid}: live UnrealEditor with a Hayba heartbeat in $hbDir"
    }
    return @($hits.Values)
}

function Invoke-Robocopy {
    param([string[]]$RcArgs)
    & robocopy @RcArgs | Out-Host
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed with exit code ${LASTEXITCODE}: robocopy $($RcArgs -join ' ')" }
}

function Set-Junction {
    param([string]$Link, [string]$Target)
    $item = Get-Item -LiteralPath $Link -Force -ErrorAction SilentlyContinue
    if ($item) {
        if ($item.LinkType -eq 'Junction' -and (@($item.Target)[0].TrimEnd('\') -ieq $Target.TrimEnd('\'))) { return }
        if (-not $item.LinkType) { throw "$Link is a real folder, not a junction. Move it away by hand; this script never deletes it." }
        [System.IO.Directory]::Delete($Link)  # removes only the link, never the files it points at
    }
    New-Item -ItemType Junction -Path $Link -Target $Target | Out-Null
    Write-Host "Junction $Link -> $Target"
}

# 1. Refuse while B is open.
$open = @(Get-OpenBEditors)
if ($open.Count -gt 0) {
    throw ("Editor B is open, so its files can't be refreshed. Close B first (see docs/agents/multi-editor.md).`n  " + ($open -join "`n  "))
}
if (-not (Test-Path -LiteralPath (Join-Path $Source 'FoA.uproject'))) { throw "No FoA.uproject in $Source." }

# 2. Disk space: the full copy plus 20 GB, even though a refresh usually copies far less.
$srcPlugins = Join-Path $Source 'Plugins'
$plugins = @(Get-ChildItem -LiteralPath $srcPlugins -Directory -Force -ErrorAction SilentlyContinue)
$copyRoots = @((Join-Path $Source 'Content'), (Join-Path $Source 'Config')) + @($plugins | Where-Object { -not $_.LinkType } | ForEach-Object { $_.FullName })
$needBytes = [int64](Get-ChildItem -LiteralPath $copyRoots -Recurse -File -Force | Measure-Object Length -Sum).Sum
$drive = New-Object System.IO.DriveInfo ([System.IO.Path]::GetPathRoot($Dest))
if ($drive.AvailableFreeSpace -lt $needBytes + 20GB) {
    throw ("Not enough space on {0}: {1:N1} GB free, need {2:N1} GB (copy) plus 20 GB." -f $drive.Name, ($drive.AvailableFreeSpace / 1GB), ($needBytes / 1GB))
}
New-Item -ItemType Directory -Force -Path $Dest | Out-Null

# 3. Rescue Content that B changed on its own disk before /MIR overwrites it.
$srcContent = Join-Path $Source 'Content'
$dstContent = Join-Path $Dest 'Content'
if (Test-Path -LiteralPath $dstContent) {
    $changed = New-Object System.Collections.Generic.List[string]
    foreach ($line in @(& robocopy $srcContent $dstContent /MIR /L /XJ /NJH /NJS /NDL /FP /NS /NP /R:0 /W:0)) {
        if ($line -match '^\s*Older\s*\t+(.+?)\s*$') { $changed.Add($dstContent + $Matches[1].Substring($srcContent.Length)) }
        elseif ($line -match '^\s*\*EXTRA File\s*\t+(.+?)\s*$') { $changed.Add($Matches[1]) }
    }
    if ($LASTEXITCODE -ge 8) { throw "robocopy dry run failed with exit code $LASTEXITCODE." }
    if ($changed.Count -gt 0) {
        $rescue = Join-Path $Dest ('Saved\RefreshRescue\' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
        foreach ($f in $changed) {
            $to = Join-Path $rescue ('Content' + $f.Substring($dstContent.Length))
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $to) | Out-Null
            Copy-Item -LiteralPath $f -Destination $to -Force
        }
        Write-Warning "$($changed.Count) Content file(s) in B differed from A (newer in B, or missing in A). Copies are in $rescue"
    }
}

# 4. Mirror.
$common = @('/R:2', '/W:2', '/XJ', '/NP', '/NFL', '/NDL', '/NJH')
Invoke-Robocopy (@($Source, $Dest, 'FoA.uproject') + $common)
Invoke-Robocopy (@((Join-Path $Source 'Config'), (Join-Path $Dest 'Config'), '/MIR', '/DCOPY:DAT') + $common)
$engineIni = Join-Path $Dest 'Config\DefaultEngine.ini'
$aIni = [System.IO.File]::ReadAllText((Join-Path $Source 'Config\DefaultEngine.ini'))
[System.IO.File]::WriteAllText($engineIni, $aIni.TrimEnd() + "`r`n" + $BOverrides.Replace("`r`n", "`n").Replace("`n", "`r`n") + "`r`n", (New-Object System.Text.UTF8Encoding $false))
Invoke-Robocopy (@($srcContent, $dstContent, '/MIR', '/DCOPY:DAT', '/MT:16') + $common)

$dstPlugins = Join-Path $Dest 'Plugins'
New-Item -ItemType Directory -Force -Path $dstPlugins | Out-Null
foreach ($p in $plugins) {
    $to = Join-Path $dstPlugins $p.Name
    if ($p.LinkType) {
        Set-Junction -Link $to -Target (@((Get-Item -LiteralPath $p.FullName -Force).Target)[0])
    } else {
        Invoke-Robocopy (@($p.FullName, $to, '/MIR', '/DCOPY:DAT', '/XD', 'Intermediate') + $common)
    }
}
foreach ($d in @(Get-ChildItem -LiteralPath $dstPlugins -Directory -Force)) {
    if (Test-Path -LiteralPath (Join-Path $srcPlugins $d.Name)) { continue }
    if ($d.LinkType) { [System.IO.Directory]::Delete($d.FullName) } else { Remove-Item -LiteralPath $d.FullName -Recurse -Force }
    Write-Host "Removed plugin $($d.Name) from B (it is gone from A)."
}

Set-Junction -Link (Join-Path $Dest 'Tools') -Target (Join-Path $Source 'Tools')

Write-Host ("Editor B's copy at {0} matches {1} as of {2}." -f $Dest, $Source, (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
exit 0  # robocopy's 1 ("files copied") would otherwise leak out as this script's exit code
