# Exit 1 when a Standalone Game the editor launched (UnrealEditor -game, parent = the editor) is running: the user's
# own test session. QA bursts must not start then (coordinator rule, 2026-11-18).
$ed = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -notmatch ' -game' }
$games = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match ' -game' -and ($ed.ProcessId -contains $_.ParentProcessId) }
if ($games) { "user game running: " + ($games.ProcessId -join ','); exit 1 } else { "no user game"; exit 0 }
