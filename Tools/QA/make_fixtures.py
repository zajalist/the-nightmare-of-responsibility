"""Rebuilds Tools/QA/fixtures from their sources (copies; sources are never moved). `python Tools/QA/foa_qa.py fixtures`.
RED = the real broken captures; GREEN = real good renders or the same captures with the defect fixed in PIL/cv2."""
import json
import os
import shutil
import subprocess
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FIX = os.path.join(ROOT, 'Tools', 'QA', 'fixtures')
SRC_55 = r'C:\Users\Admin\AppData\Local\Temp\claude\47e10ba54099b5a9\f6b57ca2-9e47-4dcd-a55a-de7f221fc83c\images\55.png'
SRC_V6 = os.path.join(ROOT, 'Saved', 'UIShots', 'WBP_MainMenu_v6.png')
SRC_SAND = os.path.join(ROOT, 'Saved', 'PPShots', 'sandmono_wide_before_after.png')
SRC_WAKE = os.path.join(ROOT, 'Saved', 'Devlog', 'wakeup_v2_editor.mp4')
FONT = r'P:\FoA-Assets\fonts\DarkerGrotesque\DarkerGrotesque-Medium.ttf'
VIEWPORT = 'crop=1252:864:4:136'  # the PIE game viewport inside the 1920x1080 editor recording
R55 = {'title': [0.02, 0.29, 0.38, 0.46], 'menu': [0.02, 0.47, 0.50, 0.88]}
RV6 = {'title': [0.075, 0.27, 0.48, 0.46], 'menu': [0.075, 0.50, 0.48, 0.76]}
RVID = {'title': [0.07, 0.28, 0.56, 0.50], 'menu': [0.07, 0.50, 0.56, 0.85]}


def vframe(t, vf, out):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(t), '-i', SRC_WAKE, '-frames:v', '1', '-vf', vf, out], check=True)


