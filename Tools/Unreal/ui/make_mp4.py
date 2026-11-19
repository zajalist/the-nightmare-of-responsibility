"""Frames in Saved/UIShots/pie/*.png (sorted) -> Saved/UIShots/pie/ui_loop.mp4, 1.5 s per frame, 1920x1080 letterboxed.
This ffmpeg build has no glob input, so it uses a concat list."""
import glob
import os
import subprocess

import sys
D = sys.argv[1] if len(sys.argv) > 1 else 'P:/FoA/Saved/UIShots/pie'
frames = sorted(glob.glob(os.path.join(D, '[0-9][0-9]_*.png')))
assert frames, 'no frames'
lst = os.path.join(D, 'frames.txt')
with open(lst, 'w', encoding='utf-8') as f:
    for fr in frames:
        f.write(f"file '{fr.replace(os.sep, '/')}'\nduration 1.5\n")
    f.write(f"file '{frames[-1].replace(os.sep, '/')}'\n")  # concat demuxer needs the last file repeated
out = os.path.join(D, 'ui_loop.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-vf',
                'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p',
                '-r', '30', out], check=True)
print(out, len(frames), 'frames')
