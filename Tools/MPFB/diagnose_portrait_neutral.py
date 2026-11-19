import bpy,json,sys
sys.path.insert(0,'P:/FoA/Tools/MPFB')
from export_ue import FaceService,bake_shape
r=next(o for o in bpy.data.objects if o.type=='ARMATURE'); b=bpy.data.objects['Human']
print('ANIMATION',r.animation_data,[(p.name,list(p.matrix_basis.translation),list(p.rotation_euler),[(c.name,c.type) for c in p.constraints]) for p in r.pose.bones if p.matrix_basis != __import__('mathutils').Matrix.Identity(4)])
print('BEFORE',[(k.name,k.value) for k in b.data.shape_keys.key_blocks if k.value])
FaceService.load_targets(b,load_microsoft_visemes=False,load_arkit_faceunits=True);FaceService.interpolate_targets(b)
print('LOADED',[(k.name,k.value) for k in b.data.shape_keys.key_blocks if k.value])
for p in r.pose.bones:p.matrix_basis.identity()
bake_shape(b)
bpy.context.view_layer.update()
print('AFTER',[(k.name,k.value) for k in b.data.shape_keys.key_blocks if k.value],b.show_only_shape_key,b.active_shape_key_index)
print('MODIFIERS',[(m.name,m.type,m.show_viewport,m.show_render) for m in b.modifiers])
print('POSE',[(p.name,list(p.matrix_basis.translation),list(p.rotation_euler)) for p in r.pose.bones if p.matrix_basis != __import__('mathutils').Matrix.Identity(4)])
