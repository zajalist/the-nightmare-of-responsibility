"""Compare actual UE LOD0 with approved and previous FBXs by bind-space nearest vertex."""
import json,itertools
from pathlib import Path
import numpy as np
from io_scene_fbx import parse_fbx
folder=Path('P:/FoA/Saved/Integration/cinematic_audit/underarm_weights_candidate')
def read(path):
    root=parse_fbx.parse(str(path))[0]
    objs=next(e for e in root.elems if e.id==b'Objects').elems
    links=next(e for e in root.elems if e.id==b'Connections').elems
    byid={e.props[0]:e for e in objs};pairs=[e.props[1:3] for e in links if e.props[0]==b'OO']
    def arr(e,n):return np.array(next(c for c in e.elems if c.id==n).props[0])
    geo=max((e for e in objs if e.id==b'Geometry' and e.props[-1]==b'Mesh'),key=lambda e:len(arr(e,b'Vertices')))
    v=arr(geo,b'Vertices').reshape(-1,3)
    weights={}
    for e in objs:
        if e.id!=b'Deformer' or e.props[-1]!=b'Cluster' or not any(c.id==b'Indexes' for c in e.elems):continue
        model=next(byid[a] for a,b in pairs if b==e.props[0] and byid[a].id==b'Model')
        name=model.props[1].split(b'\x00')[0].split(b'::')[-1].decode()
        row=np.zeros(len(v));row[arr(e,b'Indexes')]=arr(e,b'Weights');weights[name]=row
    layer=next(e for e in geo.elems if e.id==b'LayerElementNormal')
    normals=arr(layer,b'Normals').reshape(-1,3)
    mapping=next(e for e in layer.elems if e.id==b'MappingInformationType').props[0]
    vi=arr(geo,b'PolygonVertexIndex');vi=np.where(vi<0,-vi-1,vi)
    if any(e.id==b'NormalsIndex' for e in layer.elems):normals=normals[arr(layer,b'NormalsIndex')]
    avg=np.zeros_like(v)
    if mapping==b'ByVertice' or mapping==b'ByControlPoint':avg=normals
    else:
        assert len(normals)==len(vi),(mapping,len(normals),len(vi))
        np.add.at(avg,vi,normals)
    avg/=np.maximum(np.linalg.norm(avg,axis=1,keepdims=True),1e-9)
    return v,weights,avg
live,lw,ln=read(folder/'live_polo.fbx');result={}
for variant in ('teen_shoulder','teen_underarm'):
    ref,rw,rn=read(Path('P:/FoA-Assets/character/mpfb/export')/variant/'SK_Teen_Polo.fbx')
    best=None
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((-1,1),repeat=3):
            for scale in (1,.01,100):
                transformed=ref[:,perm]*np.array(signs)*scale
                error=np.linalg.norm((live.max(0)-live.min(0))-(transformed.max(0)-transformed.min(0)))+np.linalg.norm(live.mean(0)-transformed.mean(0))
                if best is None or error<best[0]:best=(error,transformed,perm,signs,scale)
    aligned=best[1];nearest=[];dist=[]
    for start in range(0,len(live),100):
        d=((live[start:start+100,None]-aligned[None])**2).sum(2);idx=d.argmin(1);nearest.extend(idx);dist.extend(np.sqrt(d[np.arange(len(idx)),idx]))
    nearest=np.array(nearest);names=sorted(set(lw)|set(rw))
    a=np.stack([lw.get(n,np.zeros(len(live))) for n in names],1)
    b=np.stack([rw.get(n,np.zeros(len(ref)))[nearest] for n in names],1)
    delta=abs(a-b).sum(1)
    degrees=np.degrees(np.arccos(np.clip((ln*rn[nearest]).sum(1),-1,1)))
    projected={r['id'] for r in json.loads((folder/'wedge_projection.json').read_text())}
    wedge_angles=degrees[np.isin(nearest,list(projected))]
    result[variant]=dict(live_vertices=len(live),source_vertices=len(ref),axis=best[2],sign=best[3],scale=best[4],geometry_max_cm=max(dist),geometry_mean_cm=float(np.mean(dist)),weight_l1_max=float(delta.max()),weight_l1_mean=float(delta.mean()),weight_changed=int((delta>.001).sum()),normal_angle_percentiles=np.percentile(degrees,[0,50,90,99,100]).tolist())
    result[variant]['projected_wedge_normal_max_degrees']=float(wedge_angles.max())
(folder/'live_comparison.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
