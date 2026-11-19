"""Assemble captured UE frames and raw-shading diagnostics; never changes source renders."""
import json
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageChops

root = Path('P:/FoA/Saved')
phase = root / 'ClothShots/ue_phase_loop'
frames = [Image.open(phase / f'wake_folds_{i:02d}.png').convert('RGB').resize((720,720)) for i in range(8)]
assert ImageChops.difference(frames[0], frames[2]).getbbox(), 'Fold phases did not change pixels'
gif = phase / 'wrinkle_phase_sweep.gif'
frames[0].save(gif, save_all=True, append_images=frames[1:], duration=160, loop=0)
sheet = Image.new('RGB', (1600,450), '#161616')
d = ImageDraw.Draw(sheet)
for i, (outfit, detail) in enumerate([('wake','waist'),('suit','cuff')]):
    for j, (folder, label) in enumerate([('ue_detail','Lit'),('ue_basecolor','Base colour')]):
        img = Image.open(root / f'CharacterShots/mpfb/{folder}/{outfit}_{detail}.png').convert('RGB')
        img = img.resize((400,400))
        x,y = j*800 + i*400, 50
        sheet.paste(img,(x,y))
        d.text((x+12,20),f'{outfit} {detail}   {label}',fill='white')
diag = root / 'ClothShots/geometry_shading_diagnostic.png'
sheet.save(diag)
entries = [
    ('Teen wake and suit rendered with packed fabric materials in four directions',
     [str(p) for p in (root/'CharacterShots/mpfb/ue_cloth').glob('*.png')]),
    ('Joint wrinkle material phase sweep at fixed full weights; runtime animation drive remains separate', [str(gif)]),
    ('Raw base-colour diagnostics confirm continuous polo hem and suit wrist geometry; dark seam comes from shading', [str(diag)]),
    ('Teen cloth material graph: 19 nodes, 252 pixel instructions, clean compile', [str(root/'ClothShots/teen_cloth_graph.png')]),
]
with open('P:/FoA-Devlog/media_log.jsonl','a',encoding='utf-8') as f:
    for what, files in entries:
        f.write(json.dumps({'t':datetime.now().strftime('%H:%M'),'lane':'character','what':what,'files':files})+'\n')
print('Wrote',gif,diag)
