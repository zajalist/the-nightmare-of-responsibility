"""Phone screen page check (main, 2026-11-09): exactly one phone page may draw. anim's phone5 frame showed the lock screen
and the Today list superimposed. OCR (easyocr) on the lower-middle of the frame (x 25-85%, y 35-100%), upscaled 2.5x; OCR swaps a/o ("Doy 18",
"Coroor Certor"), so words match fuzzily. Lock words and home words in the same frame = TWO PAGES.
Red-proven: anim shot_06_home.png -> TWO PAGES. Green: story t0 ScreenShot00985 and 00998 (Today list) and 00975 (lock) -> one page.
  python Tools/Unreal/ui/qa_phone_pages.py <png> [--crop x0,y0,x1,y1]"""
import difflib
import re
import sys

import cv2

LOCK = ('crossed', 'career', 'center', 'reminder', 'wardrobe', 'shirt')
HOME = ('wake', 'dressed', 'leave', 'house', 'job')  # not 'today': the lock's Career Center banner says "Reminder: today"
_reader = None


def _fuzzy(token, vocab):
    # same first letter: 'dressed' must not read as 'crossed' (ratio 0.71)
    return any(token[0] == v[0] and abs(len(token) - len(v)) <= 2 and difflib.SequenceMatcher(None, token, v).ratio() >= 0.65
               for v in vocab)


def pages(img, crop=None):
    """(lock words, home words, all OCR words) for a BGR frame."""
    global _reader
    if crop:
        img = img[crop[1]:crop[3], crop[0]:crop[2]]
    h, w = img.shape[:2]  # the held phone sits in the lower middle of a first-person frame
    img = cv2.resize(img[int(h * 0.35):, int(w * 0.25):int(w * 0.85)], None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    words = [t for _, t, c in _reader.readtext(img) if c > 0.3]
    lock, home = [], []
    for w in words:
        toks = re.findall(r'[a-z]{3,}', w.lower())
        if re.search(r'\bd[ao]y\s*\d', w.lower()) or any(_fuzzy(t, LOCK) for t in toks):
            lock.append(w)
        if any(_fuzzy(t, HOME) for t in toks):
            home.append(w)
    return lock, home, words


if __name__ == '__main__':
    crop = [int(v) for v in sys.argv[sys.argv.index('--crop') + 1].split(',')] if '--crop' in sys.argv else None
    lock, home, words = pages(cv2.imread(sys.argv[1]), crop)
    print(words)
    print('lock', lock, '| home', home, '->', 'TWO PAGES' if lock and home else 'one page' if lock or home else 'no phone page')
