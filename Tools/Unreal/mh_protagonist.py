"""Build the protagonist MetaHuman in short stages (each one ue_remote run, inside the editor lock).

  python Tools/Unreal/ue_remote.py Tools/Unreal/mh_protagonist.py FOA_STEP=<step>

Steps (follow Epic's examples in Engine/Plugins/MetaHuman/MetaHumanCharacter/Content/Python/examples):
  create  - create /Game/FoA/Characters/Protagonist/MHC_Protagonist, list the body constraints, hair grooms
            and presets that the installed Core Data offers
  body    - sturdy average adult man: height 180 cm plus FOA_BODY="name=value;..." constraint targets
  hair    - add groom FOA_GROOM (a WI_Hair_* wardrobe item path), dark (Melanin FOA_MELANIN, default 0.9)
  skin    - skin tone / roughness (the face gets the erosion material later, so keep it plain)
  rig     - face auto-rig (Epic cloud, blocking), joints only
  build   - Optimized assembly at FOA_QUALITY (LOW/MEDIUM) into /Game/FoA/Characters/Protagonist/Built
  export  - DCC export (FBX + textures) to FOA_EXPORT_DIR for Blender (garment fit, review renders)
Nothing temporary is created; the character asset is the deliverable.
"""
import os
import unreal

PATH, NAME = "/Game/FoA/Characters/Protagonist", "MHC_Protagonist"
FULL = f"{PATH}/{NAME}"
SUB = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)


def scan(*paths):  # after an editor restart the registry may not list newer folders yet
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(list(paths), True)


def character():
    scan(PATH)
    if unreal.EditorAssetLibrary.does_asset_exist(FULL):
        return unreal.load_asset(FULL)
    return unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        asset_name=NAME, package_path=PATH, asset_class=unreal.MetaHumanCharacter,
        factory=unreal.new_object(type=unreal.MetaHumanCharacterFactoryNew))


def editing(ch, fn):
    if not SUB.try_add_object_to_edit(ch):
        raise RuntimeError("character is already open for edit (close its editor tab)")
    try:
        fn(ch)
    finally:
        if SUB.is_object_added_for_editing(ch):
            SUB.remove_object_to_edit(ch)
    unreal.EditorAssetLibrary.save_asset(FULL, only_if_is_dirty=False)


def list_assets(root, prefix):
    try:
        scan(root)
        return sorted(p for p in unreal.EditorAssetLibrary.list_assets(root, recursive=True)
                      if os.path.basename(p).split(".")[0].startswith(prefix))
    except Exception as e:
        return [f"<{e}>"]


def step_create(ch):
    cons = SUB.get_body_constraints(ch)
    print("MH_BODY_CONSTRAINTS", [(str(c.name), round(c.target_measurement, 1), round(c.min_measurement, 1),
                                   round(c.max_measurement, 1)) for c in cons])
    print("MH_GROOMS", list_assets("/MetaHumanCharacter/Optional/Grooms", "WI_Hair")[:60])
    print("MH_PRESETS", list_assets("/MetaHumanCharacter/Optional", "MHC_")[:60])
    print("MH_CAN_BUILD", SUB.can_build_meta_human(ch, True))


# sturdy, average adult man, 180 cm (cm; names as 5.8 reports them, lower-cased with underscores)
STURDY = {"height": 180.0, "chest": 108.0, "underbust": 100.0, "waist": 92.0, "hip": 104.0, "high_hip": 98.0,
          "neck_base": 45.0, "neck": 41.0, "thigh": 59.0, "knee": 39.0, "calf": 39.0, "bicep": 35.0, "elbow": 28.0,
          "forearm": 29.0, "wrist": 18.0, "across_shoulder": 47.0, "hand_circumference": 22.0}


def step_body(ch):
    cons = SUB.get_body_constraints(ch)
    by = {str(c.name).lower().replace(" ", "_"): c for c in cons}
    targets = dict(STURDY)
    for kv in filter(None, os.environ.get("FOA_BODY", "").split(";")):  # explicit overrides
        k, v = kv.split("=")
        targets[k.strip().lower()] = float(v)
    for k, c in by.items():  # only these drive the shape; everything else follows
        c.is_active = k in targets
        if k in targets:
            c.target_measurement = targets[k]
    for k in targets.keys() - by.keys():
        print("MH_BODY unknown constraint", k)
    SUB.set_body_constraints(ch, list(by.values()))
    SUB.commit_body_state(ch)
    got = {str(c.name): round(c.target_measurement, 1) for c in SUB.get_body_constraints(ch)}
    print("MH_BODY set", targets, "now", got)


