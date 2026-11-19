"""Garment material A/B stills in the editor viewport (no PIE): frames each TMP_face_Garment_<Name> (spawned by
garments_ab_editor.py) and captures it lit and unlit, then puts the viewport camera and lit mode back.
  python Tools/Unreal/face/garments_ab.py before|after   -> Saved/FaceShots/garments_ab/<tag>_<lit|unlit>_<Name>.png"""
import base64
import sys
from pathlib import Path

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

NAMES = ('Shirt', 'Trousers', 'Sock', 'Tie')
OUT = Path('P:/FoA/Saved/FaceShots/garments_ab')
OUT.mkdir(parents=True, exist_ok=True)
TAG = sys.argv[1]


def call(cmd, **kw):
    r = hc.call(cmd, kw)
    assert r.get('ok'), (cmd, r.get('error'))
    return r.get('data', {})


cam = call('editor_capture_viewport', width=64, height=36)['camera']
try:
    for name in NAMES:
        call('editor_focus_actor', actor_label=f'TMP_face_Garment_{name}', distance_scale=1.5, direction=[-1.0, 0.3, -0.35])
        for mode in ('lit', 'unlit'):
            call('editor_set_viewport_mode', mode=mode)
            d = call('editor_capture_viewport', width=900, height=900, wait_for_shaders=True)
            (OUT / f'{TAG}_{mode}_{name}.png').write_bytes(base64.b64decode(d['image_base64']))
            print(TAG, mode, name)
finally:  # the viewport is someone's view: always hand it back as it was
    call('editor_set_viewport_mode', mode='lit')
    call('editor_set_camera', location=cam['location'],
         rotation={'pitch': cam['rotation'][0], 'yaw': cam['rotation'][1], 'roll': 0})
