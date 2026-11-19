"""Actual sock skin surface throughout the captured wake, using canonical FBX weights."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from sleep_skin_contact import matrix

root=Path('P:/FoA/Saved')
data=json.loads((root/'AnimShots/wake_contact_live.json').read_text())
with np.load(root/'WakeUp/teen_socks_skin_cache.npz') as f:
    cache={k:f[k] for k in f.files}
names=cache['bone_names'].tolist()
inverse=np.linalg.inv(cache['reference_matrices'])
vertices=np.column_stack((cache['vertices_cm'],np.ones(len(cache['vertices_cm']))))
indexes=np.repeat(np.arange(len(vertices)),np.diff(cache['vertex_offsets']))
used=np.unique(cache['weight_bones'])
rows=[]
for row in data['feet']:
    bones=row['components']['Body'];transforms=np.zeros_like(inverse)
    for i in used:
        bone=bones[names[i]]
        transforms[i]=matrix(bone['position'],bone['rotation'],bone['scale'])@inverse[i]
    posed=np.zeros((len(vertices),4))
    weighted=np.einsum('nij,nj->ni',transforms[cache['weight_bones']],vertices[indexes])*cache['weight_values'][:,None]
    np.add.at(posed,indexes,weighted)
    # The board occupies the foot-end six cm of the measured bed bounds.
    # Report surface extents; the live render and traced rail are checked separately.
    rows.append(dict(sequence_seconds=row['sequence_seconds'],skin_min=posed[:,:3].min(axis=0).tolist(),
                     skin_max=posed[:,:3].max(axis=0).tolist()))
out=dict(source='canonical SK_Teen_Socks FBX skin weights and captured world-space Body bones',
         skin_vertices=len(vertices),sample_count=len(rows),bed=data['bed'],rows=rows)
head_cache=root/'CharacterShots/mpfb/portrait_face/rigid_head_local_cm.npz'
if head_cache.exists():
    with np.load(head_cache) as f:head_vertices=f['local']
    head_vertices=np.column_stack((head_vertices,np.ones(len(head_vertices))))
    head_rows=[]
    for row in data['sleep']:
        bone=row['components']['Body']['head']
        points=head_vertices@matrix(bone['position'],bone['rotation'],bone['scale']).T
        head_rows.append(dict(sequence_seconds=row['sequence_seconds'],skin_min=points[:,:3].min(axis=0).tolist(),
                              skin_max=points[:,:3].max(axis=0).tolist()))
    out['sleep_head']=dict(vertices=len(head_vertices),headward_max_x=max(r['skin_max'][0] for r in head_rows),
                           lowest_z=min(r['skin_min'][2] for r in head_rows),rows=head_rows)
for label,lo,hi in [('before_body_reveal',0,9.2),('sleep',9.2,19.7),('sit_up',19.7,23.8),('reach',23.8,28.4)]:
    selected=[r for r in rows if lo<=r['sequence_seconds']<hi]
    out[label]=dict(min_x=min(r['skin_min'][0] for r in selected),min_z=min(r['skin_min'][2] for r in selected))
(root/'AnimShots/wake_feet_verified.json').write_text(json.dumps(out,indent=1))
print(json.dumps({k:({a:b for a,b in v.items() if a!='rows'} if isinstance(v,dict) else v)
                  for k,v in out.items() if k!='rows'},indent=1))
