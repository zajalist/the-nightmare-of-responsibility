"""Export just the repaired shirt with the same centimetre-native FBX contract."""
import os,sys
import bpy
from mathutils import Matrix
sys.path.insert(0,os.path.dirname(__file__))
from export_ue import export_fbx,export_textures
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
obj=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
for p in rig.pose.bones:p.matrix_basis.identity()
rig.location=(0,0,0)
for m in list(obj.modifiers):
    if m.type in ('SUBSURF','MASK','DATA_TRANSFER','NODES'):obj.modifiers.remove(m)
if obj.data.shape_keys:obj.shape_key_clear()
for g in list(obj.vertex_groups):
    if g.name.startswith(('Layer.','Ride.','Delete.')):obj.vertex_groups.remove(g)
rig.data.bones['Root'].name='root';rig.name=rig.data.name='Armature'
scale=Matrix.Scale(100,4);rig.data.transform(scale);obj.data.transform(scale);obj.location*=100
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=.01
bpy.context.view_layer.update()
out=os.environ.get('FOA_POLO_EXPORT_DIR','P:/FoA-Assets/character/mpfb/export/teen_hem')
os.makedirs(out+'/textures',exist_ok=True)
export_textures(obj,'Polo',out)
export_fbx(rig,obj,out+'/SK_Teen_Polo.fbx')
print('wrote',out+'/SK_Teen_Polo.fbx')
