# Original FoA command icons. One consistent round 3px stroke, white on transparent.
param([string]$Out = "$env:TEMP/hayba-asset-connectors/foa/battle")
Add-Type -AssemblyName System.Drawing
New-Item -ItemType Directory -Path $Out -Force | Out-Null
foreach ($name in @('Act','Breathe','Mirror','Items','Flee','Target','Composure','Resolve')) {
    $bmp = New-Object System.Drawing.Bitmap 64,64
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.Clear([System.Drawing.Color]::Transparent)
    $p = New-Object System.Drawing.Pen ([System.Drawing.Color]::White),3
    $p.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $p.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $p.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
    switch ($name) {
        Act {
            $g.DrawLine($p,12,41,29,23); $g.DrawLine($p,29,23,39,33)
            $g.DrawLine($p,39,33,50,20); $g.DrawLine($p,50,20,50,32)
            $g.DrawLine($p,50,20,38,20); $g.DrawLine($p,17,47,45,47)
        }
        Breathe {
            $g.DrawArc($p,9,18,25,25,15,285); $g.DrawArc($p,30,18,25,25,-120,285)
            $g.DrawLine($p,32,9,32,34); $g.DrawLine($p,20,50,44,50)
        }
        Mirror {
            $g.DrawEllipse($p,17,8,30,36); $g.DrawLine($p,32,44,32,55)
            $g.DrawLine($p,23,55,41,55); $g.DrawLine($p,24,30,36,18)
        }
        Items {
            $g.DrawRectangle($p,13,22,38,30); $g.DrawArc($p,23,10,18,23,180,180)
            $g.DrawLine($p,13,34,51,34); $g.DrawLine($p,29,32,35,32)
        }
        Flee {
            $g.DrawLine($p,35,13,15,13); $g.DrawLine($p,15,13,15,52)
            $g.DrawLine($p,15,52,35,52); $g.DrawLine($p,29,32,54,32)
            $g.DrawLine($p,45,23,54,32); $g.DrawLine($p,45,41,54,32)
        }
        Target {
            $g.DrawEllipse($p,16,16,32,32); $g.DrawEllipse($p,26,26,12,12)
            $g.DrawLine($p,32,8,32,18); $g.DrawLine($p,32,46,32,56)
            $g.DrawLine($p,8,32,18,32); $g.DrawLine($p,46,32,56,32)
        }
        Composure {
            $g.DrawArc($p,10,13,23,24,180,180); $g.DrawArc($p,31,13,23,24,180,180)
            $g.DrawLine($p,10,25,32,51); $g.DrawLine($p,54,25,32,51)
        }
        Resolve {
            $pts = [System.Drawing.Point[]]@([System.Drawing.Point]::new(36,8),[System.Drawing.Point]::new(17,36),[System.Drawing.Point]::new(31,36),[System.Drawing.Point]::new(27,56),[System.Drawing.Point]::new(49,27),[System.Drawing.Point]::new(35,27))
            $g.DrawPolygon($p,$pts)
        }
    }
    $bmp.Save((Join-Path $Out "T_Battle_$name.png"),[System.Drawing.Imaging.ImageFormat]::Png)
    $p.Dispose(); $g.Dispose(); $bmp.Dispose()
}
Write-Output "Eight battle icons written to $Out"
