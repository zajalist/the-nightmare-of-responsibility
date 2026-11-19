"""Compare portrait FBX with shipped topology, rig, UVs, skin weights and neck normals."""
import json
from pathlib import Path
import numpy as np
from io_scene_fbx import parse_fbx

root=Path('P:/FoA-Assets/character/mpfb/export')
def read(path):
    f,_=parse_fbx.parse(str(path))
    return next(e for e in f.elems if e.id==b'Objects').elems
def children(e):return {v.id:v for v in e.elems}
def geometry(objects):return next(e for e in objects if e.id==b'Geometry' and e.props[-1]==b'Mesh')
def array(e,name):return np.array(children(e)[name].props[0])
def signature(e):
    def prop(p):return list(p) if hasattr(p,'tolist') else p
    return (e.id,tuple(str(prop(p)) for p in e.props),tuple(signature(c) for c in e.elems))

old=read(root/'teen_cm/SK_Teen_Head.fbx');new=read(root/'teen_portrait_v1/SK_Teen_Head.fbx')
a,b=geometry(old),geometry(new)
va,vb=array(a,b'Vertices').reshape(-1,3),array(b,b'Vertices').reshape(-1,3)
assert va.shape==vb.shape,(va.shape,vb.shape)
assert np.array_equal(array(a,b'PolygonVertexIndex'),array(b,b'PolygonVertexIndex')),'Topology changed'
for tag in (b'LayerElementUV',b'LayerElementMaterial'):
    assert signature(children(a)[tag])==signature(children(b)[tag]),tag
def bones(objects):
    return {e.props[1]:signature(children(e)[b'Properties70']) for e in objects if e.id==b'Model' and e.props[-1]==b'LimbNode'}
assert bones(old)==bones(new),'Reference skeleton changed'
def clusters(objects):
    return [tuple((name,tuple(array(e,name)) if name in children(e) else ()) for name in (b'Indexes',b'Weights',b'Transform',b'TransformLink'))
            for e in objects if e.id==b'Deformer' and e.props[-1]==b'Cluster']
assert clusters(old)==clusters(new),'Skin weights or bind changed'
def shapes(objects):return {e.props[1]:e for e in objects if e.id==b'Geometry' and e.props[-1]==b'Shape'}
sa,sb=shapes(old),shapes(new)
assert sa.keys()==sb.keys() and len(sa)==52,'Morph set changed'
morph_error=0
for name in sa:
    # FBX elides zero deltas; centimetre conversion can change sparse support at float precision.
    da,db=np.zeros_like(va),np.zeros_like(vb)
    da[array(sa[name],b'Indexes')]=array(sa[name],b'Vertices').reshape(-1,3)
    db[array(sb[name],b'Indexes')]=array(sb[name],b'Vertices').reshape(-1,3)
    morph_error=max(morph_error,float(np.max(np.abs(da-db))))
assert morph_error<.0001,morph_error
def surface(objects):
    geo=geometry(objects);v=array(geo,b'Vertices').reshape(-1,3);ind=array(geo,b'PolygonVertexIndex');ind=np.where(ind<0,-ind-1,ind)
    layer=children(children(geo)[b'LayerElementNormal']);norm=np.array(layer[b'Normals'].props[0]).reshape(-1,3)
    if b'NormalsIndex' in layer:norm=norm[np.array(layer[b'NormalsIndex'].props[0])]
    return {tuple(np.round(v[i],4)):n for i,n in zip(ind,norm)}
body=surface(read(root/'teen_cm/SK_Teen_Body.fbx'));head=surface(new)
shared=body.keys()&head.keys();assert len(shared)>=50,len(shared)
neck_error=max(float(np.linalg.norm(body[v]-head[v])) for v in shared);assert neck_error<.001,neck_error
report={'vertex_count':len(va),'bone_count':len(bones(new)),'topology_uv_material_order_unchanged':True,
        'skeleton_weights_bind_unchanged':True,'morph_count':len(sa),'max_morph_delta_error_cm':morph_error,
        'neck_shared_vertices':len(shared),'max_neck_normal_delta':neck_error,
        'changed_vertices':int(np.count_nonzero(np.linalg.norm(va-vb,axis=1)>1e-5)),
        'max_vertex_shift_cm':float(np.linalg.norm(va-vb,axis=1).max())}
Path('P:/FoA/Saved/CharacterShots/mpfb/portrait_face/fbx_validation.json').write_text(json.dumps(report,indent=2))
print('PORTRAIT_FBX_PASS',json.dumps(report))
