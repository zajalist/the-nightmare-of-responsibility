"""Read-only: armature, bones and actions of each garment blend. run_blender.ps1 -Blend <blend> garment_probe.py"""
import bpy
for o in bpy.data.objects:
    print("OBJ", o.name, o.type, tuple(round(x, 3) for x in o.dimensions), o.parent.name if o.parent else None)
for a in bpy.data.objects:
    if a.type == "ARMATURE":
        print("BONES", a.name, len(a.data.bones), [(b.name, b.parent.name if b.parent else None, round(b.length, 3)) for b in a.data.bones])
for ac in bpy.data.actions:
    print("ACTION", ac.name, tuple(ac.frame_range), len(ac.fcurves) if hasattr(ac, "fcurves") else "layered")
print("FPS", bpy.context.scene.render.fps)
