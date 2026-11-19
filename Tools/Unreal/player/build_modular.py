"""Modular garments on BP_FoAPlayer: the bare mannequin plus one Leader Pose skeletal mesh component per garment slot.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_modular.py FOA_STEP=components|graphs
Slots (contract.md): Shirt, Trousers, Socks, Tie, Suit. Each is a SkeletalMeshComponent under the body mesh, tagged
"Garment" and its slot name, empty and hidden until the character lane assigns a mesh. Equip(GarmentId) shows the
slot (tag lookup, no switch), plays AM_FoA_Equip and a black-sand burst; UnequipAll() hides every garment.
On a fresh player, declare build_starter_coverage.py and C++ compile before graphs/equip; its body runs afterwards.
The authored MetaHuman Body drives the garment pose; the inherited mannequin mesh is not its leader."""
import importlib
import os
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
import graph_style  # noqa: E402

importlib.reload(graph_style)
at, box, link, pin_in, value = graph_style.at, graph_style.box, graph_style.link, graph_style.pin_in, graph_style.value
P = "/Game/FoA/Characters/Player"
BP_PATH = P + "/BP_FoAPlayer"
SLOTS = ("Shirt", "Trousers", "Socks", "Tie", "Suit")
SAND_LIB = "/Game/FoA/VFX/Sand/BPL_SandFX"  # sandvfx lane function library
SAND_SCALE = "1.0"  # ~40 cm per unit
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
PIN = unreal.BlueprintGraphPinLibrary
BGE = unreal.BlueprintGraphEditor


def bp_closed():
    bp = unreal.load_asset(BP_PATH)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    return bp


def step_components():
    bp = bp_closed()
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    by_name = {str(lib.get_variable_name(lib.get_data(h))): h for h in handles}
    mesh_h = by_name.get("Mesh") or by_name.get("CharacterMesh0")
    assert mesh_h, f"no body mesh handle: {sorted(by_name)}"
    for slot in SLOTS:
        if slot not in by_name:
            params = unreal.AddNewSubobjectParams(parent_handle=mesh_h, new_class=unreal.SkeletalMeshComponent, blueprint_context=bp)
            h, fail = sds.add_new_subobject(params)
            assert not str(fail), fail
            sds.rename_subobject(h, slot)
            by_name[slot] = h
        comp = lib.get_object_for_blueprint(lib.get_data(by_name[slot]), bp)
        comp.set_editor_property("component_tags", ["Garment", slot])
        comp.set_editor_property("visible", False)
        comp.set_collision_profile_name("NoCollision")  # clothing layers never block; the capsule does
    EAL.save_loaded_asset(bp, False)
    print("garment slots (compile with Hayba next):", [s for s in SLOTS if s in by_name])


def fresh_function(bp, name):
    return graph_style.function_graph(bp, name)[0]


def entry(ed):
    return unreal.BlueprintGraphPinLibrary.get_owning_node(ed.find_graph_entry_pin())


def call(ed, path, x, y):
    n = ed.add_call_function_node(path)
    assert n and BEL.get_node_title(n), f"empty call node (bad function path?): {path}"
    return at(n, x, y)


def palette(ed, *needles):
    hits = [str(a) for a in ed.list_available_nodes([]) if all(n in str(a) for n in needles)]
    assert hits, f"no palette node with {needles}"
    return min(hits, key=len)


def slot_chain(ed, fn_path, x, y, setup):
    """One call per garment slot, chained on exec (no ForEach macro: script-made macro nodes crashed the editor).
    setup(node, slot) sets the per-call pins. Returns (first, last, nodes)."""
    nodes, prev = [], None
    for i, slot in enumerate(SLOTS):
        g = at(ed.add_get_member_variable_node(slot, ""), x + i * 300, y + 200)
        c = call(ed, fn_path, x + i * 300, y)
        link(g, slot, c, "self")
        setup(c, slot)
        if prev:
            link(prev, None, c, None)
        prev = c
        nodes += [g, c]
    return nodes[1], prev, nodes


def step_graphs():
    bp = bp_closed()
    me = bp.generated_class().get_path_name()
    name_t = BEL.get_basic_type_by_name("name")
    # SpawnSandBurst(Location): optional sandvfx actor, skipped quietly until that lane ships it.
    ed = graph_style.function_graph(bp, "SpawnSandBurst", [("Location", BEL.get_struct_type(unreal.Vector.static_struct()))])[0]
    e = at(entry(ed), 0, 0)
    # sandvfx: BPL_SandFX.SpawnSandBurst(Location, Scale) from a pooled manager. Wired only if the library exists at
    # build time; until then this stays an empty, commented function (re-run this step once sandvfx ships it).
    lib = unreal.load_asset(SAND_LIB)
    members = [e]
    if lib:
        burst = call(ed, lib.generated_class().get_path_name() + ":SpawnSandBurst", 300, 0)
        link(e, None, burst, None)
        link(e, "Location", burst, "Location")
        value(burst, "Scale", SAND_SCALE)
        members.append(burst)
    box(ed, "Black-sand burst", "sandvfx BPL_SandFX.SpawnSandBurst" + ("" if lib else " (not shipped yet: no-op; re-run to wire)"), members, "util")
    # UnequipAll(): every garment hidden (new day).
    ed = fresh_function(bp, "UnequipAll")
    e = at(entry(ed), 0, 0)
    first, last, nodes = slot_chain(ed, "/Script/Engine.SceneComponent:SetVisibility", 280, 0,
                                    lambda c, slot: value(c, "bNewVisibility", "false"))
    link(e, None, first, None)
    restore = graph_style.self_call(ed, "SetSuitedBody", 1900, 0)
    value(restore, "bEnable", "false")
    link(last, None, restore, None)
    boots = graph_style.self_call(ed, "SetBootsWorn", 2220, 0)
    value(boots, "bEnable", "false")
    link(restore, None, boots, None)
    coverage = graph_style.self_call(ed, "RefreshStarterCoverage", 2540, 0)
    link(boots, None, coverage, None)
    box(ed, "Unequip all", "", [e] + nodes + [restore, boots, coverage], "state")
    # BeginPlay addition: garments follow the body's pose (Leader Pose: one skeleton evaluation for all layers).
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    begin = next(n for n in ed.list_all_nodes() if BEL.get_node_title(n).startswith("Event BeginPlay"))
    bx, by = BEL.get_node_pos(begin).x, BEL.get_node_pos(begin).y
    timers = [n for n in ed.list_all_nodes() if BEL.get_node_title(n).startswith("Set Timer by Function Name")]
    timer = max(timers, key=lambda n: BEL.get_node_pos(n).x)  # the last timer in the BeginPlay chain
    body = at(ed.add_get_member_variable_node("Body", ""), bx + 1000, by + 420)
    first, last, nodes = slot_chain(ed, "/Script/Engine.SkinnedMeshComponent:SetLeaderPoseComponent", bx + 1000, by, lambda c, slot: None)
    for c in nodes[1::2]:
        link(body, "Body", c, "NewLeaderBoneComponent")
    link(timer, None, first, None)
    box(ed, "Garments follow the body", "Every garment slot uses the body mesh as its Leader Pose component.", nodes + [body], "anim")
    EAL.save_loaded_asset(bp, False)
    print("garment graphs saved (compile with Hayba, then FOA_STEP=equip)")


