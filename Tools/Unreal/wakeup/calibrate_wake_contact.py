"""Measure Teen retarget palm drift against the simultaneous source palm, offline.

This avoids treating a sample after impact as though it were the contact frame.
Keep final physical contact checks separate from this calibration measurement.
"""
import json
from pathlib import Path
import wake_math as m
ROOT=Path('P:/FoA/Saved')
data=json.loads((ROOT/'AnimShots/wake_contact_live.json').read_text())
landmark=json.loads((ROOT/'CharacterShots/mpfb/shirt_palm_diagnostic.json').read_text())['palms']['l']
offsets=[]
for row in data['rows']:
    if not 25.42<=row['sequence_seconds']<=25.65:continue
    source=row['components']['Mesh'];hand=source['hand_l'];scale=hand['scale'][0]
    forward=m.norm(m.sub(source['middle_01_l']['position'],hand['position']))
    source_palm=m.sub(m.add(hand['position'],m.mul(forward,6*scale)),(0,0,2.5*scale))
    target=row['components']['Body']['hand_l']
    local=tuple(a*b for a,b in zip(landmark['centroid_ue_cm'],target['scale']))
    target_palm=m.add(target['position'],m.qrot(target['rotation'],local))
    offsets.append(m.sub(source_palm,target_palm))
assert len(offsets)>=3,offsets
mean=tuple(sum(v[i] for v in offsets)/len(offsets) for i in range(3))
spread=max(m.length(m.sub(v,mean)) for v in offsets)
assert spread<1,(mean,spread)
out=dict(world_offset_cm=mean,samples=len(offsets),spread_cm=spread,source='wake_contact_live.json',
         method='simultaneous source palm minus Teen skin palm during pressure hold',live_verified=False)
(ROOT/'WakeUp/teen_palm_calibration.json').write_text(json.dumps(out,indent=2))
print(out)
