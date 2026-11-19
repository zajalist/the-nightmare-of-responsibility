"""Read-only: for every Teen finger/thumb phalanx (both hands), which LOCAL bone axis it curls about in UE and the sign
that curls it toward the palm, measured on the imported SK_Teen_Body reference pose (component space):
  hinge = d x toward_palm (d = bone -> child joint); local = inverse(bone rotation) * hinge.
Writes Saved/RigShots/audit/finger_axes.json.
  $env:FOA_AREAS='Characters'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/finger_axes.py"""
import json

import unreal

mesh = unreal.load_asset("/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body")
AP = unreal.AnimPoseExtensions
ref = AP.get_reference_pose(mesh.skeleton)
comp = unreal.SkeletalMeshComponent()
comp.set_skeletal_mesh_asset(mesh)
names = [str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]
refs = [comp.get_ref_pose_transform(i) for i in range(len(names))]


def world(b):
    t = unreal.Transform()
    while b in names:
        t = unreal.MathLibrary.compose_transforms(t, refs[names.index(b)])
        b = str(comp.get_parent_bone(b))
    return t


V = unreal.Vector
out = {"bones": len(names), "twist": [n for n in names if "twist" in n], "axes": {}}
for s in "lr":
    W = {b: world(f"{b}_{s}") for b in ["hand"] + [f"{f}_0{k}" for f in ("thumb", "index", "middle", "ring", "pinky") for k in (1, 2, 3)]}
    loc = {b: t.translation for b, t in W.items()}
    k = (loc["pinky_01"] - loc["index_01"]).normal()
    fd = (loc["middle_02"] - loc["middle_01"]).normal()
    n = k.cross(fd).normal()
    if (loc["thumb_03"] - (loc["index_01"] + loc["pinky_01"]) * 0.5).dot(n) < 0:
        n = n * -1.0
    palm = (loc["hand"] + loc["index_01"] + loc["pinky_01"] + loc["middle_01"]) * 0.25 + n * 1.2
    for f in ("thumb", "index", "middle", "ring", "pinky"):
        for j in (1, 2, 3):
            b = f"{f}_0{j}"
            nxt = loc[f"{f}_0{j + 1}"] if j < 3 else loc[b] + (loc[b] - loc[f"{f}_02"])
            d = (nxt - loc[b]).normal()
            toward = n if f != "thumb" else (palm - loc[b])
            toward = (toward - d * toward.dot(d)).normal()
            h = d.cross(toward).normal()
            hl = W[b].rotation.unrotate_vector(h)
            comps = {"X": hl.x, "Y": hl.y, "Z": hl.z}
            ax = max(comps, key=lambda a: abs(comps[a]))
            sign = "+" if comps[ax] > 0 else "-"
            # FQuat(axis, +a) curls; FRotator equivalents: Roll+ = quat about -X, Pitch+ = about -Y, Yaw+ = about +Z
            rot = {"X": "Roll", "Y": "Pitch", "Z": "Yaw"}[ax]
            rsign = ("-" if sign == "+" else "+") if ax in "XY" else sign
            out["axes"][f"{b}_{s}"] = {"curl_axis": sign + ax, "frotator_curl": f"{rot} {rsign}",
                                       "purity": round(abs(comps[ax]), 4),
                                       "along_bone_axis": max({"X": abs(W[b].rotation.unrotate_vector(d).x),
                                                               "Y": abs(W[b].rotation.unrotate_vector(d).y),
                                                               "Z": abs(W[b].rotation.unrotate_vector(d).z)}.items(), key=lambda kv: kv[1])[0]}
def same(q1, q2):
    return abs(abs(q1.x * q2.x + q1.y * q2.y + q1.z * q2.z + q1.w * q2.w) - 1) < 1e-4


r30 = 0.5235988  # self-check of the FRotator mapping used above
out["frotator_check"] = {
    "Roll+30 == quat(-X,30)": same(unreal.Rotator(roll=30, pitch=0, yaw=0).quaternion(), unreal.Quat.from_axis_and_angle(V(-1, 0, 0), r30)) if hasattr(unreal.Quat, "from_axis_and_angle") else None,
    "Pitch+30 == quat(-Y,30)": same(unreal.Rotator(roll=0, pitch=30, yaw=0).quaternion(), unreal.Quat.from_axis_and_angle(V(0, -1, 0), r30)) if hasattr(unreal.Quat, "from_axis_and_angle") else None,
    "Yaw+30 == quat(+Z,30)": same(unreal.Rotator(roll=0, pitch=0, yaw=30).quaternion(), unreal.Quat.from_axis_and_angle(V(0, 0, 1), r30)) if hasattr(unreal.Quat, "from_axis_and_angle") else None}
json.dump(out, open("P:/FoA/Saved/RigShots/audit/finger_axes.json", "w"), indent=1)
print("FINGER_AXES", out["frotator_check"], out["bones"], out["twist"], json.dumps({b: v["curl_axis"] + "/" + str(v["purity"]) for b, v in out["axes"].items()}))
