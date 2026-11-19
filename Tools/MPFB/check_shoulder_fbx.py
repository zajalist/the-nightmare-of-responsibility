"""Strict pre-import garment contract for the local shoulder correction."""
import json
from pathlib import Path
import numpy as np
from io_scene_fbx import parse_fbx
root=Path('P:/FoA-Assets/character/mpfb/export')
def read(path):return next(e for e in parse_fbx.parse(str(path))[0].elems if e.id==b'Objects').elems
def children(e):return {v.id:v for v in e.elems}
def array(e,n):return np.array(children(e)[n].props[0])
def signature(e):return (e.id,tuple(str(list(p) if hasattr(p,'tolist') else p) for p in e.props),tuple(signature(c) for c in e.elems))
old=read(root/'teen_chest_flattened/SK_Teen_Polo.fbx');new=read(root/'teen_shoulder/SK_Teen_Polo.fbx')
a,b=[next(e for e in rows if e.id==b'Geometry' and e.props[-1]==b'Mesh') for rows in (old,new)]
va,vb=[array(e,b'Vertices').reshape(-1,3) for e in (a,b)]
assert va.shape==vb.shape
assert np.array_equal(array(a,b'PolygonVertexIndex'),array(b,b'PolygonVertexIndex'))
for tag in (b'LayerElementUV',b'LayerElementMaterial'):assert signature(children(a)[tag])==signature(children(b)[tag]),tag
def bones(rows):return {e.props[1]:signature(children(e)[b'Properties70']) for e in rows if e.id==b'Model' and e.props[-1]==b'LimbNode'}
def clusters(rows):return [tuple((n,tuple(array(e,n)) if n in children(e) else ()) for n in (b'Indexes',b'Weights',b'Transform',b'TransformLink')) for e in rows if e.id==b'Deformer' and e.props[-1]==b'Cluster']
assert bones(old)==bones(new),'Reference skeleton changed'
assert clusters(old)==clusters(new),'Skin weights/bind changed'
delta=np.linalg.norm(vb-va,axis=1)
assert delta.max()<1.0001,delta.max() # float32 centimetre export tolerance: one micron
report=dict(vertices=len(va),changed_vertices=int(np.count_nonzero(delta>1e-5)),max_shift_cm=float(delta.max()),topology_uv_materials_weights_bind_refpose_unchanged=True)
Path('P:/FoA/Saved/Integration/cinematic_audit/shoulder_candidate/fbx_validation.json').write_text(json.dumps(report,indent=2))
print('SHOULDER_FBX_PASS',report)
