# Run a Tools/MPFB script in the portable Blender, headless, at Idle priority, and wait.
#   pwsh -File Tools/MPFB/run_blender.ps1 [-Blend <file.blend>] <script.py> [args...]
# Log: P:/FoA-Assets/character/mpfb/logs/<script>_<args>.log. Prints the PID so only this process is ever killed.
[CmdletBinding(PositionalBinding = $false)]
param([string]$Blend = '', [Parameter(Mandatory, Position = 0)][string]$Script, [Parameter(ValueFromRemainingArguments)][string[]]$Rest)
$B = 'P:\FoA-Assets\_tools\blender-5.2.3-windows-x64\blender.exe'
$logs = New-Item -ItemType Directory -Force 'P:\FoA-Assets\character\mpfb\logs'
$name = ([IO.Path]::GetFileNameWithoutExtension($Script) + '_' + (($Rest | ForEach-Object { [IO.Path]::GetFileNameWithoutExtension($_) }) -join '_')) -replace '[^\w=.-]', '_'
$log = Join-Path $logs "$name.log"
$argv = @('-b') + $(if ($Blend) { @((Resolve-Path $Blend).Path) } else { @() }) + @('--python', (Resolve-Path $Script).Path, '--') + $Rest
$p = Start-Process -FilePath $B -ArgumentList $argv -PassThru -NoNewWindow -RedirectStandardOutput $log -RedirectStandardError "$log.err"
$p.PriorityClass = 'Idle'
"PID $($p.Id) log $log"
$p.WaitForExit()
Get-Content $log | Select-String -Pattern '^(wrote|saved|ERROR|Error|Traceback)|Error:|rror' | Select-Object -First 40
Get-Content "$log.err" -Tail 15
