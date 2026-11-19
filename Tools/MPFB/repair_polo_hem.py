"""Sew the polo's separately modelled hem trim to its body, including matching skin weights.
Writes a new layered blend; original MHM and layered source stay unchanged.
"""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
report=json.loads(Path('P:/FoA/Saved/CharacterShots/mpfb/hem_weights.json').read_text())
obj=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
points=np.array([v.co[:] for v in obj.data.vertices])
bones=[b.name for b in rig.data.bones if b.use_deform]
groups={v.index:bones.index(v.name) for v in obj.vertex_groups if v.name in bones}
weights=np.zeros((len(points),len(bones)))
for v in obj.data.vertices:
    for g in v.groups:
        if g.group in groups:weights[v.index,groups[g.group]]=g.weight
main=set(report['components'][0]['indices']);band=set(report['components'][1]['indices'])
assert len(main)==1743 and len(band)==256
mainloop=next(x['indices'] for x in report['boundary_loops'] if set(x['indices'])<=main and x['mean'][2]<1.1)
bandloop=max((x for x in report['boundary_loops'] if set(x['indices'])<=band),key=lambda x:x['mean'][2])['indices']
bandset=set(bandloop)
segments=[tuple(e.vertices) for e in obj.data.edges if set(e.vertices)<=bandset]
assert len(mainloop)==41 and len(segments)==40
adj=[set() for p in points]
for e in obj.data.edges:
    a,b=e.vertices;adj[a].add(b);adj[b].add(a)
# The trim also carried alternating hip influence around its ring. Smooth that field before sewing,
# so the matching seam is continuous in both position and curvature when thighs flex.
for _ in range(6):
    smooth=weights.copy()
    for i in band:
        neighbors=list(adj[i]&band)
        smooth[i]=.5*weights[i]+.5*weights[neighbors].mean(0)
    weights=smooth
deltas={};matched={}
for i in mainloop:
    best=None
    for a,b in segments:
        edge=points[b]-points[a];t=np.clip(np.dot(points[i]-points[a],edge)/np.dot(edge,edge),0,1)
        p=points[a]+t*edge;distance=np.linalg.norm(points[i]-p)
        if best is None or distance<best[0]:best=(distance,p,(1-t)*weights[a]+t*weights[b])
    deltas[i]=best[1]-points[i];matched[i]=best[2]
# Carry the seam correction smoothly into the adjacent two rows; keep chest and sleeves untouched.
front=set(mainloop);visited=front.copy()
for ring,factor in ((1,.5),(2,.15)):
    following=set().union(*(adj[i] for i in front))&main-visited
    for i in following:
        close=[j for j in adj[i] if j in deltas]
        deltas[i]=np.mean([deltas[j] for j in close],axis=0)*factor
        matched[i]=weights[i]*(1-factor)+np.mean([matched[j] for j in close],axis=0)*factor
    visited|=following;front=following
for i in band:
    deltas[i]=np.zeros(3);matched[i]=weights[i]
for i,delta in deltas.items():
    obj.data.vertices[i].co=Vector(points[i]+delta)
    new=matched[i]/max(matched[i].sum(),1e-10)
    for name,w in zip(bones,new):
        group=obj.vertex_groups.get(name)
        if group:
            group.remove([i])
            if w>1e-8:group.add([i],float(w),'REPLACE')
obj.data.update()
for pb in rig.pose.bones:pb.matrix_basis.identity()
out='P:/FoA-Assets/character/mpfb/teen/foa_teen_wake_hem.blend'
bpy.ops.wm.save_as_mainfile(filepath=out)
print('HEM_REPAIR',len(deltas),'vertices',max(np.linalg.norm(d) for d in deltas.values())*100,'cm max displacement')
