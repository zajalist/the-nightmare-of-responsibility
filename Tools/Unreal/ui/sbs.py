"""Side-by-side of the v3.1 page against PIE frames at matched times (title 3/6/10 s, menu +2/+5 s).
  python Tools/Unreal/ui/sbs.py <proof frames dir> <out.png> [--boot]
Page frames: Saved/MenuLook/page (frames.json: t = seconds since the title showed, menu_at = when the menu opened).
Game frames: NN_title_03s.png ... NN_menu_05s.png from pie_proof_run.py."""
import glob
import json
import os
import sys

from PIL import Image, ImageDraw

PAGE = 'P:/FoA/Saved/MenuLook/page'
BEATS = [('title_03s', 3.0), ('title_06s', 6.0), ('title_10s', 10.0), ('menu_02s', 2.0), ('menu_05s', 5.0)]
W, H = 960, 540


def page_frame(t, menu):
    idx = json.load(open(PAGE + '/frames.json'))
    want = idx['menu_at'] + t if menu else t
    f = min((f for f in idx['frames'] if f['menu'] == menu), key=lambda f: abs(f['t'] - want))
    return f['f'], f['t'] - (idx['menu_at'] if menu else 0)


BOOT = ['boot_ue', 'boot_aholo', 'boot_hayba_form', 'boot_hayba', 'boot_hayba_out', 'title_boot']


def boot(src, out):
    """Step 4: page boot beats (Saved/MenuLook/page_boot, page_boot_frames.py) against the PIE boot burst (UI_MODE=boot)."""
    sheet = Image.new('RGB', (W * 2, H * len(BOOT)), 'black')
    d = ImageDraw.Draw(sheet)
    for row, name in enumerate(BOOT):
        sheet.paste(Image.open(f'P:/FoA/Saved/MenuLook/page_boot/{name}.png').convert('RGB').resize((W, H)), (0, row * H))
        game = sorted(glob.glob(os.path.join(src, f'*_{name}.png')))
        if game:
            sheet.paste(Image.open(game[0]).convert('RGB').resize((W, H)), (W, row * H))
        d.text((8, row * H + 6), f'page v3.1 boot, {name}', fill=(255, 80, 80))
        d.text((W + 8, row * H + 6), f'in game PIE, {name}' if game else f'in game: no {name} frame', fill=(255, 80, 80))
    sheet.save(out)
    print('sbs boot ->', out)


def main(src, out):
    sheet = Image.new('RGB', (W * 2, H * len(BEATS)), 'black')
    d = ImageDraw.Draw(sheet)
    for row, (name, t) in enumerate(BEATS):
        menu = name.startswith('menu')
        pf, pt = page_frame(t, menu)
        sheet.paste(Image.open(pf).convert('RGB').resize((W, H)), (0, row * H))
        game = sorted(glob.glob(os.path.join(src, f'*_{name}.png')))
        if game:
            sheet.paste(Image.open(game[0]).convert('RGB').resize((W, H)), (W, row * H))
        label = ('menu +' if menu else 'title ') + f'{t:.0f} s'
        d.text((8, row * H + 6), f'page v3.1, {label} (frame at {pt:.1f} s)', fill=(255, 80, 80))
        d.text((W + 8, row * H + 6), f'in game PIE, {label}' if game else f'in game: no {name} frame', fill=(255, 80, 80))
    sheet.save(out)
    print('sbs ->', out)


if __name__ == '__main__':
    (boot if '--boot' in sys.argv else main)(sys.argv[1], sys.argv[2])
