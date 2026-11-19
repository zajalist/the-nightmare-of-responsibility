"""Post-process ABP for SK_Teen_Body: the forearm twist bones take 60% of the hand's roll about the forearm
("Apply a Percentage of Rotation", the UE mannequin's own twist setup). The Manny clips carry no twist-bone keys
(Saved/RigShots/audit/twist_check.json) and put the whole roll on the hand (up to 90 deg in the phone hold), so the
twist has to come from the hand. Idempotent; edits only ABP_FoA_TeenPost and SK_Teen_Body's post-process slot.
  $env:FOA_AREAS='Characters'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/build_twist_post.py FOA_PHASE=graph|assign"""
import os

import unreal

T = "/Game/FoA/Characters/Teen"
PATH = T + "/Anim/ABP_FoA_TeenPost"
E, BEL, BGE, PIN = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor, unreal.BlueprintGraphPinLibrary
SHARE = 0.6


def palette(ed, *parts):
    norm = lambda s: str(s).replace(" ", "").replace("_", "").lower()  # noqa: E731
    found = [str(n) for n in ed.list_available_nodes([]) if all(norm(p) in norm(n) for p in parts)]
    assert found, parts
    return min(found, key=len)


def node_of(ed, cls):
    return [n for n in ed.list_all_nodes() if n.get_class().get_name() == cls]


def graph():
    body = unreal.load_asset(T + "/Mesh/SK_Teen_Body")
    bp = unreal.load_asset(PATH)
    if not bp:
        f = unreal.AnimBlueprintFactory()
        f.set_editor_property("target_skeleton", body.skeleton)
        f.set_editor_property("parent_class", unreal.AnimInstance)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset("ABP_FoA_TeenPost", T + "/Anim", unreal.AnimBlueprint, f)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    ed = BGE.get_graph_editor_by_name(bp, "AnimGraph")
    root = node_of(ed, "AnimGraphNode_Root")[0]
    inp = (node_of(ed, "AnimGraphNode_LinkedInputPose") or [ed.create_node_from_name(palette(ed, "InputPose"), unreal.Vector2D(-900, 0), [])])[0]
    l2c = (node_of(ed, "AnimGraphNode_LocalToComponentSpace") or [ed.create_node_from_name(palette(ed, "LocalToComponent"), unreal.Vector2D(-650, 0), [])])[0]
    c2l = (node_of(ed, "AnimGraphNode_ComponentToLocalSpace") or [ed.create_node_from_name(palette(ed, "ComponentToLocal"), unreal.Vector2D(150, 0), [])])[0]
    rms = node_of(ed, "AnimGraphNode_RotationMultiplier")
    while len(rms) < 2:
        rms.append(ed.create_node_from_name(palette(ed, "Percentage", "Rotation"), unreal.Vector2D(-400 + 280 * len(rms), 0), []))
    for rm, s in zip(rms, "lr"):
        n = rm.get_editor_property("node")
        for prop, bone in (("source_bone", f"hand_{s}"), ("target_bone", f"lowerarm_twist_01_{s}")):
            ref = unreal.BoneReference()
            ref.set_editor_property("bone_name", bone)
            n.set_editor_property(prop, ref)
        n.set_editor_property("multiplier", SHARE)
        n.set_editor_property("rotation_axis_to_refer", unreal.BoneAxis.BA_Y)
        n.set_editor_property("is_additive", False)
        rm.set_editor_property("node", n)
        # Multiplier is an exposed pin: the compiler takes the PIN default, not the struct value (that left it at 0)
        pin = BEL.find_input_pin(rm, "Multiplier")
        assert pin and PIN.set_pin_value(pin, str(SHARE)) is not False, "Multiplier pin"
    chain = [(inp, "Pose", l2c, "LocalPose"), (l2c, "ComponentPose", rms[0], "ComponentPose"),
             (rms[0], "Pose", rms[1], "ComponentPose"), (rms[1], "Pose", c2l, "ComponentPose"), (c2l, "Pose", root, "Result")]
    for nd in (inp, l2c, rms[0], c2l, root):
        print(nd.get_class().get_name(), [(str(PIN.get_pin_name(p)), str(PIN.get_pin_direction(p))[-6:]) for p in BEL.list_all_pins(nd)][:8])
    for a, pa, b, pb in chain:
        out, into = BEL.find_output_pin(a, pa), BEL.find_input_pin(b, pb)
        assert out and into, (a.get_class().get_name(), pa, b.get_class().get_name(), pb)
        if into not in list(PIN.list_connected_pins(out)):
            PIN.break_pin_links(into)
            assert PIN.try_create_connection(out, into), (pa, pb)
    for i, nd in enumerate([inp, l2c, rms[0], rms[1], c2l, root]):
        BEL.set_node_pos(nd, unreal.IntPoint(-1000 + 300 * i, 0))
    for c in list(ed.list_comment_nodes()):
        ed.remove_comment_node(c)
    c = ed.add_comment_to_nodes("Forearm twist", [inp, l2c, rms[0], rms[1], c2l], 48)
    BEL.set_comment_color(c, unreal.LinearColor(0.30, 0.22, 0.10, 1))
    for flag in ("comment_bubble_visible_in_details_panel", "show_bubble_when_zoomed", "color_bubble"):
        try:
            c.set_editor_property(flag, True)
        except Exception:  # flag names differ between engine versions; the title alone still reads
            pass
    E.save_loaded_asset(bp, False)
    print("TWIST_POST graph ready; compile with Hayba anim_blueprint_compile", PATH)


def assign():
    body = unreal.load_asset(T + "/Mesh/SK_Teen_Body")
    bp = unreal.load_asset(PATH)
    old = body.get_editor_property("post_process_anim_blueprint")
    print("previous post-process ABP:", old)
    body.set_editor_property("post_process_anim_blueprint", bp.generated_class())
    E.save_loaded_asset(body, False)
    print("TWIST_POST assigned", body.get_editor_property("post_process_anim_blueprint"))


{"graph": graph, "assign": assign}[os.environ.get("FOA_PHASE", "graph")]()
