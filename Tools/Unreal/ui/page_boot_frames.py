"""Film the v3.1 direction page's boot (go('boot')) with headless Chromium and keep one frame per beat, for the step-4
side-by-side. The page's stage is a 16:9 element; frames are cropped to it.
  python Tools/Unreal/ui/page_boot_frames.py <page URL or index.html> <out dir>   (serve it over http: WebGL rejects file:// images)"""
import os
import sys
import time

from playwright.sync_api import sync_playwright

BEATS = [(1.0, 'boot_black'), (3.2, 'boot_ue'), (8.6, 'boot_aholo'), (13.6, 'boot_hayba_form'), (15.4, 'boot_hayba'),
         (17.4, 'boot_hayba_out'), (20.6, 'boot_title_in'), (23.5, 'title_boot')]


def main(page_path, out):
    os.makedirs(out, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False)  # headless Chromium has no WebGL: the grains and title would be missing
        pg = b.new_page(viewport={'width': 1700, 'height': 1100})
        pg.goto(page_path if page_path.startswith('http') else 'file:///' + os.path.abspath(page_path).replace(os.sep, '/'))
        pg.wait_for_timeout(2500)  # fonts, room image, WebGL
        stage = pg.locator('#stage')
        pg.click('#replay')  # the page's own "replay boot" button: go('boot')
        t0 = time.time()
        for t, name in BEATS:
            wait = t0 + t - time.time()
            if wait > 0:
                pg.wait_for_timeout(int(wait * 1000))
            stage.screenshot(path=os.path.join(out, f'{name}.png'))
            print(name, round(time.time() - t0, 2))
        b.close()


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
