"""Choose cloth-surface patch anchors from the actual Teen bind geometry, offline."""
import json
from pathlib import Path
import numpy as np
root=Path('P:/FoA/Saved/WakeUp');result=[]
for bone,cache,target,radius in [('spine_03','teen_polo_skin_cache.npz',(-4,14,137),10),
                               ('upperarm_l','teen_polo_skin_cache.npz',(27,8,143),7),
                               ('thigh_r','teen_body_full_skin_cache.npz',(-13,10,87),9)]:
    with np.load(root/cache) as stored:d={k:stored[k] for k in stored.files}
    bi=list(d['bone_names']).index(bone);weights=np.zeros(len(d['vertices_cm']))
    for i in range(len(weights)):
        a,b=d['vertex_offsets'][i:i+2];bones=d['weight_bones'][a:b];w=d['weight_values'][a:b]
        weights[i]=w[bones==bi].sum()
    indices=np.where(weights>.55)[0];assert len(indices)>10,(bone,len(indices))
    vs=d['vertices_cm'][indices];idx=indices[np.linalg.norm(vs-np.array(target),axis=1).argmin()]
    p=d['vertices_cm'][idx].astype(float);p[1]+=.5 # half-centimetre outside the front surface, also clear of trouser thickness
    local=np.linalg.inv(d['reference_matrices'][bi])@np.r_[p,1]
    result.append({'bone':bone,'local_offset_cm':local[:3].tolist(),'radius_cm':radius,'reference_surface_cm':p.tolist(),
                   'source':cache,'vertex':int(idx),'bone_weight':float(weights[idx])})
out=Path('P:/FoA/Saved/ClothShots/corruption_sites.json');out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
