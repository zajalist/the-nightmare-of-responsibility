"""Secondary motion for the hero's coat skirt, cape and hood tip: one AnimDynamics node per cloth bone chain.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_cloth.py FOA_ABP=/Game/FoA/Characters/Hero/Anims/ABP_FoAPlayer_Hero \n      FOA_MESH=/Game/FoA/Characters/Hero/SK_Hero
Chains are discovered from the mesh's bones (cloth_skirt_*, cloth_cape_*, cloth_hood_*): a chain starts at a cloth bone
whose parent is not a cloth bone and ends at its deepest cloth descendant. Nodes go in component space between the
head look-at and ComponentToLocal. Legs collide through spherical limits on thigh/calf, so the skirt cannot pass
through them. Chaos Cloth was the first choice, but its painted max-distance masks can't be authored from script;
AnimDynamics is cheap on low-end PCs and fully tunable here (shortcut: no cloth-to-cloth collision between chains)."""
import os
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
import importlib  # noqa: E402

import graph_style  # noqa: E402

importlib.reload(graph_style)
at, box, link = graph_style.at, graph_style.box, graph_style.link
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor
AP = unreal.AnimPoseExtensions
# per garment: (angular spring stiffness, angular damping, gravity scale, swing limit deg) - heavier coat = stiffer
TUNING = {"skirt": (120.0, 0.85, 1.0, 35.0), "cape": (60.0, 0.75, 1.0, 50.0), "hood": (200.0, 0.9, 0.6, 20.0)}
LEG_SPHERES = [("thigh_l", 11.0), ("thigh_r", 11.0), ("calf_l", 9.0), ("calf_r", 9.0)]


def chains(mesh):
    names = [str(n) for n in AP.get_bone_names(AP.get_reference_pose(mesh.get_editor_property("skeleton")))]
    mod = unreal.SkeletonModifier()
    mod.set_skeletal_mesh(mesh)
    parent = {n: str(mod.get_parent_name(n)) for n in names}
    cloth = [n for n in names if n.lower().startswith("cloth_")]
    out = []
    for root in (n for n in cloth if not parent.get(n, "").lower().startswith("cloth_")):
        end, frontier = root, [root]
        while frontier:  # deepest descendant along the chain
            kids = [n for n in cloth if parent.get(n) == frontier[0]]
            frontier = kids
            if kids:
                end = kids[0]
        kind = next((k for k in TUNING if k in root.lower()), "skirt")
        out.append((root, end, kind))
    return out


def setp(struct, names, value):
    for n in names:
        try:
            struct.set_editor_property(n, value)
            return n
        except Exception:
            continue
    raise AttributeError(f"none of {names} on {type(struct).__name__}")


def configure(node, root, end, kind):
    k, damp, grav, swing = TUNING[kind]
    ad = node.get_editor_property("node")
    setp(ad, ["bound_bone"], unreal.BoneReference(bone_name=root))
    setp(ad, ["chain_end"], unreal.BoneReference(bone_name=end))
    setp(ad, ["chain", "b_chain"], True)
    setp(ad, ["gravity_scale"], grav)
    setp(ad, ["angular_spring_constant"], k)
    setp(ad, ["angular_spring", "b_angular_spring"], True)
    setp(ad, ["angular_damping_override", "angular_damping"], damp)
    setp(ad, ["override_angular_damping", "b_override_angular_damping"], True)
    cons = ad.get_editor_property("constraint_setup")
    setp(cons, ["cone_angle"], swing)
    setp(cons, ["angular_constraint_type"], unreal.AnimPhysAngularConstraintType.CONE)
    ad.set_editor_property("constraint_setup", cons)
    if kind == "skirt":  # keep the coat skirt outside the legs
        lims = []
        for bone, radius in LEG_SPHERES:
            s = unreal.AnimPhysSphericalLimit()
            s.set_editor_property("driving_bone", unreal.BoneReference(bone_name=bone))
            s.set_editor_property("limit_radius", radius)
            s.set_editor_property("limit_type", unreal.SphericalLimitType.OUTER)
            lims.append(s)
        setp(ad, ["spherical_limits"], lims)
        setp(ad, ["use_spherical_limits", "b_use_spherical_limits"], True)
    node.set_editor_property("node", ad)


def run():
    abp = unreal.load_asset(os.environ["FOA_ABP"])
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(abp)
    found = chains(unreal.load_asset(os.environ["FOA_MESH"]))
    assert found, "no cloth_* bone chains on this skeleton yet"
    ed = BGE.get_graph_editor_by_name(abp, "AnimGraph")
    for n in ed.list_all_nodes():
        if BEL.get_node_title(n).startswith("Anim Dynamics"):
            ed.remove_nodes([n])
    look = next(n for n in ed.list_all_nodes() if BEL.get_node_title(n).startswith("Look At"))
    c2l = next(n for n in ed.list_all_nodes() if BEL.get_node_title(n).startswith("Component To Local"))
    x, y = BEL.get_node_pos(look).x + 260, BEL.get_node_pos(look).y + 260
    prev, made = look, []
    for i, (root, end, kind) in enumerate(found):
        n = at(ed.create_node_from_name("Animation|Dynamics|AnimDynamics", unreal.Vector2D(x + i * 260, y), []), x + i * 260, y)
        configure(n, root, end, kind)
        unreal.BlueprintGraphPinLibrary.break_pin_links(BEL.find_output_pin(prev, "Pose"))
        link(prev, "Pose", n, "ComponentPose")
        prev = n
        made.append(n)
    link(prev, "Pose", c2l, "ComponentPose")
    box(ed, "FoA: cloth dynamics", "AnimDynamics per cloth chain; skirt kept outside the legs by thigh/calf spheres.",
        made, "anim")
    unreal.EditorAssetLibrary.save_loaded_asset(abp, False)
    print("cloth chains:", found, "(compile with Hayba anim_blueprint_compile next)")


run()
