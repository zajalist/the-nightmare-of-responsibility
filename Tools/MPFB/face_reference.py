"""Read the current layered Blender reference landmarks without saving it."""
import json
import bpy
from mathutils import Vector
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
for pb in rig.pose.bones:
    pb.matrix_basis.identity()
body = bpy.data.objects['Human']
ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
mesh = ev.to_mesh()
points = [body.matrix_world @ v.co for v in mesh.vertices]
eye = next(o for o in rig.children if 'high-poly' in o.name)
eyes = [eye.matrix_world @ Vector(c) for c in eye.bound_box]
center = sum(eyes, Vector()) / len(eyes)
head = rig.data.bones['head']
print('FACE_REFERENCE', json.dumps({'eye_center_blender_m':list(center), 'head_matrix_blender': [list(row) for row in head.matrix_local],
      'face_points_front': [list(v) for v in points if abs(v.x) < 0.005 and v.z > center.z - .10 and v.y < center.y]}))
ev.to_mesh_clear()
for mod in body.modifiers:
    if mod.type == 'MASK':
        mod.show_viewport=False
bpy.context.view_layer.update()
ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
mesh=ev.to_mesh()
hand_group=body.vertex_groups['hand_r'].index
skin_group=body.vertex_groups['body'].index
weighted=[]
for v in body.data.vertices:
    groups={g.group:g.weight for g in v.groups}
    if groups.get(hand_group,0)>.7 and groups.get(skin_group,0)>0:
        weighted.append(rig.data.bones['hand_r'].matrix_local.inverted() @ mesh.vertices[v.index].co)
print('PALM_REFERENCE_LOCAL_METRES',list(sum(weighted,Vector())/len(weighted)), 'verts',len(weighted))
ev.to_mesh_clear()
