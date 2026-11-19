"""Inspect generated FBX units and bone scale before allowing UE reimport."""
import sys
from pathlib import Path
from io_scene_fbx import parse_fbx
import numpy as np

folder=Path('P:/FoA-Assets/character/mpfb/export/teen_cm')
files=list(folder.glob('SK_Teen_*.fbx'))
assert len(files)==7,len(files)
surfaces={}
for path in files:
    root,version=parse_fbx.parse(str(path))
    settings=next(e for e in root.elems if e.id==b'GlobalSettings')
    props=next(e for e in settings.elems if e.id==b'Properties70').elems
    unit=next(e.props[-1] for e in props if e.props[0]==b'UnitScaleFactor')
    assert abs(unit-1)<1e-6,(path,unit)
    models=next(e for e in root.elems if e.id==b'Objects').elems
    if path.stem in ('SK_Teen_Body','SK_Teen_Head'):
        geo=next(e for e in models if e.id==b'Geometry' and e.props[-1]==b'Mesh')
        child={e.id:e for e in geo.elems}
        verts=np.array(child[b'Vertices'].props[0]).reshape(-1,3)
        indices=np.array(child[b'PolygonVertexIndex'].props[0])
        indices=np.where(indices<0,-indices-1,indices)
        layer={e.id:e for e in child[b'LayerElementNormal'].elems}
        assert layer[b'MappingInformationType'].props[0]==b'ByPolygonVertex'
        normals=np.array(layer[b'Normals'].props[0]).reshape(-1,3)
        if b'NormalsIndex' in layer:
            normals=normals[np.array(layer[b'NormalsIndex'].props[0])]
        surfaces[path.stem]={tuple(np.round(verts[i],4)):n for i,n in zip(indices,normals)}
    bones=0
    for model in models:
        if model.id!=b'Model' or model.props[-1]!=b'LimbNode':
            continue
        bones+=1
        p=next(e for e in model.elems if e.id==b'Properties70')
        for e in p.elems:
            if e.props[0]==b'Lcl Scaling':
                assert all(abs(v-1)<1e-4 for v in e.props[-3:]),(path,model.props,e.props)
    assert bones>20,bones
    print('FBX_CM_PASS',path.name,'units',unit,'bones',bones)
body,head=surfaces['SK_Teen_Body'],surfaces['SK_Teen_Head']
shared=body.keys() & head.keys()
assert len(shared)>=10,len(shared)
error=max(float(np.linalg.norm(body[v]-head[v])) for v in shared)
assert error<.001,(len(shared),error)
print('NECK_NORMALS_PASS','shared_vertices',len(shared),'maximum_normal_delta',error)
