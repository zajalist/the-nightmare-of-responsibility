"""Prepare a chest-fit variant offline with measured body clearance; never imports it."""
import sys,json,hashlib
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,'P:/FoA/Tools/MPFB')
from stage import stage,shoot
out=Path('P:/FoA/Saved/CharacterShots/chest_review')
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for p in rig.pose.bones:p.matrix_basis.identity()
shirt=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'));body=bpy.data.objects['Human']
for m in body.modifiers:
 if m.type in ('MASK','SUBSURF'):m.show_viewport=False
bpy.context.view_layer.update()
e=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh()
skin=body.vertex_groups['body'].index
valid={v.index for v in body.data.vertices if any(g.group==skin and g.weight>0 for g in v.groups)}
tri=[tuple(p.vertices) for p in me.polygons if all(i in valid for i in p.vertices)]
bvh=BVHTree.FromPolygons([v.co[:] for v in me.vertices],tri)
e.to_mesh_clear()
p=np.array([v.co[:] for v in shirt.data.vertices]);after=p.copy();rows=[]
def smooth(a,b,v):
 t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
for i,(x,y,z) in enumerate(p):
 weight=float(smooth(1.22,1.32,z)*(1-smooth(1.45,1.53,z))*(1-smooth(.12,.18,abs(x)))*smooth(.02,.08,-y))
 if weight<=0:continue
 hit,normal,index,d=bvh.ray_cast(Vector((x,-1,z)),Vector((0,1,0)),2)
 if hit is None:continue
 gap=hit.y-y
 shift=min(.010*weight,max(0,gap-.004))
 after[i,1]+=shift;rows.append({'vertex':i,'before_gap_mm':gap*1000,'after_gap_mm':(gap-shift)*1000,'shift_mm':shift*1000})
assert rows
assert np.all(after[:,0]==p[:,0]) and np.all(after[:,2]==p[:,2])
assert np.max(np.abs(after-p))<=.010001
assert all(r['after_gap_mm']>=min(r['before_gap_mm'],4)-1e-6 for r in rows)
shirt.data.vertices.foreach_set('co',after.astype(np.float32).ravel());shirt.data.update()
dest='P:/FoA-Assets/character/mpfb/teen/foa_teen_chest_review.blend'
bpy.ops.wm.save_as_mainfile(filepath=dest)
report={'variant':dest,'changed_vertices':int(np.count_nonzero(after[:,1]-p[:,1])),'max_shift_mm':float(np.max(after[:,1]-p[:,1])*1000),'median_before_gap_mm':float(np.median([r['before_gap_mm'] for r in rows])),'minimum_after_gap_mm':min(r['after_gap_mm'] for r in rows),'body_and_rig_unchanged':True,'applied_to_unreal':False,'samples':rows}
(out/'variant_report.json').write_text(json.dumps(report,indent=2))
for o in bpy.data.objects:o.hide_render=o!=shirt
mat=bpy.data.materials.new('TMP_chest_review');mat.diffuse_color=(.34,.38,.40,1);mat.use_nodes=True
bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.34,.38,.40,1);bs.inputs['Roughness'].default_value=.85
for i in range(len(shirt.data.materials)):shirt.data.materials[i]=mat
cam=stage(res=(720,720));cam.hide_render=False
for o in bpy.data.objects:
 if o.type=='LIGHT':o.hide_render=False
for label,yaw in [('front',0),('profile',90),('threequarter',40)]:shoot(cam,Vector((0,0,1.32)),1.35,yaw,70,str(out/('after_'+label+'.png')))
print('CHEST_PREP',report['changed_vertices'],report['max_shift_mm'])
