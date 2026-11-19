"""Offline clothed chest inspection; leaves source blend and Unreal untouched."""
import sys,json
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,'P:/FoA/Tools/MPFB')
from stage import stage,shoot
out=Path('P:/FoA/Saved/CharacterShots/chest_review');out.mkdir(parents=True,exist_ok=True)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for p in rig.pose.bones:p.matrix_basis.identity()
shirt=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
for o in bpy.data.objects:
 o.hide_render=o!=shirt
mat=bpy.data.materials.new('TMP_chest_clay');mat.diffuse_color=(.34,.38,.40,1)
mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.34,.38,.40,1);bs.inputs['Roughness'].default_value=.85
for i in range(len(shirt.data.materials)):shirt.data.materials[i]=mat
cam=stage(res=(720,720));cam.hide_render=False
for o in bpy.data.objects:
 if o.type=='LIGHT':o.hide_render=False
p=np.array([v.co[:] for v in shirt.data.vertices]);mask=(p[:,2]>1.2)&(p[:,2]<1.5)&(abs(p[:,0])<.18)&(p[:,1]<0)
report={'source':bpy.data.filepath,'shirt_bounds':[p.min(0).tolist(),p.max(0).tolist()],'front_chest_bounds':[p[mask].min(0).tolist(),p[mask].max(0).tolist()],'shape_keys':[(k.name,k.value) for k in shirt.data.shape_keys.key_blocks] if shirt.data.shape_keys else [],'modifiers':[(m.name,m.type) for m in shirt.modifiers]}
(out/'inspection.json').write_text(json.dumps(report,indent=2))
for label,yaw in [('front',0),('profile',90),('threequarter',40)]:shoot(cam,Vector((0,0,1.32)),1.35,yaw,70,str(out/('before_'+label+'.png')))
