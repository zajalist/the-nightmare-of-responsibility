"""Read-only: channels and value ranges of each action in a garment blend."""
import bpy
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
print("ROTMODE", {pb.name: pb.rotation_mode for pb in arm.pose.bones})
print("ARMSCALE", tuple(arm.scale), "MESHPARENT", [(o.name, tuple(o.scale)) for o in bpy.data.objects if o.type == "MESH"])
for ac in bpy.data.actions:
    curves = []
    for layer in getattr(ac, "layers", []):
        for strip in layer.strips:
            for bag in strip.channelbags:
                curves += list(bag.fcurves)
    if not curves and hasattr(ac, "fcurves"):
        curves = list(ac.fcurves)
    rows = {}
    for fc in curves:
        vals = [k.co[1] for k in fc.keyframe_points]
        rows[f"{fc.data_path.split('\"')[1] if '\"' in fc.data_path else fc.data_path}.{fc.data_path.split('.')[-1]}[{fc.array_index}]"] = (round(min(vals), 3), round(max(vals), 3), len(vals))
    print("ACTION", ac.name, rows)
