"""Reconstruct captured UE pose on source garment for a flat-material deformation diagnostic."""
import sys,json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from sleep_skin_contact import matrix
sys.path.insert(0,'P:/FoA/Tools/MPFB')
from stage import stage
pose=json.loads(Path('P:/FoA/Saved/CharacterShots/sleep_side/20261108_015347/body_pose.json').read_text())
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
C=np.diag([1,-1,1,1])
for row in pose['bones']:
    name=row['name'] if row['name']!='root' else 'root'
    if name not in rig.pose.bones:continue
    transform=C@matrix(row['position'],row['rotation'],row['scale'])@C
    transform[:3,3]/=100
    rig.pose.bones[name].matrix=Matrix(transform.tolist())
    bpy.context.view_layer.update()
mat=bpy.data.materials.new('TMP_flat');mat.diffuse_color=(.5,.5,.5,1);mat.use_nodes=True
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.75
for obj in bpy.data.objects:
    if obj.type=='MESH':
        obj.data.materials.clear();obj.data.materials.append(mat)
        for p in obj.data.polygons:p.material_index=0
cam=stage(res=(1000,700))
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=24;sc.cycles.use_denoising=True
sc.render.threads_mode='FIXED';sc.render.threads=8
shirt=next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
ev=shirt.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
pts=np.array([v.co[:] for v in me.vertices]);ev.to_mesh_clear()
target=Vector(pts.mean(0));cam.location=target+Vector((2.1,-.5,.4));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=55
sc.render.filepath='P:/FoA/Saved/CharacterShots/mpfb/sleep_shirt_flat.png';bpy.ops.render.render(write_still=True)
print('wrote',sc.render.filepath)
