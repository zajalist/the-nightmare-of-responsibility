"""Turns a pie_drive.py run into an MP4 and named stills.
  python Tools/Unreal/encounter/make_video.py <drive_log.txt> <out_name> [fps]
Takes every Saved/Screenshots/WindowsEditor/Shot*.png written during the run (pie_drive's 'shot showui' frames), writes
Saved/EncounterCaptures/<out_name>.mp4, copies the frame right after each MARK to <out_name>_<label>.png, then deletes
the raw shots (they are hundreds of megabytes)."""
import glob
import os
import shutil
import subprocess
import sys

log, name = sys.argv[1], sys.argv[2]
fps = sys.argv[3] if len(sys.argv) > 3 else "5"
OUT = "P:/FoA/Saved/EncounterCaptures"
marks = [(float(p[2]), p[3]) for p in (line.split() for line in open(log, encoding="utf-8")) if p[:1] == ["MARK"]]
assert marks, "no MARK lines in the log"
t0 = marks[0][0] - 5
shots = sorted((os.path.getmtime(f), f) for f in glob.glob("P:/FoA/Saved/Screenshots/WindowsEditor/*Shot*.png")
               if os.path.getmtime(f) >= t0)
assert shots, "no screenshots from the run"
seq = os.path.join(OUT, name + "_frames")
shutil.rmtree(seq, ignore_errors=True)
os.makedirs(seq)
for i, (_, f) in enumerate(shots):
    shutil.copy(f, os.path.join(seq, f"{i:05d}.png"))
for t, label in marks:
    after = [f for m, f in shots if m >= t] or [shots[-1][1]]
    shutil.copy(after[0], os.path.join(OUT, f"{name}_{label}.png"))
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", fps, "-i", os.path.join(seq, "%05d.png"),
                "-vf", "scale=1600:-2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22",
                os.path.join(OUT, name + ".mp4")], check=True)
shutil.rmtree(seq)
for _, f in shots:
    os.remove(f)
print(f"{len(shots)} frames -> {OUT}/{name}.mp4; stills:", [f"{name}_{label}.png" for _, label in marks])