HAIR_PREF = ("wi_hair_s_messy", "wi_hair_s_casual", "messy", "tousled", "shaggy", "unkempt", "wavy_short", "short_wavy", "curly_short", "short_curly",
             "medium", "short")


def pick_groom():
    want = os.environ.get("FOA_GROOM", "auto")
    if want != "auto":
        return want
    all_ = [p for p in list_assets("/MetaHumanCharacter/Optional/Grooms", "WI_Hair") if not p.startswith("<")]
    for kw in HAIR_PREF:
        hit = [p for p in all_ if kw in os.path.basename(p).lower()]
        if hit:
            return hit[0]
    if not all_:
        raise RuntimeError("no WI_Hair wardrobe items: is MetaHuman Creator Core Data installed?")
    return all_[0]


def step_hair(ch):
    path = pick_groom()
    os.environ["FOA_GROOM"] = path
    groom = unreal.load_asset(path)
    key = ch.internal_collection.try_add_item_from_wardrobe_item("Hair", groom)
    ch.internal_collection.default_instance.try_add_slot_selection(
        unreal.MetaHumanPipelineSlotSelection(slot_name="Hair", selected_item=key))

    def tint(c):
        SUB.assemble_for_preview(character=c)
        params = c.internal_collection.default_instance.get_instance_parameters(
            item_path=unreal.MetaHumanPaletteItemPath(item_key=key))
        mel = next((p for p in params if p.name == "Melanin"), None)
        if mel:
            mel.set_float(value=float(os.environ.get("FOA_MELANIN", "0.9")))
        print("MH_HAIR", os.environ["FOA_GROOM"], "melanin", bool(mel))
    return tint


def step_skin(ch):
    sp = unreal.MetaHumanCharacterSkinProperties()
    sp.u, sp.v = float(os.environ.get("FOA_SKIN_U", "0.45")), float(os.environ.get("FOA_SKIN_V", "0.55"))
    sp.roughness = 0.8
    ss = unreal.MetaHumanCharacterSkinSettings()
    ss.skin = sp
    ss.enable_texture_overrides = False
    SUB.commit_skin_settings(ch, ss)
    print("MH_SKIN", sp.u, sp.v)


def step_rig(ch):
    req = unreal.MetaHumanCharacterAutoRiggingRequestParams()
    req.blocking = True
    req.report_progress = False
    req.rig_type = unreal.MetaHumanRigType.JOINTS_ONLY
    SUB.request_auto_rigging(ch, req)
    print("MH_RIG requested (joints only); can_build now", SUB.can_build_meta_human(ch, True))


def step_textures(ch):
    """Download Texture Sources (Epic cloud, blocking): assembly refuses to run without them."""
    req = unreal.MetaHumanCharacterTextureRequestParams()
    req.blocking = True
    req.report_progress = False
    SUB.request_texture_sources(ch, req)
    print("MH_TEXTURES requested; can_build now", SUB.can_build_meta_human(ch, True))


def step_build(ch):
    bp = unreal.MetaHumanCharacterEditorBuildParameters()
    bp.pipeline_type = unreal.MetaHumanDefaultPipelineType.OPTIMIZED
    bp.pipeline_quality = getattr(unreal.MetaHumanQualityLevel, os.environ.get("FOA_QUALITY", "MEDIUM"))
    bp.absolute_build_path = f"{PATH}/Built"
    bp.common_folder_path = f"{PATH}/Common"
    print("MH_BUILD can_build", SUB.can_build_meta_human(ch, True))
    SUB.build_meta_human(character=ch, params=bp)
    print("MH_BUILD done", bp.absolute_build_path)


