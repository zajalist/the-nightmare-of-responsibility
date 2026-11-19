"""Export only the portrait head; leave canonical body/outfit FBXs untouched."""
import json,sys
from pathlib import Path
import bpy
from mathutils import Matrix
sys.path.insert(0,'P:/FoA/Tools/MPFB')
from export_ue import bake_shape,drop_helpers,split_head,mpfb_type,HEAD_PARTS,export_fbx,export_textures

out=Path('P:/FoA-Assets/character/mpfb/export/teen_portrait_v1')
(out/'textures').mkdir(parents=True,exist_ok=True)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');body=bpy.data.objects['Human']
for p in rig.pose.bones:p.matrix_basis.identity()
rig.location=(0,0,0)
parts=[o for o in rig.children if o.type=='MESH' and (o is body or mpfb_type(o) in HEAD_PARTS)]
for obj in parts:
    for mod in list(obj.modifiers):
        if mod.type in ('SUBSURF','MASK','DATA_TRANSFER','NODES'):obj.modifiers.remove(mod)
    bake_shape(obj)
drop_helpers(body)
head=split_head(body,rig)
bpy.ops.object.select_all(action='DESELECT')
for obj in parts:
    if obj is not body:obj.select_set(True)
head.select_set(True);bpy.context.view_layer.objects.active=head
bpy.ops.object.join()
for vg in list(head.vertex_groups):
    if vg.name.startswith(('Delete.','Hidden_by.','Layer.','Ride.')):head.vertex_groups.remove(vg)
with bpy.context.temp_override(object=head,active_object=head,selected_objects=[head]):
    bpy.ops.object.material_slot_remove_unused()
head.material_slots[0].material.name='Skin'
rig.data.bones['Root'].name='root';rig.name=rig.data.name='Armature'
scale=Matrix.Scale(100,4);rig.data.transform(scale);head.data.transform(scale,shape_keys=True);head.location*=100
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=.01
bpy.context.view_layer.update()
export_textures(head,'Head',str(out));export_fbx(rig,head,str(out/'SK_Teen_Head.fbx'))
report={'source':bpy.data.filepath,'vertices':len(head.data.vertices),'polygons':len(head.data.polygons),
        'slots':[s.material.name for s in head.material_slots],
        'morphs':[k.name for k in head.data.shape_keys.key_blocks[1:]],'bones':len(rig.data.bones)}
assert len(report['morphs'])==52 and len(report['slots'])==6,report
(out/'manifest.json').write_text(json.dumps(report,indent=2))
print('wrote',out/'SK_Teen_Head.fbx',json.dumps(report))
