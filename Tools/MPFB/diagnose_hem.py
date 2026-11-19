"""Read-only hem weight continuity report on the layered shirt."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils.kdtree import KDTree
obj=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
bones=[b.name for b in rig.data.bones if b.use_deform]
index={v.index:bones.index(v.name) for v in obj.vertex_groups if v.name in bones}
weights=np.zeros((len(obj.data.vertices),len(bones)))
points=np.array([v.co[:] for v in obj.data.vertices])
for v in obj.data.vertices:
    for g in v.groups:
        if g.group in index:weights[v.index,index[g.group]]=g.weight
tree=KDTree(len(points))
for i,p in enumerate(points):tree.insert(p,i)
tree.balance();seams=[]
for i,p in enumerate(points):
    for co,j,d in tree.find_range(p,.0002):
        if j>i:
            difference=float(np.abs(weights[i]-weights[j]).sum())
            if difference>.01:seams.append({'a':i,'b':j,'z':float(p[2]),'weight_difference':difference})
edges=[]
for e in obj.data.edges:
    i,j=e.vertices
    if max(points[i,2],points[j,2])>1.12:continue
    difference=float(np.abs(weights[i]-weights[j]).sum())
    if difference>.4:edges.append({'a':int(i),'b':int(j),'distance_cm':float(np.linalg.norm(points[i]-points[j])*100),
        'weight_difference':difference,'a_weights':{b:float(w) for b,w in zip(bones,weights[i]) if w>.01},
        'b_weights':{b:float(w) for b,w in zip(bones,weights[j]) if w>.01}})
adj=[set() for p in points]
for e in obj.data.edges:
    i,j=e.vertices;adj[i].add(j);adj[j].add(i)
remaining=set(range(len(points)));components=[]
while remaining:
    todo=[remaining.pop()];component=[]
    while todo:
        i=todo.pop();component.append(i)
        neighbors=adj[i]&remaining;remaining-=neighbors;todo.extend(neighbors)
    pc=points[component]
    components.append({'count':len(component),'indices':component,'minimum':pc.min(0).tolist(),'maximum':pc.max(0).tolist()})
edge_faces={tuple(sorted(e.vertices)):0 for e in obj.data.edges}
for face in obj.data.polygons:
    for edge in face.edge_keys:edge_faces[tuple(sorted(edge))]+=1
boundary=[edge for edge,count in edge_faces.items() if count==1]
badj={}
for a,b in boundary:badj.setdefault(a,set()).add(b);badj.setdefault(b,set()).add(a)
left=set(badj);loops=[]
while left:
    todo=[left.pop()];vertices=[]
    while todo:
        i=todo.pop();vertices.append(i);neighbors=badj[i]&left;left-=neighbors;todo.extend(neighbors)
    pc=points[vertices];loops.append({'count':len(vertices),'indices':vertices,'minimum':pc.min(0).tolist(),'maximum':pc.max(0).tolist(),'mean':pc.mean(0).tolist()})
report={'boundary_loops':loops,'components':sorted(components,key=lambda x:-x['count']),'coincident_weight_discontinuities':sorted(seams,key=lambda x:-x['weight_difference']),
    'hem_edge_discontinuities':sorted(edges,key=lambda x:-x['weight_difference'])}
Path('P:/FoA/Saved/CharacterShots/mpfb/hem_weights.json').write_text(json.dumps(report,indent=2))
print('HEM_DIAGNOSTIC',len(seams),len(edges),report['hem_edge_discontinuities'][:5])
