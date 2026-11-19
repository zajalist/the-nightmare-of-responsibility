"""Offline anatomical pose candidates against the captured source, preserving limb lengths."""
import json,sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal/wakeup')
import wake_math as m
source=json.loads(Path('P:/FoA/Saved/CharacterShots/walk_sleep/lying_closed_source_bones.json').read_text())
b={x['name']:x['position'] for x in source['bones']}
out=[]
for side,targets in [('l',[(12,57,-1),(13,56.5,-1),(13,57.5,-1)]),('r',[(-11,60,-2.5),(-11,60.5,-2.5),(-10,61,-2.5)])]:
    hip,knee,ankle=(b[n+'_'+side] for n in ('thigh','calf','foot'))
    for target in targets:
        pole=m.add(hip,(8 if side=='l' else -3,25,32 if side=='l' else 15))
        q1,q2,reached=m.two_bone(hip,knee,ankle,target,pole)
        solved=m.add(hip,m.qrot(q1,m.sub(knee,hip)))
        a=m.norm(m.sub(hip,solved));c=m.norm(m.sub(reached,solved))
        import math
        flexion=180-math.degrees(math.acos(max(-1,min(1,m.dot(a,c)))))
        out.append(dict(side=side,target=target,knee=solved,miss=m.length(m.sub(reached,target)),
            flexion_deg=flexion,length_cm=m.length(m.sub(knee,hip))+m.length(m.sub(ankle,knee))))
print(json.dumps(out,indent=1))
Path('P:/FoA/Saved/CharacterShots/sleep_art_pose_candidates.json').write_text(json.dumps(out,indent=1))
