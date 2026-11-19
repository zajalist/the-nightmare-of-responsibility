"""Story lane: an MP4 and a captioned frame strip from a PIE proof's frames (pie_wont_come / pie_wardrobe_fall).
The frames were taken every 0.1 s of real time at x0.5 game speed, so the MP4 at 20 fps plays at game speed.
  python Tools/Unreal/flow/proof_media.py <name> [fps=20] [strip=12]
reads Saved/StoryShots/<name>.json (rows kind 'f': n, gt, view, beat, state) and Saved/StoryShots/<name>/f####.png,
writes Saved/StoryShots/<name>.mp4 and Saved/StoryShots/<name>_strip.jpg (strip frames evenly over the run, each
captioned with its game time, view target and beat)."""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

name = sys.argv[1]
fps = int(sys.argv[2]) if len(sys.argv) > 2 else 20
count = int(sys.argv[3]) if len(sys.argv) > 3 else 12
ROOT = Path('P:/FoA/Saved/StoryShots')
rows = [r for r in json.loads((ROOT / f'{name}.json').read_text())['rows'] if r.get('kind') == 'f']
frames = [(r, ROOT / name / ('f%04d.png' % r['n'])) for r in rows]
frames = [(r, p) for r, p in frames if p.exists()]
assert frames, 'no frames'
tmp = ROOT / name / 'seq'
tmp.mkdir(exist_ok=True)
for f in tmp.glob('*.png'):
    f.unlink()
for i, (r, p) in enumerate(frames):  # contiguous numbering for ffmpeg (a missed Shot leaves a gap)
    (tmp / ('%05d.png' % i)).write_bytes(p.read_bytes())
mp4 = ROOT / f'{name}.mp4'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', str(tmp / '%05d.png'),
                '-vf', 'scale=1280:-2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(mp4)], check=True)
pick = [frames[round(i * (len(frames) - 1) / max(1, count - 1))] for i in range(count)]
w, h = 480, 270
sheet = Image.new('RGB', (w * 4, (h + 26) * ((count + 3) // 4)), 'black')
for i, (r, p) in enumerate(pick):
    im = Image.open(p).convert('RGB').resize((w, h))
    x, y = (i % 4) * w, (i // 4) * (h + 26)
    sheet.paste(im, (x, y))
    ImageDraw.Draw(sheet).text((x + 6, y + h + 6), '%.2fs  %s  %s %s' % (r['gt'], r.get('view', '')[:22], r.get('beat') or '',
                                                                          r.get('state') or ''), fill='white')
strip = ROOT / f'{name}_strip.jpg'
sheet.save(strip, quality=88)
print('media', mp4, strip, len(frames), 'frames')
