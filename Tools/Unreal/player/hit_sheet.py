"""Contact sheets for a pie_wake_film.py slap strip: the strike and contact (slap_005..016) and the hold and withdraw
(every 4th frame after), each labelled with the sequence time the shot asked for. Crops the editor's letterboxed game
viewport (FOA_CROP=x0,y0,x1,y1; default the 1918x1054 editor layout).
  python Tools/Unreal/player/hit_sheet.py <wake_film folder>"""
import json
import os
import sys

from PIL import Image, ImageDraw

d = sys.argv[1]
crop = tuple(int(v) for v in os.environ.get('FOA_CROP', '7,215,1293,937').split(','))
rows = {r['label']: r['requested_at'] for r in json.load(open(os.path.join(d, 'film.json')))['rows']}
slaps = sorted(k for k in rows if k.startswith('slap_'))


def sheet(labels, out, cols=4, w=480):
    ims = []
    for label in labels:
        a = Image.open(os.path.join(d, label + '.png')).convert('RGB').crop(crop)
        a = a.resize((w, int(w * a.size[1] / a.size[0])))
        ImageDraw.Draw(a).text((5, 5), '%s %.3f' % (label, rows[label]), fill=(255, 40, 40))
        ims.append(a)
    h = ims[0].size[1]
    s = Image.new('RGB', (cols * w, ((len(ims) + cols - 1) // cols) * h))
    for i, a in enumerate(ims):
        s.paste(a, ((i % cols) * w, (i // cols) * h))
    s.save(out, quality=88)
    print(out)


sheet(slaps[5:17], os.path.join(d, 'hit_strip_contact.jpg'))
sheet(slaps[17::4][:12], os.path.join(d, 'hit_strip_hold.jpg'))
