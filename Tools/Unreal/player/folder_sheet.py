"""Contact sheet of every PNG in a PIE proof folder, in name order, cropped to the PIE viewport and labelled.
  python Tools/Unreal/player/folder_sheet.py <folder> [cols] [prefix]  -> <folder>/sheet[_prefix].jpg"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

folder = Path(sys.argv[1])
cols = int(sys.argv[2]) if len(sys.argv) > 2 else 6
prefix = sys.argv[3] if len(sys.argv) > 3 else ''
CROP = (7, 137, 1293, 1015)  # the PIE viewport inside the editor window that 'Shot showui' grabs
files = sorted(f for f in folder.glob(prefix + '*.png'))
w, h = 400, 273
sheet = Image.new('RGB', (cols * w, max(1, (len(files) + cols - 1) // cols) * (h + 20)), (20, 20, 20))
for k, f in enumerate(files):
    im = Image.open(f).convert('RGB')
    if im.size[0] > 1500:
        im = im.crop(CROP)
    x, y = (k % cols) * w, (k // cols) * (h + 20)
    sheet.paste(im.resize((w, h)), (x, y))
    ImageDraw.Draw(sheet).text((x + 4, y + h + 4), f.stem, fill=(255, 220, 120))
out = folder / ('sheet%s.jpg' % ('_' + prefix if prefix else ''))
sheet.save(out, quality=88)
print(out, len(files))
