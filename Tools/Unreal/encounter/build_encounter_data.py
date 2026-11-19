"""Battle data: PDA_Move / PDA_Opponent (PrimaryDataAsset Blueprints) and their DA_ instances, from encounter_data.py.
  $env:FOA_AGENT='mech_encounter'; python Tools/Unreal/ue_remote.py Tools/Unreal/encounter/build_encounter_data.py
Why data assets and not DT_Moves/S_Move: neither editor Python nor Hayba can add fields to a UserDefinedStruct, so the
row "struct" is a Blueprint class and each row is a DA (same scheme as mech_flow's PDA_Beat). Idempotent: drops fields
that are gone, adds missing ones, creates missing DAs and rewrites every value from encounter_data.py."""
import importlib
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/encounter")
import encounter_data as D  # noqa: E402

importlib.reload(D)
BEL, GE, EAL = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor, unreal.EditorAssetLibrary
ROOT = "/Game/FoA/Gameplay/Encounter"
DATA = ROOT + "/Data"
GARMENTS = "/Game/FoA/Characters/Garments"  # the character lane's rigged enemies
T = {k: BEL.get_basic_type_by_name(k) for k in ("bool", "int", "name", "text", "real")}
STRUCT = {k: BEL.get_struct_type(s.static_struct()) for k, s in
          (("vec4", unreal.Vector4), ("xform", unreal.Transform), ("color", unreal.LinearColor))}


def blueprint(name):
    path = f"{ROOT}/{name}"
    bp = unreal.load_asset(path) if EAL.does_asset_exist(path) else \
        BEL.create_blueprint_asset_with_parent(path, unreal.PrimaryDataAsset)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    return bp


def ensure_vars(bp, category, specs, drop=()):
    ed = GE.get_graph_editor(BEL.find_event_graph(bp))
    have = {str(n) for n in BEL.list_member_variable_names(bp)}
    for name in drop:
        if name in have:
            ed.remove_member_variable(name)
    for name, t in specs:
        if name in have:
            cur = BEL.get_member_variable_type(bp, name)
            if BEL.pin_type_to_json_schema(cur, bp.generated_class()) != BEL.pin_type_to_json_schema(t, bp.generated_class()):
                ed.remove_member_variable(name)  # its type changed: re-add it
                have.discard(name)
        if name not in have:
            assert ed.add_member_variable(name, t, ""), name
        BEL.set_blueprint_variable_instance_editable(bp, name, True)
        BEL.set_blueprint_variable_category(bp, name, category)


def make_da(cls, name):
    path = f"{DATA}/{name}"
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    fac = unreal.DataAssetFactory()
    fac.set_editor_property("data_asset_class", cls)
    da = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, DATA, None, fac)
    assert da, f"create {name} failed"
    return da


def schema():
    """Structural: the PDA classes' fields. Then compile both with Hayba blueprint_compile before 'rows'."""
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()  # before structural edits
    move_bp, opp_bp = blueprint("PDA_Move"), blueprint("PDA_Opponent")
    ensure_vars(move_bp, "Move", [
        ("DisplayName", T["text"]), ("bOpponentMove", T["bool"]), ("ResolveCost", T["int"]),
        ("ComposureDelta", T["int"]), ("ResolveDelta", T["int"]), ("ProgressDelta", T["int"]),
        ("StatusApplied", T["name"]), ("StatusCleared", T["name"]), ("BlockedBy", T["name"]), ("BoostedBy", T["name"]),
        ("bTimedInput", T["bool"]), ("bRevealsNext", T["bool"]), ("bStuns", T["bool"]), ("bTelegraphed", T["bool"]),
        ("TelegraphLine", T["text"]), ("bSwapsTwin", T["bool"]), ("Narration", T["text"])], drop=("ButtonsDelta",))
    move_ref = BEL.get_object_reference_type(move_bp.generated_class())
    ensure_vars(opp_bp, "Opponent", [
        ("DisplayName", T["text"]), ("Level", T["int"]), ("Resistance", T["int"]), ("DrainPerTurn", T["int"]),
        ("StartComposure", T["int"]), ("StartResolve", T["int"]), ("ActMoves", BEL.get_array_type(move_ref)),
        ("PoolPlausible", BEL.get_array_type(move_ref)), ("PoolSuspicious", BEL.get_array_type(move_ref)),
        ("PoolOpen", BEL.get_array_type(move_ref)), ("PoolEnraged", BEL.get_array_type(move_ref)), ("OpeningMove", move_ref),
        ("KnowledgeFlag", T["name"]),
        ("Party", BEL.get_array_type(BEL.get_object_reference_type(opp_bp.generated_class()))),
        ("IntroLine", T["text"]), ("WinLine", T["text"]), ("LoseLine", T["text"]), ("VictoryLine", T["text"]),
        ("Mesh", BEL.get_object_reference_type(unreal.StaticMesh)), ("MeshTransform", STRUCT["xform"]),
        ("Tint", STRUCT["color"]), ("EquipSocket", T["name"]), ("GarmentId", T["name"]),
        ("Rig", BEL.get_object_reference_type(unreal.SkeletalMesh)),
        ("AttackAnim", BEL.get_object_reference_type(unreal.AnimSequenceBase))], drop=("WinButtons", "PlayerMoves", "MoveWeights"))
    print("schema ok: now Hayba blueprint_compile PDA_Move and PDA_Opponent")