def main():
    os.makedirs(FIX, exist_ok=True)
    spec = []
    # (a)/(b): the user's broken menu shot (no menu words; the title washes out over the window)
    shutil.copy(SRC_55, os.path.join(FIX, 'ab_red_menu_55.png'))
    im = Image.open(SRC_55).convert('RGB')
    dr = ImageDraw.Draw(im)
    font = ImageFont.truetype(FONT, 36)
    for i, word in enumerate(('Wake Up', 'Continue', 'Settings', 'Quit')):
        dr.text((195, 470 + 54 * i), word, font=font, fill=(230, 226, 215))
    im.save(os.path.join(FIX, 'a_green_menu_55_words_drawn.png'))
    shutil.copy(SRC_V6, os.path.join(FIX, 'ab_green_mainmenu_v6.png'))
    spec += [dict(check='a', img='ab_red_menu_55.png', region=R55['menu'], expect='FAIL'),
             dict(check='a', img='a_green_menu_55_words_drawn.png', region=R55['menu'], expect='PASS'),
             dict(check='a', img='ab_green_mainmenu_v6.png', region=RV6['menu'], expect='PASS'),
             dict(check='b', img='ab_red_menu_55.png', region=R55['title'], expect='FAIL'),
             dict(check='b', img='ab_green_mainmenu_v6.png', region=RV6['title'], expect='PASS')]
    # (c): the title overlaying the wake-up cinematic (editor recording, game viewport cropped); GREEN = title inpainted
    for t in (25, 33):
        red = os.path.join(FIX, f'c_red_wake_title_{t}s.png')
        vframe(t, VIEWPORT, red)
        a = cv2.imread(red)
        h, w = a.shape[:2]
        x0, y0, x1, y1 = (int(RVID['title'][0] * w), int(RVID['title'][1] * h), int(RVID['title'][2] * w), int(RVID['title'][3] * h))
        m = np.zeros((h, w), np.uint8)
        m[y0:y1, x0:x1] = (cv2.cvtColor(a[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY) > 140).astype(np.uint8) * 255
        m = cv2.dilate(m, np.ones((7, 7), np.uint8))
        cv2.imwrite(os.path.join(FIX, f'c_green_wake_{t}s_title_removed.png'), cv2.inpaint(a, m, 9, cv2.INPAINT_TELEA))
        spec += [dict(check='c', img=f'c_red_wake_title_{t}s.png', regions=RVID, expect='FAIL'),
                 dict(check='c', img=f'c_green_wake_{t}s_title_removed.png', regions=RVID, expect='PASS')]
    # (d): left half = coloured sand (RED), right half = mono sand (GREEN), right half brightened = grey sand (RED)
    s = np.asarray(Image.open(SRC_SAND).convert('RGB')).astype(np.float32) / 255
    left, right = s[:, :1280], s[:, 1280:]
    ch = left.max(2) - left.min(2)
    n, lab, st, _ = cv2.connectedComponentsWithStats((ch > 0.08).astype(np.uint8))
    mask = np.isin(lab, [i for i in range(1, n) if st[i, 4] > 1000]).astype(np.uint8)
    mask = cv2.dilate(cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)), np.ones((5, 5), np.uint8))
    # GREEN: the mono half's sand body scaled to luma ~0.03 (black goo); a 2 px rim keeps its original highlight
    body = cv2.erode(mask, np.ones((5, 5), np.uint8)) > 0
    black = right.copy()
    black[body] *= 0.03 / max(1e-4, float((right[body] @ np.array([0.2126, 0.7152, 0.0722], np.float32)).mean()))
    for name, arr in (('d_red_sand_coloured_left.png', left), ('d_red_sand_grey_mono_right.png', right),
                      ('d_green_sand_black_rim.png', black), ('d_sand_mask.png', np.dstack([mask] * 3).astype(np.float32))):
        Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).save(os.path.join(FIX, name))
    spec += [dict(check='d', img='d_red_sand_coloured_left.png', mask='d_sand_mask.png', expect='FAIL'),
             dict(check='d', img='d_red_sand_grey_mono_right.png', mask='d_sand_mask.png', expect='FAIL'),
             dict(check='d', img='d_green_sand_black_rim.png', mask='d_sand_mask.png', expect='PASS')]
    # (e): 6 s of the wake-up at 5 fps (26-32 s); it moves 26.4-27.6 s and 30.8-32 s and holds still 28.2-30.6 s
    seq = os.path.join(FIX, 'e_seq')
    shutil.rmtree(seq, ignore_errors=True)
    os.makedirs(seq)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '26', '-i', SRC_WAKE, '-t', '6', '-vf',
                    VIEWPORT + ',fps=5,scale=320:-2,format=gray', os.path.join(seq, 'f_%03d.png')], check=True)
    for name, holds in (('e_green_beats.json', [{'name': 'sit_hold', 't': 3.0}, {'name': 'sit_hold_late', 't': 4.0}]),
                        ('e_red_beats.json', [{'name': 'sit_hold', 't': 3.0}, {'name': 'rise_marked_as_hold', 't': 1.0}])):
        json.dump({'fps': 5, 'holds': holds}, open(os.path.join(FIX, name), 'w'), indent=1)
    spec += [dict(check='e', seq='e_seq', beats='e_red_beats.json', expect='FAIL'),
             dict(check='e', seq='e_seq', beats='e_green_beats.json', expect='PASS')]
    # (f): 20 s at 60 fps; RED adds six hitches (80-310 ms)
    rng = np.random.default_rng(7)
    for name, hitch in (('f_green_frametimes.csv', False), ('f_red_frametimes.csv', True)):
        ms = 16.7 + rng.normal(0, 1.2, 1200)
        if hitch:
            ms[[100, 300, 500, 700, 900, 1100]] = [80, 120, 95, 310, 66, 140]
        with open(os.path.join(FIX, name), 'w', encoding='utf-8') as fh:
            fh.write('t,ms,near_shot,phase\n' + ''.join(f'{i / 60:.3f},{v:.2f},0,fixture\n' for i, v in enumerate(ms)))
        spec.append(dict(check='f', csv=name, expect='FAIL' if hitch else 'PASS'))
    json.dump(spec, open(os.path.join(FIX, 'fixtures.json'), 'w'), indent=1)
    print(f'{len(spec)} fixtures -> {FIX}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
