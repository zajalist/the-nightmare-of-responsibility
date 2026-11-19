"""Can the player read the held phone? OCR (easyocr, English, CPU, no download) on the phone proof's lock frame
(shot_*_home.png) at the game's 960x540: PASS when "6:40" is read, and UI's qa_phone_pages finds one page drawing
on the home, list and message frames. The editor viewport is cropped first (FOA_CROP).
  python Tools/Unreal/player/phone_readability.py <phone proof folder>"""
import glob
import os
import sys

import easyocr
from PIL import Image

d = sys.argv[1]
crop = tuple(int(v) for v in os.environ.get('FOA_CROP', '7,137,1293,1015').split(','))
shots = sorted(glob.glob(os.path.join(d, 'shot_*_home.png')))
assert shots, 'no lock frame (shot_*_home.png) in ' + d
reader = easyocr.Reader(['en'], gpu=False, verbose=False, download_enabled=False)
ok = False
for s in shots:
    im = Image.open(s).convert('RGB').crop(crop).resize((960, 540), Image.LANCZOS)
    out = os.path.join(d, os.path.basename(s)[:-4] + '_960.png')
    im.save(out)
    words = reader.readtext(out, detail=0)
    hit = any('6:40' in w for w in words)
    ok = ok or hit
    print(os.path.basename(s), 'OCR at 960x540:', words[:10], '-> 6:40', 'read' if hit else 'NOT read')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import cv2  # noqa: E402
import qa_phone_pages  # noqa: E402  (UI's rendered-frame check: one page drawing, fuzzy OCR)
two = []
for s in sorted(glob.glob(os.path.join(d, 'shot_*_home.png')) + glob.glob(os.path.join(d, 'shot_*_list.png')) +
                glob.glob(os.path.join(d, 'shot_*_message.png'))):
    lock, home, _ = qa_phone_pages.pages(cv2.imread(s), list(crop))
    print(os.path.basename(s), 'pages: lock', lock[:3], '| home', home[:3])
    if lock and home:
        two.append(os.path.basename(s))
ok = ok and not two
print('PHONE_PAGES', 'TWO PAGES in ' + ', '.join(two) if two else 'one page')
print('PHONE_READABLE', 'passed' if ok else 'FAILED')
sys.exit(0 if ok else 1)
