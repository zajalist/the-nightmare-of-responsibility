"""Side-by-side stills of A/B variants from a perf_run.py run, with a 1:1 crop and an edge-energy sharpness number,
so "is 55% visibly softer than 60%" is measured as well as looked at.
  python Tools/Perf/stills_ab.py <run dir> <moment> <variantA> <variantB> [--crop x,y,w,h] [--q 1] [--out file.png]
Sharpness = mean absolute Laplacian over the luminance (higher is crisper); same view, so only relative values count."""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageStat

LAPLACE = ImageFilter.Kernel((3, 3), (0, 1, 0, 1, -4, 1, 0, 1, 0), scale=1, offset=128)


def sharpness(im):
    lap = im.convert('L').filter(LAPLACE)
    return sum(abs(v - 128) * n for v, n in enumerate(lap.histogram())) / (lap.width * lap.height)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run')
    ap.add_argument('moment')
    ap.add_argument('variants', nargs='+')
    ap.add_argument('--crop', default='', help='x,y,w,h in 1080p pixels; default: the centre 480x270')
    ap.add_argument('--q', default='1')
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    shots = [Path(a.run) / 'shots' / f'{a.moment}_{v}_q{a.q}.png' for v in a.variants]
    ims = [Image.open(p).convert('RGB') for p in shots]
    w, h = ims[0].size
    x, y, cw, ch = (int(v) for v in a.crop.split(',')) if a.crop else (w // 2 - 240, h // 2 - 135, 480, 270)
    tw, th = 960, 540
    sheet = Image.new('RGB', (tw * len(ims), th + ch * 2))
    for i, (v, im) in enumerate(zip(a.variants, ims)):
        crop = im.crop((x, y, x + cw, y + ch))
        s_full, s_crop = sharpness(im), sharpness(crop)
        print(f'{a.moment} {v}: sharpness full {s_full:.2f}, crop {s_crop:.2f}, mean luma {ImageStat.Stat(im.convert("L")).mean[0]:.1f}')
        sheet.paste(im.resize((tw, th)), (i * tw, 0))
        sheet.paste(crop.resize((cw * 2, ch * 2), Image.NEAREST), (i * tw, th))  # 2x nearest: pixels stay honest
        d = ImageDraw.Draw(sheet)
        d.rectangle((i * tw + x * tw // w, y * th // h, i * tw + (x + cw) * tw // w, (y + ch) * th // h), outline=(255, 0, 0))
        d.text((i * tw + 6, 6), f'{v}  sharp {s_full:.2f} / crop {s_crop:.2f}', fill=(255, 0, 0))
    out = a.out or str(Path(a.run) / f'stills_{a.moment}_{"_vs_".join(a.variants)}.png')
    sheet.save(out)
    print(out)


if __name__ == '__main__':
    # self-check: a blurred copy must score lower than the original
    _im = Image.effect_noise((64, 64), 64).convert('RGB')
    assert sharpness(_im.filter(ImageFilter.GaussianBlur(2))) < sharpness(_im)
    main()
