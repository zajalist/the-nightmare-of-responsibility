"""Offline skinning of the existing leg cache; no editor/Blender/render or live process."""
import json
from pathlib import Path
import numpy as np

def matrix(position,quaternion,scale=(1,1,1)):
    x,y,z,w=quaternion
    r=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
    t=np.eye(4);t[:3,:3]=r@np.diag(scale);t[:3,3]=position
    return t

def skin(pose_path,cache_path='P:/FoA/Saved/CharacterShots/body_leg_skin_cache.npz'):
    # NpzFile decompresses on every lookup; materialize once before vertex loops.
    with np.load(cache_path) as archive:
        cache={key:archive[key] for key in archive.files}
    pose=json.loads(Path(pose_path).read_text());bones={b['name']:b for b in pose['bones']}
    names=cache['bone_names'].tolist();ref=cache['reference_matrices'];parents=cache['parent_indices']
    transforms=[];fallback=[]
    for i,name in enumerate(names):
        b=bones[name];t=matrix(b['position'],b['rotation'],b['scale'])
        if i>0 and np.linalg.norm(t[:3,3])<.001 and np.linalg.norm(ref[i,:3,3])>2:
            parent=parents[i];t=transforms[parent]@np.linalg.inv(ref[parent])@ref[i];fallback.append(name)
        transforms.append(t)
    transforms=np.asarray(transforms)@np.linalg.inv(ref)
    v=np.column_stack((cache['vertices_cm'],np.ones(len(cache['vertices_cm']))))
    indexes=np.repeat(np.arange(len(v)),np.diff(cache['vertex_offsets']))
    posed=np.zeros((len(v),4))
    weighted=np.einsum('nij,nj->ni',transforms[cache['weight_bones']],v[indexes])*cache['weight_values'][:,None]
    np.add.at(posed,indexes,weighted)
    world=pose['world'];world_m=matrix(world['position'],world['rotation'],world['scale'])
    return (posed@world_m.T)[:,:3],cache,dict(fallback=fallback)

if __name__=='__main__':
    import sys
    points,cache,meta=skin(sys.argv[1])
    labels=np.zeros(len(points),dtype=int)
    # Report exact surface extrema per most influential bone, not joint-axis proxies.
    for i in range(len(points)):
        lo,hi=cache['vertex_offsets'][i:i+2]
        labels[i]=cache['weight_bones'][lo+np.argmax(cache['weight_values'][lo:hi])]
    out={}
    for kind in ('pelvis','thigh','calf','foot','ball'):
        select=np.array([str(cache['bone_names'][b]).startswith(kind) for b in labels])
        q=points[select]
        if len(q):out[kind]=dict(vertices=len(q),min=q.min(axis=0).tolist(),max=q.max(axis=0).tolist())
    print(json.dumps(out,indent=1))
