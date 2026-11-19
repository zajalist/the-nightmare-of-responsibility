"""Select lowest skin surface samples from captured Body, before a bounded static bed trace."""
import json,os
from pathlib import Path
import numpy as np
from sleep_skin_contact import skin
folder=Path(json.loads(Path('P:/FoA/Saved/CharacterShots/sleep_side/latest.json').read_text())['folder'])
cache_path=os.environ.get('FOA_SKIN_CACHE','P:/FoA/Saved/CharacterShots/body_full_skin_cache.npz')
points,cache,meta=skin(folder/'body_pose.json',cache_path)
cache_meta=json.loads(Path(cache_path).with_suffix('.json').read_text())
pose_meta=json.loads((folder/'body_pose.json').read_text())
if cache_meta.get('source_mesh'):
    assert cache_meta['source_mesh'].split('.')[0]==pose_meta['mesh'].split('.')[0], 'Skin cache does not match current Body asset; regenerate its bind data'
labels=[]
for i in range(len(points)):
    lo,hi=cache['vertex_offsets'][i:i+2]
    labels.append(str(cache['bone_names'][cache['weight_bones'][lo+np.argmax(cache['weight_values'][lo:hi])]]))
out=[]
for kind in ('pelvis','foot_l','foot_r','calf','spine','neck','clavicle','upperarm','lowerarm','hand'):
    ids=[i for i,n in enumerate(labels) if n.startswith(kind)]
    cells={}
    for i in ids:
        p=points[i];cell=(round(p[0]/3),round(p[1]/3))
        if cell not in cells or p[2]<cells[cell][2]:cells[cell]=p
    for p in cells.values():out.append(dict(region=kind,skin=p.tolist()))
(folder/'support_probes.json').write_text(json.dumps(out))
print('Wrote',len(out),'skin samples',folder)