def step_equip():
    """Needs SpawnSandBurst and PlayInteraction on the generated class: run after a Hayba compile."""
    bp = bp_closed()
    name_t = BEL.get_basic_type_by_name("name")
    # Equip(GarmentId): show the tagged slot, snap beat, sand burst at the chest.
    ed = graph_style.function_graph(bp, "Equip", [("GarmentId", name_t)])[0]
    e = at(entry(ed), 0, 0)
    get = call(ed, "/Script/Engine.Actor:GetComponentsByTag", 280, 200)
    value(get, "ComponentClass", "/Script/Engine.SkeletalMeshComponent")
    link(e, "GarmentId", get, "Tag")
    first = at(ed.create_node_from_name(palette(ed, "Utilities|Array|Get"), unreal.Vector2D(560, 200), []), 560, 200)
    vis = call(ed, "/Script/Engine.SceneComponent:SetVisibility", 760, 0)
    value(vis, "bNewVisibility", "true")
    link(get, "ReturnValue", first, "Array")  # palette "Get" is the by-ref variant: pins Array, Dimension 1 (index 0)
    outs = [str(PIN.get_pin_name(x)) for x in BEL.list_output_pins(first)]
    link(first, "Output" if "Output" in outs else outs[0], vis, "self")
    is_suit = call(ed, "/Script/Engine.KismetMathLibrary:EqualEqual_NameName", -500, 200)
    branch = at(ed.add_branch_node(), -250, 0)
    suited = graph_style.self_call(ed, "SetSuitedBody", 0, -300)
    value(is_suit, "B", "Suit")
    value(suited, "bEnable", "true")
    link(e, "GarmentId", is_suit, "A")
    link(is_suit, "ReturnValue", branch, "Condition")
    link(e, None, branch, None)
    link(branch, "Then", suited, None)
    link(suited, None, vis, None)
    link(branch, "Else", vis, None)
    nodes = [get, first, vis, is_suit, branch, suited]
    coverage = graph_style.self_call(ed, "RefreshStarterCoverage", 1000, 0)
    loc = call(ed, "/Script/Engine.Actor:K2_GetActorLocation", 1000, 220)
    burst = graph_style.self_call(ed, "SpawnSandBurst", 1320, 0)
    beat = graph_style.self_call(ed, "PlayInteraction", 1640, 0)
    value(beat, "Montage", P + "/Montages/AM_FoA_Equip.AM_FoA_Equip")
    link(vis, None, coverage, None)
    link(coverage, None, burst, None)
    link(loc, "ReturnValue", burst, "Location")
    link(burst, None, beat, None)
    box(ed, "Equip garment", "Show the slot tagged GarmentId (Shirt, Trousers, Socks, Tie, Suit), burst sand, play the snap beat.",
        [e] + nodes + [coverage, loc, burst, beat], "state")
    EAL.save_loaded_asset(bp, False)
    print("Equip saved (compile with Hayba next)")


def step_hair():
    """GroomComponent "Hair" under the body mesh; FOA_GROOM / FOA_BINDING are the character lane's groom + binding."""
    bp = bp_closed()
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    by_name = {str(lib.get_variable_name(lib.get_data(h))): h for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
    if "Hair" not in by_name:
        params = unreal.AddNewSubobjectParams(parent_handle=by_name["Mesh"], new_class=unreal.GroomComponent, blueprint_context=bp)
        h, fail = sds.add_new_subobject(params)
        assert not str(fail), fail
        sds.rename_subobject(h, "Hair")
        by_name["Hair"] = h
    hair = lib.get_object_for_blueprint(lib.get_data(by_name["Hair"]), bp)
    for prop, env in (("groom_asset", "FOA_GROOM"), ("binding_asset", "FOA_BINDING")):
        if os.environ.get(env):
            hair.set_editor_property(prop, unreal.load_asset(os.environ[env]))
    EAL.save_loaded_asset(bp, False)
    print("hair slot ready (compile with Hayba next):", hair.get_editor_property("groom_asset"))


{"components": step_components, "graphs": step_graphs, "equip": step_equip, "hair": step_hair}[os.environ["FOA_STEP"]]()
