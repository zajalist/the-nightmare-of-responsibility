"""mech_core types: the interface, the two row structs, DT_Items and the empty class shells. Runs INSIDE the editor:
  python Tools/Unreal/ue_remote.py Tools/Unreal/gameplay/build_types.py FOA_STEP=shells|structs|cleanup|table
UE 5.8 Python cannot add struct members or implement interfaces, so two values are written with Hayba's generic
object_set_property (it reaches non-editable UPROPERTYs):
  - UserDefinedStructEditorData.VariablesDescriptions on S_*_Src (see STRUCTS below; `structs` prints the JSON),
  - Blueprint.ImplementedInterfaces on BP_Interactable (the next compile conforms the interface graphs).
Duplicating a struct runs FStructureEditorUtils::OnStructureChanged, which compiles the members from that data, so
`structs` duplicates S_*_Src to the real names and `cleanup` deletes the sources in a separate run."""
import json
import os
import uuid

import unreal

D = "/Game/FoA/Gameplay"
EAL, BEL = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
GE = unreal.BlueprintGraphEditor

# Member lists: (friendly name, pin category, default). softobject members compile as Soft Object (Object) refs,
# because the setter cannot write SubCategoryObject; the graphs cast after loading.
STRUCTS = {
    "S_Item": [("DisplayName", "text", ""), ("LookLine", "text", ""), ("Mesh", "softobject", ""),
               ("Icon", "softobject", ""), ("UsedBecomes", "name", "None"), ("CombineWith", "name", "None"), ("CombineInto", "name", "None")],
    "S_Interaction": [("Interactable", "name", "None"), ("State", "name", "None"), ("Verb", "name", "Use"),
                      ("Item", "name", "None"), ("Requires", "name", "None"), ("NextState", "name", "None"),
                      ("Prompt", "text", ""), ("Line", "text", ""), ("Give", "name", "None"), ("Event", "name", "None"),
                      ("Montage", "softobject", "")],
}
CLASSES = [("BP_Interactable", unreal.Actor), ("BPC_Interactor", unreal.ActorComponent),
           ("BPC_Inventory", unreal.ActorComponent)]
CHILDREN = ["BP_Pickup", "BP_Container", "BP_Door", "BP_Topple"]


def asset(name):
    p = f"{D}/{name}"
    return unreal.load_asset(p) if EAL.does_asset_exist(p) else None


def save(*objs):
    for o in objs:
        assert EAL.save_loaded_asset(o, False), o


def var_desc(struct, i, name, cat, default):
    guid = uuid.uuid5(uuid.NAMESPACE_URL, f"foa/{struct}/{name}").hex.upper()  # stable, so reruns name pins the same
    return {"VarName": f"{name}_{i}_{guid}", "VarGuid": guid, "FriendlyName": name, "Category": cat,
            "DefaultValue": default, "ToolTip": ""}


def step_shells():
    if not EAL.does_directory_exist(D):
        EAL.make_directory(D)
    for s in STRUCTS:
        src = asset(s + "_Src")
        if not src and not asset(s):
            src = AT.create_asset(s + "_Src", D, unreal.UserDefinedStruct, unreal.StructureFactory())
            save(src)
        if src:
            print("STRUCT_SRC", src.get_path_name())  # Hayba object_get_property names=[EditorData] gives the subobject
            print("VARS", s, json.dumps([var_desc(s, i, *m) for i, m in enumerate(STRUCTS[s])]))
    bpi = asset("BPI_Interactable")
    if not bpi:
        bpi = AT.create_asset("BPI_Interactable", D, unreal.Blueprint, unreal.BlueprintInterfaceFactory())
        name, text, boolean = (BEL.get_basic_type_by_name(t) for t in ("name", "text", "bool"))
        for fn, ins, outs in (("GetPrompt", [], [("Prompt", text)]),
                              ("CanInteract", [("Verb", name), ("HeldItem", name)], [("bCanInteract", boolean)]),
                              ("Interact", [("Verb", name), ("HeldItem", name)], []),
                              ("ResetForNewDay", [], [])):
            ed = GE.create_and_edit_function_graph(bpi, fn)
            for n, t in ins:
                ed.add_graph_input_parameter(n, t)
            for n, t in outs:
                ed.add_graph_output_parameter(n, t)
        BEL.compile_blueprint(bpi)
        save(bpi)
    for n, parent in CLASSES:
        if not asset(n):
            save(BEL.create_blueprint_asset_with_parent(f"{D}/{n}", parent))
    base = asset("BP_Interactable")
    for n in CHILDREN:
        if not asset(n):
            save(BEL.create_blueprint_asset_with_parent(f"{D}/{n}", base.generated_class()))
    step_input()
    print("shells ok", [str(g) for g in BEL.list_graph_names(bpi)])


