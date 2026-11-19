"""Studio stage for character stills: neutral grey world, key/fill/rim area lights, one camera."""
import math

import bpy
from mathutils import Vector


def stage(engine="EEVEE", res=(900, 1100)):
    scn = bpy.context.scene
    if engine == "CYCLES":
        scn.render.engine = "CYCLES"
        scn.cycles.device = "GPU"
        scn.cycles.samples = 256
        scn.cycles.use_denoising = True
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
                for d in prefs.devices:
                    d.use = d.type != "CPU"
                break
            except TypeError:
                continue
    else:
        for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                scn.render.engine = eng
                break
            except TypeError:
                continue
        if hasattr(scn, "eevee"):
            scn.eevee.taa_render_samples = 64
    scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.film_transparent = False
    scn.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("TMP_world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.11, 0.11, 0.115, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    scn.world = world
    lights = (("key", (-2.3, -1.3, 2.3), 320, 1.0), ("fill", (1.9, -1.8, 1.4), 45, 2.0), ("rim", (1.2, 2.0, 2.4), 260, 0.8))
    for name, loc, watts, size in lights:
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.size = watts, size
        obj = bpy.data.objects.new(name, data)
        scn.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (Vector((0, 0, 1.2)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scn.collection.objects.link(cam)
    scn.camera = cam
    return cam


def shoot(cam, target, dist, yaw_deg, lens, path, lift=0.0):
    """Camera on a circle around `target` (yaw 0 = the character's front, 90 = his left side, 180 = back)."""
    yaw = math.radians(yaw_deg)
    cam.data.lens = lens
    cam.location = target + Vector((math.sin(yaw) * dist, -math.cos(yaw) * dist, lift))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("wrote", path)
