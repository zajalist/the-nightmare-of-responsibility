"""An IN1 run's 0.25 s frames as an MP4 at their real timing (intro lane, for review and the devlog):
  python Tools/LookDev/intro_v4/film.py <run>/IN1 <out.mp4>
Each frame is held until the next one was taken (the play.json 'intro' log), the PIE window's title bar cropped."""
import json
import os
import subprocess
import sys
import tempfile

run, out = sys.argv[1], sys.argv[2]
rows = [e for e in json.load(open(f'{run}/play.json'))['log'] if e.get('kind') == 'intro' and e.get('frame') and os.path.exists(e['frame'])]
lst = os.path.join(tempfile.mkdtemp(), 'frames.txt')
with open(lst, 'w') as f:
    for a, b in zip(rows, rows[1:] + [None]):
        f.write(f"file '{a['frame']}'\nduration {max(0.05, (b['s'] - a['s']) if b else 0.25):.3f}\n")
    f.write(f"file '{rows[-1]['frame']}'\n")
r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-vf',
                    'crop=1282:720:2:36,scale=1280:720,fps=24', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', out],
                   capture_output=True, text=True)
print(out, r.returncode, r.stderr[-500:])
