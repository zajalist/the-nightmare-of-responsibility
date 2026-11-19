"""Combine actual render RGB with its engine opacity matte; no generated/inpainted pixels."""
import json
from pathlib import Path
from PIL import Image, ImageChops
import numpy as np

ROOT=Path('P:/FoA/Saved/LookDev/intro_ingame')
capture=json.loads((ROOT/'layers_capture.json').read_text())
assert capture['error'] is None,capture
names=sorted({s['name'] for s in capture['shots']})
report=[]
for name in names:
    full=Image.open(ROOT/(name+'_Full.png')).convert('RGBA')
    bg=Image.open(ROOT/(name+'_BG.png')).convert('RGBA')
    matte=Image.open(ROOT/(name+'_Matte.png')).convert('RGBA')
    # SceneColor HDR A is inverse opacity: opaque foreground is 0, uncovered pixels are 1.
    alpha=ImageChops.invert(matte.getchannel('A'))
    a=np.asarray(alpha);rgb=np.asarray(full)[:,:,:3]
    coverage=float((a>127).mean());luma=rgb.mean(axis=2)
    assert .005<coverage<.995,(name,'invalid actor matte',coverage,matte.getextrema())
    assert float(luma.mean())>8 and float(np.percentile(luma,95))>35,(name,'image remains too dark',luma.mean())
    near=full.copy();near.putalpha(alpha)
    bg.save(ROOT/(name+'.png'));near.save(ROOT/(name+'_Near.png'))
    report.append({'name':name,'foreground_coverage':coverage,'mean_rgb':float(luma.mean()),'p95_rgb':float(np.percentile(luma,95)),
                   'source':'Unreal full room, foreground-hidden background, actor-only inverse-opacity matte'})
# First beat is the already approved real PIE sleeping-player frame.
Image.new('RGBA',(1,1),(0,0,0,0)).save(ROOT/'Game01_Sleep_Near.png')
(ROOT/'layers_assembled.json').write_text(json.dumps(report,indent=1))
print(json.dumps(report,indent=1))
