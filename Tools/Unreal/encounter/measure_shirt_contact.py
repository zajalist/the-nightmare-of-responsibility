"""Offline surface and furniture clearance from the actual animated battle sample."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'P:/FoA/Tools/Unreal/player');from sleep_skin_contact import matrix
folder=Path('P:/FoA/Saved/Integration/cinematic_audit')
d=json.loads((folder/'live_contact_peak.json').read_text())
r=next(g for g in d['battle']['garments'] if 'Shirt' in str(g['state']))['components']['Rig']
c=np.load(folder/'enemy_shirt_skin.npz');names=c['bone_names'].tolist()
xf=lambda t:matrix(t['position'],t['rotation'],t['scale'])
pose=np.array([xf(r['bones'][n]) for n in names]);deform=pose@np.linalg.inv(c['reference_matrices'])
verts=np.c_[c['vertices_cm'],np.ones(len(c['vertices_cm']))]
out=np.zeros((len(verts),3));weights=np.zeros((len(verts),len(names)))
for i in range(len(verts)):
    a,b=c['vertex_offsets'][i:i+2];bs=c['weight_bones'][a:b];ws=c['weight_values'][a:b]
    out[i]=(np.einsum('nij,j->ni',deform[bs],verts[i])*ws[:,None]).sum(axis=0)[:3];weights[i,bs]=ws
bone='sleeve_l_01';bi=names.index(bone);center=pose[bi,:3,3]
eligible=np.flatnonzero((weights[:,bi]>.85)&(np.linalg.norm(out-center,axis=1)<14))
assert len(eligible)>5
# Surface facing the hero, close to the sleeve-root seam rather than the cuff.
vi=int(eligible[np.argmax(out[eligible,0])]);anchor=out[vi]
local=(np.linalg.inv(pose[bi])@np.r_[anchor,1])[:3]
hand=np.array(d['components']['Body']['bones']['index_03_l']['position'])
delta=hand-anchor
collisions=[]
for row in d['furniture_bounds']:
    lo=np.array(row['center'])-row['extent'];hi=np.array(row['center'])+row['extent']
    if row['label']=='Floor':continue
    for t in np.linspace(0,1,21):
        points=out+delta*t
        n=int(np.all((points>lo)&(points<hi),axis=1).sum())
        if n:collisions.append(dict(label=row['label'],alpha=float(t),vertices=n));break
report=dict(bone=bone,vertex=vi,source_vertex=int(c['source_vertex_ids'][vi]),dominant_weight=float(weights[vi,bi]),
    bone_local_offset=local.tolist(),anchor_world=anchor.tolist(),hand_world=hand.tolist(),translation_cm=delta.tolist(),
    baseline_bounds=[out.min(axis=0).tolist(),out.max(axis=0).tolist()],contact_bounds=[(out+delta).min(axis=0).tolist(),(out+delta).max(axis=0).tolist()],
    sampled_furniture_intersections=collisions,all_furniture=len(d['furniture_bounds']))
report['skin_anchor']=[dict(bone=names[i],weight=float(weights[vi,i]),local=(np.linalg.inv(c['reference_matrices'][i])@verts[vi])[:3].tolist()) for i in np.flatnonzero(weights[vi]>0)]
# The contact target is the outer fingertip skin, not the joint hidden inside it.
with np.load('P:/FoA/Saved/WakeUp/teen_body_full_skin_cache.npz') as z:body={k:z[k] for k in z.files}
bn=body['bone_names'].tolist();finger=bn.index('index_03_l');ids=[]
for i in range(len(body['vertices_cm'])):
    a,b=body['vertex_offsets'][i:i+2]
    if sum(w for j,w in zip(body['weight_bones'][a:b],body['weight_values'][a:b]) if j==finger)>.999:ids.append(i)
ref_inv=np.linalg.inv(body['reference_matrices'][finger]);local=(np.c_[body['vertices_cm'][ids],np.ones(len(ids))]@ref_inv.T)[:,:3]
world=(np.c_[local,np.ones(len(local))]@xf(d['components']['Body']['bones']['index_03_l']).T)[:,:3]
tip=int(np.argmin(world[:,0]));report['fingertip']=dict(source_vertex=int(body['source_vertex_ids'][ids[tip]]),bone='index_03_l',local=local[tip].tolist(),world=world[tip].tolist())
(folder/'shirt_contact_geometry.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