def step_export(ch):
    """DCC export (baked skin textures + DNA) for Blender, and geometry: the full-body skeletal mesh is the in-game
    mesh (Protagonist/Mesh, Manny-compatible MetaHuman skeleton; the face is hidden, so no face rig is needed);
    the body-only mesh goes to TMP_character_Geometry just to be written out as FBX for the garment refit.
    Both are written as FBX (LOD0, no morphs). Delete the TMP folder in a separate run: FOA_STEP=cleanup."""
    out = os.environ.get("FOA_EXPORT_DIR", "P:/FoA-Assets/character/metahuman")
    os.makedirs(out, exist_ok=True)  # the FBX exporter reports success but writes nothing into a missing folder
    if os.environ.get("FOA_DCC") == "1":  # needs the face rig and downloaded texture sources (cloud) first
        p = unreal.MetaHumanDCCExportParams()
        p.external_path = f"{out}/dcc"
        p.bake_make_up = True
        p.compress_in_zip_file = False
        p.archive_name = NAME
        unreal.MetaHumanCharacterExportBlueprintLibrary.export_dcc(ch, p)
        print("MH_EXPORT dcc", p.external_path)
    for folder, body, full in ((TMP_GEO, True, False), (f"{PATH}/Mesh", False, True)):
        gp = unreal.MetaHumanGeometryExportParams()
        gp.project_path = folder
        gp.head_skeletal_mesh = False
        gp.body_skeletal_mesh = body
        gp.full_body_skeletal_mesh = full
        gp.overwrite_existing_assets = True
        unreal.MetaHumanCharacterExportBlueprintLibrary.export_geometry(ch, gp)
        scan(folder)
        for a in unreal.EditorAssetLibrary.list_assets(folder, recursive=True):
            obj = unreal.load_asset(a)
            if not isinstance(obj, unreal.SkeletalMesh):
                continue
            t = unreal.AssetExportTask()
            t.object = obj
            t.filename = f"{out}/{obj.get_name()}.fbx"
            t.automated, t.prompt, t.replace_identical = True, False, True
            o = unreal.FbxExportOption()
            o.level_of_detail = False
            o.export_morph_targets = False
            t.options = o
            print("MH_EXPORT fbx", a, "->", t.filename, unreal.Exporter.run_asset_export_task(t))
            unreal.EditorAssetLibrary.save_asset(a.split(".")[0], only_if_is_dirty=False)


TMP_GEO = f"{PATH}/TMP_character_Geometry"


def cleanup():
    scan(TMP_GEO)
    ok = unreal.EditorAssetLibrary.delete_directory(TMP_GEO)
    print("MH_CLEANUP", TMP_GEO, ok)


def step_haircolor(ch):
    """Dark hair: list the groom's instance parameters and set the darkness one (Melanin or its 5.8 name)."""
    col, inst = ch.internal_collection, ch.internal_collection.default_instance
    print("MH_API collection", [a for a in dir(col) if not a.startswith("_") and ("item" in a or "slot" in a)])
    print("MH_API instance", [a for a in dir(inst) if not a.startswith("_") and ("item" in a or "slot" in a or "param" in a)])
    SUB.assemble_for_preview(character=ch)
    for key in col.get_item_keys_for_slot("Hair"):
        params = inst.get_instance_parameters(item_path=unreal.MetaHumanPaletteItemPath(item_key=key))
        print("MH_HAIRCOLOR", key, [str(p_.name) for p_ in params])
        for p_ in params:
            n = str(p_.name).lower()
            if "melanin" in n and "red" not in n:
                p_.set_float(value=float(os.environ.get("FOA_MELANIN", "0.92")))
                print("MH_HAIRCOLOR set", p_.name)


# wardrobe: (slot keyword, wardrobe item). Hair is already WI_Hair_S_Messy. Default garment = MHC's fitted crew-neck
# t-shirt (+ shorts; MHC 5.8 ships no long trousers, so the sleep pants come from our Lux3D shell on this body)
GROOMS = "/MetaHumanCharacter/Optional/Grooms/Bindings"
WARDROBE = [("eyebrow", f"{GROOMS}/Eyebrows/WI_Eyebrows_M_Thick.WI_Eyebrows_M_Thick"),
            ("beard", f"{GROOMS}/Beards/WI_Beard_S_Stubble.WI_Beard_S_Stubble"),
            ("eyelash", f"{GROOMS}/Eyelashes/WI_Eyelashes_S_Fine.WI_Eyelashes_S_Fine"),
            ("outfit", "/MetaHumanCharacter/Optional/Clothing/WI_DefaultGarment.WI_DefaultGarment")]