def step_input():
    """IA_Interact (E, gamepad face bottom) and IA_CycleVerb (Q, gamepad face top) in the template's IMC_Default."""
    imc = unreal.load_asset("/Game/Input/IMC_Default")
    have = {(m.action.get_name() if m.action else "", str(m.key.key_name)) for m in imc.get_editor_property("mappings")}
    for ia_name, keys in (("IA_Interact", ("E", "Gamepad_FaceButton_Bottom")),
                          ("IA_CycleVerb", ("Q", "Gamepad_FaceButton_Top"))):
        path = f"/Game/Input/Actions/{ia_name}"
        ia = unreal.load_asset(path) if EAL.does_asset_exist(path) else AT.create_asset(
            ia_name, "/Game/Input/Actions", unreal.InputAction, unreal.InputAction_Factory())
        save(ia)
        for k in keys:
            if (ia_name, k) not in have:
                key = unreal.Key()
                key.import_text(k)
                imc.map_key(ia, key)
    save(imc)
    print("input ok", sorted((m.action.get_name(), str(m.key.key_name)) for m in imc.get_editor_property("mappings")
                             if m.action and m.action.get_name() in ("IA_Interact", "IA_CycleVerb", "IA_Jump")))


def step_structs():
    for s in STRUCTS:
        if not asset(s):
            dup = EAL.duplicate_asset(f"{D}/{s}_Src", f"{D}/{s}")
            assert dup, s
            save(dup)
        print("STRUCT", s, asset(s).get_path_name())


def step_cleanup():
    editors = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
    for s in STRUCTS:
        p = f"{D}/{s}_Src"
        if EAL.does_asset_exist(p):
            refs = EAL.find_package_referencers_for_asset(p, False)
            print(p, "referencers", refs)
            if not refs:
                editors.close_all_editors_for_asset(unreal.load_asset(p))
                print("deleted", p, EAL.delete_asset(p))


def fill(name, struct, rows):
    dt = asset(name)
    if not dt:
        f = unreal.DataTableFactory()
        f.set_editor_property("struct", asset(struct))
        dt = AT.create_asset(name, D, unreal.DataTable, f)
    ok = unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(dt, json.dumps(rows))
    save(dt)
    print(name, "filled", ok, len(unreal.DataTableFunctionLibrary.get_data_table_row_names(dt)), "rows")


def step_table():
    import importlib
    import sys
    sys.path.insert(0, "P:/FoA/Tools/Unreal/gameplay")
    import data_rows
    importlib.reload(data_rows)
    data_rows.check()
    fill("DT_Items", "S_Item", [{"Name": k, "DisplayName": n, "LookLine": look, "Mesh": mesh, "Icon": "", "UsedBecomes": used,
                                 "CombineWith": "None", "CombineInto": "None"}
                                for k, n, look, mesh, used in data_rows.ITEMS])
    rows = []
    for i, r in enumerate(data_rows.INTERACTIONS):  # row names keep table order readable; order is match priority
        rows.append(dict(r, Name=f"{i:03d}_{r['Interactable']}_{r['State']}_{r['Verb']}_{r['Item']}"))
    fill("DT_Interactions", "S_Interaction", rows)


def step_player():
    """BPC_Interactor + BPC_Inventory on the template character, so BP_FoAPlayer (its child) inherits them too.
    SCS only: no graph edits on another lane's Blueprint."""
    path = os.environ.get("FOA_PAWN", "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter")
    bp = unreal.load_asset(path)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    have = {str(lib.get_variable_name(lib.get_data(h))) for h in handles}
    for n in ("BPC_Interactor", "BPC_Inventory"):
        if n not in have:
            h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(
                parent_handle=handles[0], new_class=asset(n).generated_class(), blueprint_context=bp))
            assert not str(fail), fail
            sds.rename_subobject(h, n)
    BEL.compile_blueprint(bp)
    save(bp)
    print("player components", sorted(str(lib.get_variable_name(lib.get_data(h)))
                                       for h in sds.k2_gather_subobject_data_for_blueprint(bp)))


def step_host():
    """BPI_InteractionHost: the pawn that owns BPC_Interactor locks its own input for an interaction's montage.
    BPC_Interactor only sends the message, so it never references a Blueprint class (no load cycle)."""
    bpi = asset("BPI_InteractionHost")
    if not bpi:
        bpi = AT.create_asset("BPI_InteractionHost", D, unreal.Blueprint, unreal.BlueprintInterfaceFactory())
        ed = GE.create_and_edit_function_graph(bpi, "LockForInteraction")
        ed.add_graph_input_parameter("Seconds", BEL.get_basic_type_by_name("real"))
        BEL.compile_blueprint(bpi)
        save(bpi)
    # Target: the interactable, so the host can turn onto it (anim lane's stand-in for motion warping)
    ed = GE.get_graph_editor_by_name(bpi, "LockForInteraction")
    entry = unreal.BlueprintGraphPinLibrary.get_owning_node(ed.find_graph_entry_pin())
    if "Target" not in [str(unreal.BlueprintGraphPinLibrary.get_pin_name(p)) for p in BEL.list_output_pins(entry)]:
        unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bpi)
        ed.add_graph_input_parameter("Target", BEL.get_object_reference_type(unreal.Actor))
        BEL.compile_blueprint(bpi)
        save(bpi)
    print("host", [str(g) for g in BEL.list_graph_names(bpi)],
          [str(unreal.BlueprintGraphPinLibrary.get_pin_name(p)) for p in BEL.list_output_pins(entry)])


{"shells": step_shells, "player": step_player, "host": step_host, "structs": step_structs, "cleanup": step_cleanup,
 "table": step_table}[os.environ.get("FOA_STEP", "shells")]()
