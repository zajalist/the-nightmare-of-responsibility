"""Allow only measured local sleeve weights/vertices; lock topology, UVs, bind and skeleton."""
import json
from pathlib import Path
import numpy as np
from io_scene_fbx import parse_fbx
folder=Path('P:/FoA/Saved/Integration/cinematic_audit/underarm_weights_candidate')
report=json.loads((folder/'change.json').read_text())
root=Path('P:/FoA-Assets/character/mpfb/export')
def read(p):return next(e for e in parse_fbx.parse(str(p))[0].elems if e.id==b'Objects').elems
def kids(e):return {v.id:v for v in e.elems}
def arr(e,n):return np.array(kids(e)[n].props[0])
def sig(e):return(e.id,tuple(str(list(p) if hasattr(p,'tolist') else p) for p in e.props),tuple(sig(c) for c in e.elems))
old,new=[read(root/v/'SK_Teen_Polo.fbx') for v in ('teen_shoulder','teen_underarm')]
a,b=[next(e for e in rows if e.id==b'Geometry' and e.props[-1]==b'Mesh') for rows in (old,new)]
va,vb=[arr(e,b'Vertices').reshape(-1,3) for e in (a,b)];assert va.shape==vb.shape
assert np.array_equal(arr(a,b'PolygonVertexIndex'),arr(b,b'PolygonVertexIndex'))
for tag in (b'LayerElementUV',b'LayerElementMaterial'):assert sig(kids(a)[tag])==sig(kids(b)[tag])
def bones(rows):return {e.props[1]:sig(kids(e)[b'Properties70']) for e in rows if e.id==b'Model' and e.props[-1]==b'LimbNode'}
assert bones(old)==bones(new),'Reference pose changed'
def clusters(rows):return [e for e in rows if e.id==b'Deformer' and e.props[-1]==b'Cluster']
allowed=set(report['local_weights']['changed_weight_vertex_ids']);changed=set()
for x,y in zip(clusters(old),clusters(new)):
    for n in (b'Transform',b'TransformLink'):assert np.array_equal(arr(x,n),arr(y,n)),n
    weights=[]
    for e in (x,y):
        row=np.zeros(len(va))
        if b'Indexes' in kids(e):row[arr(e,b'Indexes')]=arr(e,b'Weights')
        weights.append(row)
    changed.update(np.flatnonzero(abs(weights[0]-weights[1])>1e-7).tolist())
assert changed<=allowed,changed-allowed
delta=np.linalg.norm(vb-va,axis=1);assert delta.max()<1.202,delta.max()
# FBX positions use the Blender local mesh axes in centimetres.
central=abs(va[:,0])<=14;assert delta[central].max()<1e-4
result=dict(vertices=len(va),max_shift_cm=float(delta.max()),changed_weight_vertices=len(changed),central_chest_unchanged=True,topology_uv_materials_bind_refpose_unchanged=True)
(folder/'fbx_validation.json').write_text(json.dumps(result,indent=2));print(result)
