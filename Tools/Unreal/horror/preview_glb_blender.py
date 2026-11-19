"""Offline turnaround of a Lux3D GLB in Blender (horror lane monster pick): front, three-quarter and side, with a
hard key from below-left, the way the jumpscare lights it.
  blender -b --factory-startup -P Tools/Unreal/horror/preview_glb_blender.py -- <in.glb> <out_prefix>"""
import math
import sys

import bpy
from mathutils import Vector

src, out = sys.argv[sys.argv.index('--') + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
centre, size = (lo + hi) / 2, max(hi - lo)
print('BOUNDS', [round(v, 3) for v in lo], [round(v, 3) for v in hi], 'tris',
      sum(len(o.data.polygons) for o in meshes))
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items} else 'BLENDER_EEVEE'
scene.render.resolution_x, scene.render.resolution_y = 640, 800
scene.world = bpy.data.worlds.new('w')
scene.world.color = (0.01, 0.01, 0.01)
key = bpy.data.objects.new('key', bpy.data.lights.new('key', 'AREA'))
key.data.energy, key.data.size = 400 * size * size, size
scene.collection.objects.link(key)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
cam.data.lens = 50
scene.collection.objects.link(cam)
scene.camera = cam
# glTF is +Y up in file, Blender imports it Z-up with the model facing -Y
for name, ang in (('front', 0), ('threeq', 35), ('side', 90)):
    a = math.radians(ang)
    d = Vector((math.sin(a), -math.cos(a), 0.05)) * size * 2.2
    cam.location = centre + d
    cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
    key.location = centre + Vector((-0.6 * size, -1.2 * size, -0.4 * size))
    key.rotation_euler = (centre - key.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = f'{out}_{name}.png'
    bpy.ops.render.render(write_still=True)
