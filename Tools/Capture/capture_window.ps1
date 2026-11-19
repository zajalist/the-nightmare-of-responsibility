<#
Screenshots an Unreal Editor window (main frame or a floating asset editor) to PNG, even when other windows cover it.
  powershell -File Tools/Capture/capture_window.ps1 -Title "M_LightShaft" -Out P:/FoA/Saved/GraphShots/M_LightShaft.png
-Title matches part of the window title. Run with -List to see the editor's window titles.
#>
param([string]$Title = "", [string]$Out = "", [switch]$List)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices; using System.Text; using System.Collections.Generic;
public static class FoAWin {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint f);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  public struct RECT { public int L, T, R, B; }
  public static List<KeyValuePair<IntPtr, string>> Windows(HashSet<uint> pids) {
    var found = new List<KeyValuePair<IntPtr, string>>();
    EnumWindows((h, l) => {
      uint pid; GetWindowThreadProcessId(h, out pid);
      if (pids.Contains(pid) && IsWindowVisible(h)) {
        var sb = new StringBuilder(512); GetWindowText(h, sb, 512);
        if (sb.Length > 0) found.Add(new KeyValuePair<IntPtr, string>(h, sb.ToString()));
      }
      return true;
    }, IntPtr.Zero);
    return found;
  }
}
"@
$pids = New-Object 'System.Collections.Generic.HashSet[uint32]'
Get-Process UnrealEditor -ErrorAction SilentlyContinue | ForEach-Object { [void]$pids.Add([uint32]$_.Id) }
if ($pids.Count -eq 0) { Write-Error "No UnrealEditor process"; exit 1 }
$wins = [FoAWin]::Windows($pids)
if ($List) { $wins | ForEach-Object { $_.Value }; exit 0 }
$hit = $wins | Where-Object { $_.Value -like "*$Title*" } | Select-Object -First 1
if (-not $hit) { Write-Error ("No editor window titled like '$Title'. Open: " + (($wins | ForEach-Object { $_.Value }) -join " | ")); exit 1 }
if ([FoAWin]::IsIconic($hit.Key)) { Write-Error "Window '$($hit.Value)' is minimized; PrintWindow can't render it"; exit 1 }
$r = New-Object FoAWin+RECT
[void][FoAWin]::GetWindowRect($hit.Key, [ref]$r)
$w = $r.R - $r.L; $h = $r.B - $r.T
$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
$ok = [FoAWin]::PrintWindow($hit.Key, $hdc, 2)   # 2 = PW_RENDERFULLCONTENT, needed for DirectX-drawn Slate windows
$g.ReleaseHdc($hdc); $g.Dispose()
if (-not $ok) { Write-Error "PrintWindow failed"; exit 1 }
if (-not $Out) { $Out = Join-Path (Split-Path $PSScriptRoot -Parent | Split-Path -Parent) ("Saved/GraphShots/" + ($Title -replace '[^\w-]', '_') + ".png") }
New-Item -ItemType Directory -Force (Split-Path $Out -Parent) | Out-Null
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
"$($hit.Value) -> $Out ($w x $h)"
