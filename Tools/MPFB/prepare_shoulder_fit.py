"""Reversible local shoulder/underarm smoothing; no rig, weights, collar or central-chest changes."""
import bpy,json,sys,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');body=bpy.data.objects['Human']
shirt=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
points=np.array([v.co[:] for v in shirt.data.vertices]);after=points.copy()
bones={b.name:tuple(v for row in b.matrix_local for v in row) for b in rig.data.bones}
weights=[[(g.group,g.weight) for g in v.groups] for v in shirt.data.vertices]
for mod in body.modifiers:
    if mod.type in ('MASK','SUBSURF'):mod.show_viewport=False
bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
skin=body.vertex_groups['body'].index
valid={v.index for v in body.data.vertices if any(g.group==skin and g.weight>0 for g in v.groups)}
tri=[tuple(f.vertices) for f in mesh.polygons if all(i in valid for i in f.vertices)]
tree=BVHTree.FromPolygons([v.co[:] for v in mesh.vertices],tri);ev.to_mesh_clear()
adj=[set() for v in points]
for e in shirt.data.edges:
    a,b=e.vertices;adj[a].add(b);adj[b].add(a)
remaining=set(range(len(points)));components=[]
while remaining:
    todo=[remaining.pop()];part=[]
    while todo:
        i=todo.pop();part.append(i);n=adj[i]&remaining;remaining-=n;todo.extend(n)
    components.append(part)
main=max(components,key=len);assert len(main)==1743
def smooth(a,b,x):
    q=np.clip((x-a)/(b-a),0,1);return q*q*(3-2*q)
x,y,z=points.T
mask=smooth(.13,.19,abs(x))*(1-smooth(.29,.34,abs(x)))*smooth(1.31,1.40,z)*(1-smooth(1.59,1.62,z))
# Keep the accepted front chest below the shoulder line completely unchanged.
protected=(abs(x)<.20)&(y<-.055)&(z<1.48)
mask[protected]=0;mask[[i for i in range(len(points)) if i not in main]]=0
for _ in range(8):
    proposed=after.copy()
    for i in np.flatnonzero(mask):
        target=after[list(adj[i])].mean(0);p=after[i]+.4*mask[i]*(target-after[i])
        q,n,_,d=tree.find_nearest(Vector(p))
        if q is not None and (Vector(p)-q).dot(n)<.005:p=np.array(q+n*.005)
        delta=p-points[i];length=np.linalg.norm(delta)
        if length>.010:delta*=.010/length
        proposed[i]=points[i]+delta
    after=proposed
# Keep measured reach and accepted sleeping clearance at least as good as the original.
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from sleep_skin_contact import matrix
ref=np.load('P:/FoA/Saved/WakeUp/teen_body_full_skin_cache.npz');references=dict(zip(ref['bone_names'].tolist(),ref['reference_matrices']))
conversion=np.diag((100,-100,100,1));guarded=set();guard_rows={}
records={}
for name in ('battle_command','battle_reach'):
    row=json.loads(Path('P:/FoA/Saved/Integration/cinematic_audit/live_'+name+'.json').read_text())['components']['Body']
    xf=lambda t:matrix(t['position'],t['rotation'],t['scale'])
    inv=np.linalg.inv(xf(row['world']));records[name]={key:inv@xf(v) for key,v in row['bones'].items()}
sleep=json.loads(Path('P:/FoA/Saved/CharacterShots/groom_pose/rigid_verified/body_pose.json').read_text())
records['accepted_sleep']={row['name']:matrix(row['position'],row['rotation'],row['scale']) for row in sleep['bones']}
changed=np.flatnonzero(mask)
for name,posed in records.items():
    for bone in rig.pose.bones:
        key='root' if bone.name=='Root' else bone.name
        if key in references:
            deform=posed[key]@np.linalg.inv(references[key])
            bone.matrix=Matrix((np.linalg.inv(conversion)@deform@conversion).tolist())@bone.bone.matrix_local
            bpy.context.view_layer.update()
    eb=body.evaluated_get(bpy.context.evaluated_depsgraph_get());bm=eb.to_mesh()
    posed_tree=BVHTree.FromPolygons([v.co[:] for v in bm.vertices],tri);eb.to_mesh_clear()
    def gaps(coords):
        shirt.data.vertices.foreach_set('co',coords.astype('f4').ravel());shirt.data.update();bpy.context.view_layer.update()
        es=shirt.evaluated_get(bpy.context.evaluated_depsgraph_get());sm=es.to_mesh();result={}
        for i in changed:
            p=sm.vertices[int(i)].co;q,n,_,_=posed_tree.find_nearest(p)
            result[int(i)]=(p-q).dot(n)
        es.to_mesh_clear();return result
    baseline=gaps(points);attempts=0
    for attempts in range(12):
        current=gaps(after);bad=[i for i in changed if current[i]<min(.002,baseline[i])-.0001]
        if not bad:break
        for i in bad:after[i]=points[i]+.5*(after[i]-points[i]);guarded.add(int(i))
    assert not bad,(name,bad)
    guard_rows[name]={'attempts':attempts,'min_before_mm':min(baseline.values())*1000,'min_after_mm':min(current.values())*1000}
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
delta=np.linalg.norm(after-points,axis=1)
assert np.array_equal(after[protected],points[protected])
assert np.max(delta)<=.0100001
shirt.data.vertices.foreach_set('co',after.astype('f4').ravel());shirt.data.update()
assert weights==[[(g.group,g.weight) for g in v.groups] for v in shirt.data.vertices]
assert bones=={b.name:tuple(v for row in b.matrix_local for v in row) for b in rig.data.bones}
dest='P:/FoA-Assets/character/mpfb/teen/foa_teen_shoulder_review.blend'
bpy.ops.wm.save_as_mainfile(filepath=dest)
out=Path('P:/FoA/Saved/Integration/cinematic_audit/shoulder_candidate');out.mkdir(exist_ok=True)
(out/'change.json').write_text(json.dumps(dict(source='foa_teen_chest_flattened.blend',variant=dest,
    changed_vertices=int(np.count_nonzero(delta>1e-8)),max_displacement_mm=float(delta.max()*1000),
    protected_chest_unchanged=True,weights_unchanged=True,bones_unchanged=True,topology_unchanged=True,
    clearance_guards=guard_rows,guarded_vertices=sorted(guarded)),indent=2))
print('wrote',dest,'changed',np.count_nonzero(delta>1e-8),'maxmm',delta.max()*1000)