DARK = {"melanin": 0.9, "redness": 0.12}


def wardrobe():
    """Adds eyebrows, stubble, eyelashes and the default garment (outside an edit session, as Epic's examples do)."""
    ch = character()
    col, inst = ch.internal_collection, ch.internal_collection.default_instance
    slots = [str(x) for x in col.get_slot_names()]
    print("MH_SLOTS", slots)
    for kw, path in WARDROBE:
        slot = next((x for x in slots if kw in x.lower()), None)
        item = unreal.load_asset(path)
        if slot is None or item is None:
            print("MH_WARDROBE missing", kw, "slot", slot, "item", bool(item), path)
            continue
        if col.get_item_keys_for_wardrobe_item(item):
            print("MH_WARDROBE already", slot, path)
            continue
        key = col.try_add_item_from_wardrobe_item(slot, item)
        inst.try_add_slot_selection(unreal.MetaHumanPipelineSlotSelection(slot_name=slot, selected_item=key))
        print("MH_WARDROBE added", slot, path)

    def colour(c):
        SUB.assemble_for_preview(character=c)
        print("MH_SUB hair api", [a_ for a_ in dir(SUB) if any(k in a_.lower() for k in ("hair", "groom", "lash", "brow"))])
        for path in inst.get_instance_parameter_item_paths():
            params = inst.get_instance_parameters(item_path=path)
            names = [str(p_.name) for p_ in params]
            print("MH_PARAMS", path, names[:20])
            for p_ in params:
                n = str(p_.name).lower()
                if n in DARK:
                    p_.set_float(value=DARK[n])
                    print("MH_COLOUR set", n, DARK[n])
    editing(ch, colour)


def outfit():
    """Swap the Outfits slot to FOA_OUTFIT (default: the Fab 'MetaOutfits - Casual Wear - Male' t-shirt, pants,
    slippers), replacing MHC's default garment. Outside an edit session, like the other wardrobe edits."""
    ch = character()
    col, inst = ch.internal_collection, ch.internal_collection.default_instance
    item = unreal.load_asset(os.environ.get("FOA_OUTFIT", "/Game/Fab/MetaHuman/WI_Casual_M_Outfit.WI_Casual_M_Outfit"))
    keys = list(col.get_item_keys_for_wardrobe_item(item)) or [col.try_add_item_from_wardrobe_item("Outfits", item)]
    try:
        inst.set_single_slot_selection("Outfits", keys[0])
    except Exception as e:  # older signature: keyword arguments
        print("MH_OUTFIT positional failed", e)
        inst.set_single_slot_selection(slot_name="Outfits", item_key=keys[0])
    print("MH_OUTFIT selected", item.get_path_name(), "slot items now", len(col.get_item_keys_for_slot("Outfits")))
    editing(ch, lambda c: SUB.assemble_for_preview(character=c))


def run():
    step = os.environ.get("FOA_STEP", "create")
    if step == "cleanup":  # its own run: never delete in the run that loaded the assets
        return cleanup()
    if step == "wardrobe":
        return wardrobe()
    if step == "outfit":
        return outfit()
    if step == "save":  # after a build: write the Built and Common folders to disk
        for d in (f"{PATH}/Built", f"{PATH}/Common"):
            scan(d)
            print("MH_SAVE", d, unreal.EditorAssetLibrary.save_directory(d, only_if_is_dirty=False, recursive=True),
                  len(unreal.EditorAssetLibrary.list_assets(d, recursive=True)))
        return
    ch = character()
    print("MH_CHARACTER", ch.get_path_name() if ch else None, "step", step)
    if step == "hair":
        tint = step_hair(ch)  # wardrobe edits happen outside the edit session, as in Epic's example
        editing(ch, tint)
    else:
        editing(ch, {"create": step_create, "body": step_body, "skin": step_skin, "rig": step_rig,
                     "build": step_build, "export": step_export, "haircolor": step_haircolor,
                     "textures": step_textures}[step])


run()
