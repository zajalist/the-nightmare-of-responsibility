"""Head pixels in first person, from pie_head_check.py's A/B pairs: fp_<point>_A (as rendered) vs fp_<point>_B (the next
frame with every head component forced hidden). A head in front of the camera shows as a block of changed pixels; frame
to frame noise (grain, dust) stays scattered. Reports the fraction of the game viewport in solid changed blobs (an 11 px opening drops sway edges) and writes
the blob image; FAILS when more than 0.5 % of the viewport changed by more than 40 levels in such blobs.
  python Tools/Unreal/player/head_pixels.py <head_check folder>"""
import glob
import os
import sys

from PIL import Image, ImageChops, ImageFilter

d = sys.argv[1]
crop = tuple(int(v) for v in os.environ.get('FOA_CROP', '7,137,1293,1015').split(','))
bad = []
for a_path in sorted(glob.glob(os.path.join(d, 'fp_*_A.png'))):
    b_path = a_path[:-6] + '_B.png'
    if not os.path.exists(b_path):
        continue
    a = Image.open(a_path).convert('L').crop(crop)
    b = Image.open(b_path).convert('L').crop(crop)
    # the view may turn a little between the two frames (T9 return): register B onto A by the best whole-pixel shift
    # (searched on a quarter-size copy), so a moving camera does not read as a head
    sa, sb = a.resize((a.size[0] // 4, a.size[1] // 4)), b.resize((a.size[0] // 4, a.size[1] // 4))
    cost = lambda im: sum(i * c for i, c in enumerate(im.histogram()))  # noqa: E731  (sum of absolute differences)
    best = min(((cost(ImageChops.difference(sa, ImageChops.offset(sb, dx, dy)).crop((8, 8, sa.size[0] - 8, sa.size[1] - 8))), dx, dy)
                for dx in range(-6, 7) for dy in range(-6, 7)))
    b = ImageChops.offset(b, best[1] * 4, best[2] * 4)
    m = 6 * 4 + 4  # ignore the wrapped border the shift leaves
    a, b = a.crop((m, m, a.size[0] - m, a.size[1] - m)), b.crop((m, m, b.size[0] - m, b.size[1] - m))
    diff = ImageChops.difference(a, b).filter(ImageFilter.MedianFilter(5))  # drop single-pixel grain
    # an opening (erode, then dilate, 11 px) keeps solid blobs (a head) and drops the thin edge lines a 1-2 px
    # breathing sway between the two frames leaves along every contrast edge
    blob = diff.point(lambda v: 255 if v > 40 else 0).filter(ImageFilter.MinFilter(11)).filter(ImageFilter.MaxFilter(11))
    changed = sum(blob.histogram()[255:]) / float(a.size[0] * a.size[1])
    point = os.path.basename(a_path)[3:-6]
    blob.save(os.path.join(d, 'diff_%s.png' % point))
    print('%-18s changed %.3f %%  (B registered by %d,%d px)' % (point, 100 * changed, best[1] * 4, best[2] * 4))
    if changed > 0.005:
        bad.append(point)
for m_path in sorted(glob.glob(os.path.join(d, 'fp_*_M.png'))):  # the blur-weight mask: stencil-4 (Face, Hair) coverage
    mk = Image.open(m_path).convert('L').crop(crop).filter(ImageFilter.MedianFilter(5))
    hist = mk.histogram()
    cover = sum(hist[128:]) / float(mk.size[0] * mk.size[1])
    point = os.path.basename(m_path)[3:-6]
    print('%-18s mask (blur weight > 0.5) %.3f %%' % (point, 100 * cover))
    if cover > 0.005:
        bad.append(point + ' mask')
print('HEAD_PIXELS', 'FAILED ' + ', '.join(bad) if bad else 'passed')
sys.exit(1 if bad else 0)
