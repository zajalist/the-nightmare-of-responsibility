"""Read-only: rest head/tail world positions of each garment's bones (for axis design)."""
import bpy
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for b in arm.data.bones:
    h, t = arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local
    print("REST", b.name, tuple(round(x, 3) for x in h), tuple(round(x, 3) for x in (t - h).normalized()))
