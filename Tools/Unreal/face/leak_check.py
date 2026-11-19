"""Face blur proof from a pie_face_shots.py run (numpy + PIL, outside the editor).
  python Tools/Unreal/face/leak_check.py <run>        -> Saved/FaceShots/<run>/leak_report.json, exit 1 on any FAIL
  python Tools/Unreal/face/leak_check.py selftest     -> proves each check goes red on a broken fixture
Mask frames (FaceSlip -1, mask review): R = blur weight, G = hard head mask (stencil 4, depth gated), B = dim scene.
Checks per mask frame, with the head projected by the driver (head_px = screen x, y, 16 cm radius in px):
  stencil  the hard mask stays inside 1.7 head radii of his head (head and hair only: no collar, body or props)
  feather  every blurred pixel lies within the face mask plus its soft edge (0.13 head heights + 3 px):
           nothing bleeds past the face (v10)
  firstp   with the pawn as view target (first person) nothing is blurred at all
And per clean/blurred pair (clean_* = the same view with the blur weight 0):
  unread   the face region's structure correlates weakly with the clean face (NCC of gradients < 0.35)
  outside  pixels beyond the feather ring are unchanged (under 3% change by more than 25/255); None (inconclusive)
           when the far frame changed too (room light flicker between the two frames)"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path('P:/FoA/Saved/FaceShots')
FACE_VIEWS = ('close_front', 'close_34', 'close_profile', 'mid_34', 'far_front')


def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float32) / 255.0


def dilate(m, r, ry=None):
    """Box dilation by r pixels sideways and ry (default r) up and down, via shifted maxima (separable)."""
    r, ry = int(np.ceil(r)), int(np.ceil(r if ry is None else ry))
    row = m.copy()
    for s in range(1, r + 1):
        row[:, s:] |= m[:, :-s]
        row[:, :-s] |= m[:, s:]
    out = row.copy()
    for s in range(1, ry + 1):
        out[s:, :] |= row[:-s, :]
        out[:-s, :] |= row[s:, :]
    return out


def allowed(hard, head):
    """Where the blur may change pixels (face only, no bleed): the hard face mask plus its soft oval edge, 0.13 head
    heights + 3 px on every side (v11: the edge fades over 3.5 cm, the oval's depth fade, seen side on in profile).
    Head height = 27 cm, head_px radius = 16 cm."""
    hH = head[2] * 27.0 / 16.0
    return dilate(hard, 0.13 * hH + 3.0, 0.13 * hH + 3.0)


def head_disc(shape, head, k):
    x, y, r = head
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return (xx - x) ** 2 + (yy - y) ** 2 <= (k * r) ** 2


def check_mask(img, head, first_person=False, need_face=True):
    w = img[..., 0] > 3 / 255
    hard = img[..., 1] > 0.5
    res = dict(blurred_px=int(w.sum()), head_px=int(hard.sum()))
    if first_person:
        res['firstp'] = res['blurred_px'] == 0
        return res
    if head is None:
        res['error'] = 'no projected head'
        return res
    ring = allowed(hard, head)
    res['feather_leak_px'] = int((w & ~ring).sum())
    res['feather'] = res['feather_leak_px'] == 0
    disc = head_disc(hard.shape, head, 1.7)
    res['stencil_leak_px'] = int((hard & ~disc).sum())
    res['stencil'] = res['stencil_leak_px'] <= max(4, 0.002 * res['head_px']) and (res['head_px'] > 0 or not need_face)
    return res


def grad_ncc(a, b, m):
    ga = np.abs(np.diff(a.mean(-1), axis=0))[:, :-1] + np.abs(np.diff(a.mean(-1), axis=1))[:-1]
    gb = np.abs(np.diff(b.mean(-1), axis=0))[:, :-1] + np.abs(np.diff(b.mean(-1), axis=1))[:-1]
    m = m[:-1, :-1]
    x, y = ga[m] - ga[m].mean(), gb[m] - gb[m].mean()
    return float((x * y).sum() / (np.sqrt((x * x).sum() * (y * y).sum()) + 1e-9))


def check_pair(clean, blur, mask_img, head):
    """unread: gradient NCC of the face region vs the clean frame. outside: in a band around the head (beyond the
    feather ring, out to 0.6 head heights) under 3% of pixels change by more than 25/255; the two frames are a few
    ticks apart, so grain, breathing and TSR differ a little everywhere, but a smear leak changes whole rows."""
    hard = mask_img[..., 1] > 0.5
    rH = head[2] * 27.0 / 16.0
    ring = allowed(hard, head)
    band = dilate(hard, 0.8 * rH) & ~ring
    face = head_disc(hard.shape, (head[0], head[1] + 0.25 * head[2], head[2]), 0.75) & hard
    diff = np.abs(clean - blur).max(-1)
    res = dict(face_px=int(face.sum()))
    res['ncc'] = grad_ncc(clean, blur, face) if face.sum() > 50 else None
    res['unread'] = res['ncc'] is not None and res['ncc'] < 0.35
    res['outside_changed'] = float((diff[band] > 25 / 255).mean()) if band.any() else 0.0
    far = ~head_disc(hard.shape, head, 2.5)
    res['far_changed'] = float((diff[far] > 25 / 255).mean()) if far.any() else 0.0
    # The room light changed between the two frames (whole frame differs): the band can't show a leak either way.
    res['outside'] = None if res['far_changed'] > 0.3 else res['outside_changed'] < 0.03
    return res


def run(name):
    folder = ROOT / name
    shots = {s['label']: s for s in json.loads((folder / 'shots.json').read_text())['shots']}
    report, ok = {}, True
    for label, s in shots.items():
        if not label.startswith('mask_'):
            continue
        img = load(folder / f'{label}.png')
        r = check_mask(img, s.get('head_px'), first_person=label == 'mask_gameplay', need_face=label[5:] != 'back')  # from behind no face is right
        report[label] = r
        ok &= all(r.get(k, True) for k in ('firstp', 'feather', 'stencil')) and 'error' not in r
        view = label[5:]
        if (folder / f'clean_{view}.png').exists() and (folder / f'{view}.png').exists() and s.get('head_px'):
            p = check_pair(load(folder / f'clean_{view}.png'), load(folder / f'{view}.png'), img, s['head_px'])
            if view not in FACE_VIEWS:  # back, behind and top-down views show no face: readability does not apply
                p['unread'] = None
            report['pair_' + view] = p
            ok &= p['unread'] is not False and p['outside'] is not False
    report['PASS'] = bool(ok)
    (folder / 'leak_report.json').write_text(json.dumps(report, indent=1))
    for k, v in report.items():
        print(k, v)
    return ok


def selftest():
    """Each check must go red on a fixture built to break it, and green on a clean one."""
    h, w = 200, 300
    head = (150.0, 80.0, 30.0)
    good = np.zeros((h, w, 3), np.float32)
    good[head_disc((h, w), head, 1.0)] = (1.0, 1.0, 0.0)
    assert check_mask(good, head)['feather'] and check_mask(good, head)['stencil']
    leak = good.copy()
    leak[180:190, 10:40, 0] = 1.0  # blur far from the head
    assert not check_mask(leak, head)['feather']
    collar = good.copy()
    collar[150:200, 100:200] = (1.0, 1.0, 0.0)  # stencil on the shirt below the head
    assert not check_mask(collar, head)['stencil']
    fp = np.zeros((h, w, 3), np.float32)
    assert check_mask(fp, None, True)['firstp']
    assert not check_mask(good, None, True)['firstp']
    rng = np.random.default_rng(1)
    clean = rng.random((h, w, 3)).astype(np.float32)
    same = clean.copy()
    assert not check_pair(clean, same, good, head)['unread']  # an untouched face is readable
    smeared = clean.copy()
    disc = head_disc((h, w), head, 1.0)
    smeared[disc] = np.roll(clean, 9, axis=1)[disc] * 0 + clean[disc].mean(0)
    assert check_pair(clean, smeared, good, head)['unread']
    spill = smeared.copy()
    spill[100:130, :, :] = 1.0 - spill[100:130, :, :]  # whole rows changed just below the head
    assert not check_pair(clean, spill, good, head)['outside']
    assert check_pair(clean, smeared, good, head)['outside']
    assert check_pair(clean, smeared * 0.4, good, head)['outside'] is None  # whole frame darker: inconclusive
    print('selftest 11/11 red-proven')


if __name__ == '__main__':
    if sys.argv[1] == 'selftest':
        selftest()
    else:
        sys.exit(0 if run(sys.argv[1]) else 1)