def rows():
    """Data-asset writes, after the Hayba compile (never compile after these in the same session)."""
    move_cls = unreal.load_class(None, f"{ROOT}/PDA_Move.PDA_Move_C")
    opp_cls = unreal.load_class(None, f"{ROOT}/PDA_Opponent.PDA_Opponent_C")

    moves = {}
    for mid, m in D.MOVES.items():
        da = make_da(move_cls, f"DA_Move_{mid}")
        for k, v in m.items():
            if k == "Owner":
                da.set_editor_property("bOpponentMove", v == "Opponent")
            elif k in ("DisplayName", "Narration", "TelegraphLine"):
                da.set_editor_property(k, unreal.Text(v))
            else:
                da.set_editor_property(k, v)
        EAL.save_loaded_asset(da, False)
        moves[mid] = da
    opps = {oid: make_da(opp_cls, f"DA_Opponent_{oid}") for oid in D.OPPONENTS}
    for oid, o in D.OPPONENTS.items():
        da = opps[oid]
        for k, v in o.items():
            if k in ("DisplayName", "IntroLine", "WinLine", "LoseLine", "VictoryLine"):
                v = unreal.Text(v)
            elif k == "OpeningMove":
                v = moves[v] if v else None
            elif k == "ActMoves":
                v = [moves[x] for x in v]
            elif k == "Party":
                v = [opps[x] for x in v]
            elif k == "MoveWeights":  # weights become ticket pools, one per column: a random ticket is a weighted pick
                for col, field_name in enumerate(("PoolPlausible", "PoolSuspicious", "PoolOpen", "PoolEnraged")):
                    da.set_editor_property(field_name, [moves[mid] for mid, w in v.items() for _ in range(round(w[col] * 2))])
                continue
            elif k == "Mesh":
                v = unreal.load_asset(v)
            elif k == "MeshTransform":
                x, y, z, yaw, sx, sy, sz = v
                v = unreal.Transform(unreal.Vector(x, y, z), unreal.Rotator(roll=0, pitch=0, yaw=yaw),
                                     unreal.Vector(sx, sy, sz))
            elif k == "Tint":
                v = unreal.LinearColor(*v, 1.0)
            da.set_editor_property(k, v)
        rig_name, clip, xform = D.RIGS[oid]
        rig = unreal.load_asset(f"{GARMENTS}/{rig_name}") if EAL.does_asset_exist(f"{GARMENTS}/{rig_name}") else None
        anim = None
        if rig:  # the character lane's clips: <rig>..._<clip>, found by name so the take naming can vary
            for path in EAL.list_assets(GARMENTS, recursive=True, include_folder=False):
                a_name = path.rsplit(".", 1)[-1]
                if a_name.startswith(rig_name) and clip.lower() in a_name.lower():
                    a = unreal.load_asset(path)
                    if isinstance(a, unreal.AnimSequenceBase):
                        anim = a
                        break
            x, y, z, yaw, sx, sy, sz = xform
            da.set_editor_property("MeshTransform", unreal.Transform(
                unreal.Vector(x, y, z), unreal.Rotator(roll=0, pitch=0, yaw=yaw), unreal.Vector(sx, sy, sz)))
        da.set_editor_property("Rig", rig)
        da.set_editor_property("AttackAnim", anim)
        EAL.save_loaded_asset(da, False)
        print("opponent", oid, "rig", bool(rig), "anim", anim.get_name() if anim else None, "act", len(da.get_editor_property("ActMoves")), "weights",
              len(da.get_editor_property("PoolOpen")), "party", len(da.get_editor_property("Party")))
    print("moves:", len(moves))


import os  # noqa: E402
{'schema': schema, 'rows': rows}[os.environ.get('FOA_PHASE', 'schema')]()
