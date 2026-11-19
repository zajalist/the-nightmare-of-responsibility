"""Offline local sleeve-weight smoothing plus multi-pose clearance; central chest fixed."""
import bpy,numpy as np,json
from pathlib import Path
shirt=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
p=np.array([v.co[:] for v in shirt.data.vertices]);x,y,z=p.T
def smooth(a,b,v):
    t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
mask=smooth(.14,.17,abs(x))*(1-smooth(.24,.28,abs(x)))*smooth(1.28,1.34,z)*(1-smooth(1.44,1.50,z))
names=[g.name for g in shirt.vertex_groups if g.name in rig.data.bones];indices={n:i for i,n in enumerate(names)}
weights=np.zeros((len(p),len(names)));adj=[set() for _ in p]
for edge in shirt.data.edges:
    a,b=edge.vertices;adj[a].add(b);adj[b].add(a)
for v in shirt.data.vertices:
    for g in v.groups:
        name=shirt.vertex_groups[g.group].name
        if name in indices:weights[v.index,indices[name]]=g.weight
before=weights.copy()
for _ in range(6):
    after=weights.copy()
    for i in np.flatnonzero(mask):
        if adj[i]:after[i]=weights[i]+.65*mask[i]*(weights[list(adj[i])].mean(0)-weights[i])
    weights=after
for i in np.flatnonzero(mask):
    weights[i]/=weights[i].sum()
    for j,name in enumerate(names):
        group=shirt.vertex_groups[name];group.remove([int(i)])
        if weights[i,j]>1e-8:group.add([int(i)],float(weights[i,j]),'REPLACE')
assert np.array_equal(weights[abs(x)<=.14],before[abs(x)<=.14])
stats=dict(changed_weight_vertices=int(np.count_nonzero(np.max(abs(weights-before),axis=1)>1e-6)),changed_weight_vertex_ids=np.flatnonzero(np.max(abs(weights-before),axis=1)>1e-8).tolist(),max_weight_l1=float(np.max(abs(weights-before).sum(1))),central_chest_weights_unchanged=True)
source=Path('P:/FoA/Tools/MPFB/prepare_underarm_fit.py').read_text()
source=source.replace('protected=(abs(x)<.20)&(y<-.055)&(z<1.48)','protected=(abs(x)<.14)&(y<-.025)&(z<1.50)')
source=source.replace('(abs(x)>.13)&(abs(x)<.26)','(abs(x)>.14)&(abs(x)<.28)')
source=source.replace("records['rest']=references", "records['rest']=references\nedge=json.loads(Path('P:/FoA/Saved/CharacterShots/wake_handoff/20261108_102230/bed_edge_body_pose.json').read_text())\nrecords['bed_edge']={r['name']:matrix(r['position'],r['rotation'],r['scale']) for r in edge['bones']}")
source=source.replace('foa_teen_underarm_review.blend','foa_teen_underarm_weights_review.blend').replace('/underarm_candidate','/underarm_weights_candidate')
source=source.replace("'weights_bones_topology_unchanged':True","'bones_topology_unchanged':True,'local_weights':stats")
exec(compile(source,'prepare_underarm_fit.py','exec'),globals())
