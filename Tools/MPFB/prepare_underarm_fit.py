"""Offline bounded inverse-skinning clearance solve for the existing underarm folds only."""
import sys,json
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from sleep_skin_contact import matrix
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');body=bpy.data.objects['Human'];shirt=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
points=np.array([v.co[:] for v in shirt.data.vertices]);after=points.copy();x,y,z=points.T
protected=(abs(x)<.20)&(y<-.055)&(z<1.48)
select=(abs(x)>.13)&(abs(x)<.26)&(abs(y)<.10)&(z>1.30)&(z<1.49)&~protected
ids=np.flatnonzero(select);assert len(ids)>20
for m in body.modifiers:
    if m.type in ('MASK','SUBSURF'):m.show_viewport=False
skin=body.vertex_groups['body'].index;valid={v.index for v in body.data.vertices if any(g.group==skin and g.weight>0 for g in v.groups)}
tri=[tuple(f.vertices) for f in body.data.polygons if all(i in valid for i in f.vertices)]
ref=np.load('P:/FoA/Saved/WakeUp/teen_body_full_skin_cache.npz');references=dict(zip(ref['bone_names'].tolist(),ref['reference_matrices']))
B=np.diag((100,-100,100,1));records={}
for name in ('battle_command','battle_reach'):
    row=json.loads(Path('P:/FoA/Saved/Integration/cinematic_audit/live_'+name+'.json').read_text())['components']['Body']
    xf=lambda t:matrix(t['position'],t['rotation'],t['scale'])
    inv=np.linalg.inv(xf(row['world']));records[name]={key:inv@xf(v) for key,v in row['bones'].items()}
sleep=json.loads(Path('P:/FoA/Saved/CharacterShots/groom_pose/rigid_verified/body_pose.json').read_text())
records['accepted_sleep']={row['name']:matrix(row['position'],row['rotation'],row['scale']) for row in sleep['bones']}
records['rest']=references
cache={};group_names={g.index:g.name for g in shirt.vertex_groups if g.name in rig.pose.bones}
for name,posed in records.items():
    for bone in rig.pose.bones:
        key='root' if bone.name=='Root' else bone.name
        if key in references:
            D=posed[key]@np.linalg.inv(references[key]);bone.matrix=Matrix((np.linalg.inv(B)@D@B).tolist())@bone.bone.matrix_local
            bpy.context.view_layer.update()
    eb=body.evaluated_get(bpy.context.evaluated_depsgraph_get());bm=eb.to_mesh();tree=BVHTree.FromPolygons([v.co[:] for v in bm.vertices],tri);eb.to_mesh_clear()
    bone_mats={p.name:np.array(p.matrix@p.bone.matrix_local.inverted()) for p in rig.pose.bones}
    blends=np.array([sum((g.weight*bone_mats[group_names[g.group]] for g in shirt.data.vertices[int(i)].groups if g.group in group_names),np.zeros((4,4))) for i in ids])
    cache[name]=(tree,blends)
def measure(coords):
    result={}
    for name,(tree,mats) in cache.items():
        posed=np.einsum('nij,nj->ni',mats,np.c_[coords[ids],np.ones(len(ids))]);rows=[]
        for i,p in zip(ids,posed):
            q,n,_,_=tree.find_nearest(Vector(p[:3]));rows.append((int(i),float((Vector(p[:3])-q).dot(n))))
        result[name]=rows
    return result
before=measure(points)
for iteration in range(14):
    pushes=np.zeros_like(points);magnitudes=np.zeros(len(points))
    for name,(tree,mats) in cache.items():
        posed=np.einsum('nij,nj->ni',mats,np.c_[after[ids],np.ones(len(ids))])
        for j,(i,p) in enumerate(zip(ids,posed)):
            q,n,_,_=tree.find_nearest(Vector(p[:3]));gap=(Vector(p[:3])-q).dot(n)
            if gap>=.003:continue
            push=np.linalg.solve(mats[j,:3,:3],np.array(n)*(.003-gap))
            if np.linalg.norm(push)>magnitudes[i]:pushes[i]=push;magnitudes[i]=np.linalg.norm(push)
    after+=pushes*.65
    delta=after-points;length=np.linalg.norm(delta,axis=1);over=length>.020;delta[over]*=(.020/length[over])[:,None];after=points+delta
result=measure(after)
assert np.array_equal(after[~select],points[~select])
assert np.array_equal(after[protected],points[protected])
for bone in rig.pose.bones:bone.matrix_basis.identity()
shirt.data.vertices.foreach_set('co',after.astype('f4').ravel());shirt.data.update();bpy.context.view_layer.update()
dest='P:/FoA-Assets/character/mpfb/teen/foa_teen_underarm_review.blend';bpy.ops.wm.save_as_mainfile(filepath=dest)
report={'source':'foa_teen_shoulder_review.blend','variant':dest,'changed_vertices':len(ids),'max_shift_mm':float(np.linalg.norm(after-points,axis=1).max()*1000),
    'protected_chest_unchanged':True,'weights_bones_topology_unchanged':True,'poses':{name:{'before_min_mm':min(v for i,v in before[name])*1000,'after_min_mm':min(v for i,v in rows)*1000,'after_inward_over_2mm':sum(v<-.002 for i,v in rows)} for name,rows in result.items()}}
out=Path('P:/FoA/Saved/Integration/cinematic_audit/underarm_candidate');out.mkdir(exist_ok=True);(out/'change.json').write_text(json.dumps(report,indent=2));print('UNDERARM_CANDIDATE',report)
