"""Read-only dump of RTG_Mannequin_to_Teen and both IK rigs: chain bones, chain mapping, FK op settings per chain,
the target retarget pose offsets, root/pelvis. Writes Saved/RigShots/audit/rtg_dump.json.
  $env:FOA_AREAS='Characters'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/rtg_dump.py"""
import json

import unreal

P = "/Game/FoA/Characters/Player/Retarget/"
SOT = unreal.RetargetSourceOrTarget


def props(o, names):
    out = {}
    for n in names:
        try:
            v = o.get_editor_property(n)
        except Exception:  # property names move between engine versions
            continue
        out[n] = v if isinstance(v, (int, float, bool, str)) else str(v)
    return out


def rig_info(path):
    rig = unreal.load_asset(path)
    c = unreal.IKRigController.get_controller(rig)
    chains = []
    for ch in c.get_retarget_chains():
        name = str(ch.get_editor_property("chain_name"))
        chains.append({"name": name, "start": str(c.get_retarget_chain_start_bone(name)),
                       "end": str(c.get_retarget_chain_end_bone(name)), "goal": str(c.get_retarget_chain_goal(name))})
    return {"root": str(c.get_retarget_root()), "chains": chains, "mesh": str(c.get_skeletal_mesh().get_path_name())}


def run():
    out = {"source": rig_info(P + "IK_FoA_Mannequin"), "target": rig_info(P + "IK_FoA_Teen")}
    rtg = unreal.load_asset(P + "RTG_Mannequin_to_Teen")
    r = unreal.IKRetargeterController.get_controller(rtg)
    out["mapping"] = {ch["name"]: str(r.get_source_chain(ch["name"])) for ch in out["target"]["chains"]}
    out["ops"] = []
    for i in range(r.get_num_retarget_ops()):
        name = str(r.get_op_name(i))
        op = {"name": name, "enabled": r.get_retarget_op_enabled(i)}
        oc = r.get_op_controller(i)
        s = oc.get_settings() if oc else None
        if s is not None and name == "FK Chains":
            op["chains"] = [props(ch, ("target_chain_name", "enable_fk", "rotation_mode", "rotation_alpha",
                                       "translation_mode", "translation_alpha")) for ch in s.get_editor_property("chains_to_retarget")]
        elif s is not None:
            op["settings"] = s.export_text()[:3000] if hasattr(s, "export_text") else str(s)[:3000]
        out["ops"].append(op)
    for side, sot in (("source", SOT.SOURCE), ("target", SOT.TARGET)):
        cur = str(r.get_current_retarget_pose_name(sot))
        offs = {}
        mesh = unreal.load_asset(out[side]["mesh"].split(".")[0])
        names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(
            unreal.AnimPoseExtensions.get_reference_pose(mesh.skeleton))]
        for b in names:
            q = r.get_rotation_offset_for_retarget_pose_bone(b, sot)
            if abs(q.w) < 0.99999:
                offs[b] = [q.x, q.y, q.z, q.w]
        out[side + "_retarget_pose"] = {"current": cur, "poses": [str(k) for k in r.get_retarget_poses(sot)],
                                        "root_offset": str(r.get_root_offset_in_retarget_pose(sot)), "rotation_offsets": offs}
    with open("P:/FoA/Saved/RigShots/audit/rtg_dump.json", "w") as f:
        json.dump(out, f, indent=1)
    print("RTG_DUMP", json.dumps(out["mapping"]), len(out["target_retarget_pose"]["rotation_offsets"]), "target offsets")


run()
