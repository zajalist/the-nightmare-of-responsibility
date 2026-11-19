"""Offline: bake ambient occlusion and curvature (Cycles pointiness) of the Lux3D jumpscare bust into its own UV
space, and export its base colour and metal/rough textures, for make_monster_maps.py.
  blender -b --factory-startup -P Tools/Unreal/horror/bake_monster_maps_blender.py -- <in.glb> <out_dir>
Writes <out_dir>/bc_src.png, mr_src.png, ao.png, curv.png, pos.png (1024, linear; pos = the bounding-box-normalised
object position, Blender axes: X right, Y back (front is -Y), Z up)."""
import os
import sys

import bpy

src, out = sys.argv[sys.argv.index('--') + 1:][:2]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
mat = obj.active_material
nt = mat.node_tree
for n in nt.nodes:  # export the embedded textures as they are
    if n.type == 'TEX_IMAGE' and n.image:
        links = [l.to_socket.name for l in n.outputs['Color'].links] + [l.to_node.type for l in n.outputs['Color'].links]
        tag = 'bc_src' if 'Base Color' in links else 'mr_src'
        img = n.image.copy()
        img.filepath_raw = f'{out}/{tag}.png'
        img.file_format = 'PNG'
        img.save()
        print('saved', tag, n.image.size[:], links)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 64
bpy.context.view_layer.objects.active = obj
obj.select_set(True)


def bake(name, kind, setup=None):
    img = bpy.data.images.new(name, 1024, 1024, float_buffer=False, is_data=True)
    node = nt.nodes.new('ShaderNodeTexImage')
    node.image = img
    nt.nodes.active = node
    restore = setup() if setup else None
    bpy.ops.object.bake(type=kind, margin=8)
    if restore:
        restore()
    img.filepath_raw = f'{out}/{name}.png'
    img.file_format = 'PNG'
    img.save()
    nt.nodes.remove(node)
    print('baked', name)


def emission(node_type, socket):
    """Temporarily route one geometry output into an Emission output for an EMIT bake."""
    outn = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    old = [l.from_socket for l in outn.inputs['Surface'].links]
    geo = nt.nodes.new(node_type)
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(geo.outputs[socket], em.inputs['Color'])
    nt.links.new(em.outputs['Emission'], outn.inputs['Surface'])

    def restore():
        if old:
            nt.links.new(old[0], outn.inputs['Surface'])
        nt.nodes.remove(geo)
        nt.nodes.remove(em)
    return restore


bake('ao', 'AO')
bake('curv', 'EMIT', lambda: emission('ShaderNodeNewGeometry', 'Pointiness'))
bake('pos', 'EMIT', lambda: emission('ShaderNodeTexCoord', 'Generated'))
