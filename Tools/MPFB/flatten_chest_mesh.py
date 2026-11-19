"""Flatten the clothed chest locally, keeping bones, weights and the neck/hands untouched."""
import sys,json
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,'P:/FoA/Tools/MPFB')
from export_ue import bake_shape
from stage import stage,shoot
out=Path('P:/FoA/Saved/CharacterShots/chest_flattened');out.mkdir(parents=True,exist_ok=True)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for p in rig.pose.bones:p.matrix_basis.identity()
rest={b.name:tuple(v for row in b.matrix_local for v in row) for b in rig.data.bones}
body=bpy.data.objects['Human'];shirt=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
bake_shape(body)
def smooth(a,b,v):
 t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
report={}
for obj in (body,shirt):
 p=np.array([v.co[:] for v in obj.data.vertices]);x,y,z=p.T
 mask=smooth(1.04,1.20,z)*(1-smooth(1.44,1.57,z))*(1-smooth(.13,.20,abs(x)))*smooth(.025,.085,-y)
 delta=np.zeros_like(p);delta[:,1]=.025*mask
 assert np.max(delta)<=.025001
 assert not np.any(delta[(z<1.04)|(z>1.57)|(abs(x)>.20)])
 if obj.data.shape_keys:
  for key in obj.data.shape_keys.key_blocks:
   coords=np.array([v.co[:] for v in key.data]);key.data.foreach_set('co',(coords+delta).astype(np.float32).ravel())
 obj.data.vertices.foreach_set('co',(p+delta).astype(np.float32).ravel());obj.data.update()
 report[obj.name]={'changed_vertices':int(np.count_nonzero(mask)),'max_reduction_mm':float(delta[:,1].max()*1000)}
# Keep the shirt outside the now flatter skin at the edited front surface.
skin=body.vertex_groups['body'].index
valid={v.index for v in body.data.vertices if any(g.group==skin and g.weight>0 for g in v.groups)}
tri=[tuple(p.vertices) for p in body.data.polygons if all(i in valid for i in p.vertices)]
bvh=BVHTree.FromPolygons([v.co[:] for v in body.data.vertices],tri)
clearance=[]
for v in shirt.data.vertices:
 x,y,z=v.co
 if not(1.04<z<1.57 and abs(x)<.20 and y<-.025):continue
 hit,_,_,_=bvh.ray_cast(Vector((x,-1,z)),Vector((0,1,0)),2)
 if hit is not None:
  v.co.y=min(y,hit.y-.004);clearance.append(hit.y-v.co.y)
assert min(clearance)>.003999
assert rest=={b.name:tuple(v for row in b.matrix_local for v in row) for b in rig.data.bones}
shirt.data.update()
dest='P:/FoA-Assets/character/mpfb/teen/foa_teen_chest_flattened.blend'
bpy.ops.wm.save_as_mainfile(filepath=dest)
report.update(variant=dest,minimum_shirt_clearance_mm=min(clearance)*1000,skeleton_unchanged=True)
(out/'report.json').write_text(json.dumps(report,indent=2))
for o in bpy.data.objects:o.hide_render=o!=shirt
mat=bpy.data.materials.new('TMP_flat_chest');mat.use_nodes=True
bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.34,.38,.40,1);bs.inputs['Roughness'].default_value=.85
for i in range(len(shirt.data.materials)):shirt.data.materials[i]=mat
cam=stage(res=(720,720));cam.hide_render=False
for o in bpy.data.objects:
 if o.type=='LIGHT':o.hide_render=False
for label,yaw in [('profile',90),('threequarter',40)]:shoot(cam,Vector((0,0,1.32)),1.35,yaw,70,str(out/('after_'+label+'.png')))
print('wrote',dest)
