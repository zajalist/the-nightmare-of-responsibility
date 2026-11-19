"""Turn a record_jumpscare.sh burst into proof media:
  python Tools/Unreal/horror/make_media.py <name> [before_s=1.2] [after_s=1.6]
Reads Saved/HorrorShots/<name>_frames (in-engine 'Shot' PNGs, timestamped by mtime) and <name>_timeline.json (phase
changes with epoch). Writes, all under Saved/HorrorShots/:
  <name>_scare.mp4    real-time video of the window around the hit (each frame held until the next one landed), with
                      SFX_Horror_Stinger_01 muxed in at the logged stinger time (the in-engine audio is not captured)
  <name>_scare.gif    the same window, 480 px, silent
  <name>_sheet.png    every frame in the window, labelled with ms relative to the hit frame (phase 3)
Self-check: asserts the window holds frames before and after the hit."""
import glob
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

name = sys.argv[1]
before = float(sys.argv[2]) if len(sys.argv) > 2 else 1.2
after = float(sys.argv[3]) if len(sys.argv) > 3 else 1.6
D = 'P:/FoA/Saved/HorrorShots'
STINGER = 'P:/FoA-Assets/audio/SFX/Horror/SFX_Horror_Stinger_01.wav'
RISER = 0.40

log = json.load(open(f'{D}/{name}_timeline.json', encoding='utf-8'))
slo = next((e['epoch'] for e in log if e['kind'] == 'cmd' and e['cmd'].startswith('slomo 0')), None)
fac = float(next((e['cmd'].split()[1] for e in log if e['kind'] == 'cmd' and e['cmd'].startswith('slomo 0')), 1))
slo_end = next((e['epoch'] for e in log if e['kind'] == 'cmd' and e['cmd'] == 'slomo 1'), float('inf'))


def game(t):
    """Wall clock -> game clock: the scare window ran at slomo `fac`."""
    if slo is None or t <= slo:
        return t
    return slo + (min(t, slo_end) - slo) * fac + max(0.0, t - slo_end)


hit = game(next(e['epoch'] for e in log if e['kind'] == 'phase' and e['phase'] == 3))
frames = sorted(glob.glob(f'{D}/{name}_frames/*.png'), key=os.path.getmtime)
win = [(f, game(os.path.getmtime(f)) - hit) for f in frames if -before <= game(os.path.getmtime(f)) - hit <= after]
assert any(t < 0 for _, t in win) and any(t > 0 for _, t in win), 'no frames around the hit'
print('slomo', fac, 'frames in window', len(win), 'first', round(win[0][1], 3), 'last', round(win[-1][1], 3))

lst = f'{D}/{name}_frames/window.txt'
with open(lst, 'w') as fh:
    for i, (f, t) in enumerate(win):
        nxt = win[i + 1][1] if i + 1 < len(win) else t + 0.1
        fh.write(f"file '{os.path.basename(f)}'\nduration {max(nxt - t, 0.02):.3f}\n")
    fh.write(f"file '{os.path.basename(win[-1][0])}'\n")
silent = f'{D}/{name}_scare_silent.mp4'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-vf',
                'scale=1280:-2,framerate=30,format=yuv420p', '-c:v', 'libx264', '-crf', '18', silent], check=True)
delay_ms = int(max(0.0, (-RISER - win[0][1])) * 1000)  # the stinger file starts RISER s before the hit
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', silent, '-i', STINGER, '-filter_complex',
                f'[1:a]adelay={delay_ms}|{delay_ms}[a]', '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac',
                '-b:a', '192k', '-shortest', f'{D}/{name}_scare.mp4'], check=True)
os.remove(silent)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-vf',
                'scale=480:-2,framerate=20,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse',
                f'{D}/{name}_scare.gif'], check=True)

cols, tw = 6, 320
th = int(tw * 9 / 16)
rows = (len(win) + cols - 1) // cols
sheet = Image.new('RGB', (cols * tw, rows * (th + 18)), (12, 12, 12))
dr = ImageDraw.Draw(sheet)
for i, (f, t) in enumerate(win):
    im = Image.open(f).convert('RGB').resize((tw, th))
    x, y = (i % cols) * tw, (i // cols) * (th + 18)
    sheet.paste(im, (x, y + 18))
    dr.text((x + 4, y + 3), f'{t * 1000:+.0f} ms', fill=(255, 255, 255) if t >= 0 else (150, 150, 150))
sheet.save(f'{D}/{name}_sheet.png')
print('wrote', f'{D}/{name}_scare.mp4', f'{D}/{name}_scare.gif', f'{D}/{name}_sheet.png')
