import bpy
import json
obj = next(o for o in bpy.data.objects if o.type == 'MESH' and 'short01' in o.name)
me=obj.data
adj={v.index:set() for v in me.vertices}
for e in me.edges:
    a,b=e.vertices
    adj[a].add(b);adj[b].add(a)
remaining=set(adj)
islands=[]
while remaining:
    todo=[remaining.pop()]; island=set(todo)
    while todo:
        for n in adj[todo.pop()] & remaining:
            remaining.remove(n);island.add(n);todo.append(n)
    islands.append(island)
uv=me.uv_layers.active.data
print('CARDS',len(me.vertices),len(me.polygons),'islands',len(islands))
for island in sorted(islands,key=len,reverse=True)[:10]:
    pts=[uv[i].uv for p in me.polygons if p.vertices[0] in island for i in p.loop_indices]
    print('CARD',len(island),'uv_bounds',[(min(v[k] for v in pts),max(v[k] for v in pts)) for k in (0,1)])
