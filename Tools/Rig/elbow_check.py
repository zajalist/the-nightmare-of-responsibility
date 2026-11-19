"""Is the step at the elbow the polo sleeve hem or the skin? Measures, at rest, where the right sleeve's open hem sits
along the upper arm (fraction shoulder->elbow, and cm above the elbow), the sleeve hem radius vs the skin radius just
below it, and the skin radius just above and below the elbow joint. Read-only.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/elbow_check.py"""
import json
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(__file__))
import fbx_io  # noqa: E402

X = "P:/FoA-Assets/character/mpfb/export/"
fbx_io.clear()
rig, (body,) = fbx_io.load(X + "teen_rigfix/SK_Teen_Body.fbx")
_, (polo,) = fbx_io.load(X + "teen_polo_drape/SK_Teen_Polo.fbx")
bpy.context.view_layer.update()
inv = rig.matrix_world.inverted()
sh, el, wr = (rig.data.bones[n].head_local for n in ("upperarm_r", "lowerarm_r", "hand_r"))
ua = (el - sh)
fa = (wr - el)


def radius_at(obj, origin, axis, t0, t1):
    """Mean distance from the bone axis of the vertices whose projection lies in [t0, t1] cm along axis from origin."""
    d = axis.normalized()
    rs = []
    for v in obj.data.vertices:
        p = inv @ (obj.matrix_world @ v.co)
        t = (p - origin).dot(d)
        if t0 <= t <= t1:
            r = ((p - origin) - d * t).length
            if r < 9:
                rs.append(r)
    return round(sum(rs) / len(rs), 2) if rs else None


bm = bmesh.new()
bm.from_mesh(polo.data)
hem = [inv @ (polo.matrix_world @ e.verts[0].co) for e in bm.edges if e.is_boundary]
bm.free()
arm = [p for p in hem if (p - sh).dot(ua.normalized()) > 3 and ((p - sh) - ua.normalized() * (p - sh).dot(ua.normalized())).length < 10 and p.x < 0]
t_hem = sum((p - sh).dot(ua.normalized()) for p in arm) / len(arm)
out = {
    "upperarm_len_cm": round(ua.length, 1),
    "sleeve_hem_from_shoulder_cm": round(t_hem, 1),
    "sleeve_hem_above_elbow_cm": round(ua.length - t_hem, 1),
    "sleeve_radius_at_hem_cm": radius_at(polo, sh, ua, t_hem - 1.5, t_hem),
    "skin_radius_just_below_hem_cm": radius_at(body, sh, ua, t_hem + 0.5, t_hem + 2.5),
    "skin_radius_upperarm_5cm_above_elbow": radius_at(body, el, -ua, 4, 6),
    "skin_radius_forearm_5cm_below_elbow": radius_at(body, el, fa, 4, 6),
}
print("ELBOW", json.dumps(out))
json.dump(out, open("P:/FoA/Saved/RigShots/audit/elbow_check.json", "w"), indent=1)
