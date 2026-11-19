"""Same-body teenage head. Short Creator steps; build is a separately coordinated heavy operation."""
import importlib
import os
import sys
import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal")
import mh_faces
importlib.reload(mh_faces)

PATH = "/Game/FoA/Characters/Protagonist/Faces/MHC_Face_N"
BUILD = "/Game/FoA/Characters/Protagonist/Teen/Built_N"
SOURCE = "/Game/FoA/Characters/Protagonist/MHC_Protagonist"
SUB = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
EAL = unreal.EditorAssetLibrary
STEP = os.environ.get("FOA_STEP", "status")
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), "Exit PIE before Creator work"

if STEP == "create":
    if not EAL.does_asset_exist(PATH):
        assert EAL.duplicate_asset(SOURCE, PATH), "Could not preserve original Creator asset"
    assert EAL.save_asset(PATH, False)
    print("TEEN created separate source; original body and player unchanged", PATH)
elif STEP == "face":
    os.environ["FOA_PRESERVE_BODY"] = "1"
    mh_faces.FACE = "N"
    mh_faces.face_path = lambda _face: PATH
    mh_faces.step_face()
    print("TEEN approved natural brown-haired reference committed; fitted body constraints unchanged")
elif STEP == "shoot":
    mh_faces.FACE = "N"
    mh_faces.face_path = lambda _face: PATH
    mh_faces.OUT = "P:/FoA/Saved/CharacterShots/reference_teen"
    mh_faces.WAIT = 8.0
    mh_faces.step_shoot()
elif STEP == "hair":
    ch = unreal.load_asset(PATH)
    if SUB.is_object_added_for_editing(ch):
        SUB.remove_object_to_edit(ch)
    col = ch.internal_collection
    mh_faces.FACE = "N"
    mh_faces.set_slot(col, col.default_instance, [str(x) for x in col.get_slot_names()],
                      "hair", mh_faces.DIRS["N"]["hair"])
    mh_faces.edit(ch)
    try:
        SUB.assemble_for_preview(character=ch)
        mh_faces.set_melanin(ch)
        assert EAL.save_loaded_asset(ch, False)
    finally:
        mh_faces.done(ch)
    print("TEEN shorter dark curly fade saved; face rig/body unchanged")
else:
    ch = unreal.load_asset(PATH)
    assert ch, "Run create/face first"
    if not SUB.is_object_added_for_editing(ch):
        assert SUB.try_add_object_to_edit(ch)
    if STEP == "rig":
        # Reopening a rigged source restores cached DNA; apply edited proportions before regenerating it.
        SUB.commit_body_state(ch)
        request = unreal.MetaHumanCharacterAutoRiggingRequestParams()
        request.blocking = False
        request.report_progress = True
        request.rig_type = unreal.MetaHumanRigType.JOINTS_ONLY
        SUB.request_auto_rigging(ch, request)
        print("TEEN asynchronous auto-rig requested; Creator session retained until completion")
    elif STEP == "textures":
        request = unreal.MetaHumanCharacterTextureRequestParams()
        request.blocking = False
        request.report_progress = True
        SUB.request_texture_sources(ch, request)
        print("TEEN asynchronous texture sources requested; Creator session retained")
    elif STEP == "build":
        assert SUB.can_build_meta_human(ch, True), "Rig/textures must finish before assembly"
        params = unreal.MetaHumanCharacterEditorBuildParameters()
        params.pipeline_type = unreal.MetaHumanDefaultPipelineType.OPTIMIZED
        params.pipeline_quality = unreal.MetaHumanQualityLevel.MEDIUM
        params.absolute_build_path = BUILD
        params.common_folder_path = "/Game/FoA/Characters/Protagonist/Common"
        SUB.build_meta_human(ch, params)
        print("TEEN assembly returned; validate output before replacing player Face")
    elif STEP == "materials":
        assert SUB.can_build_meta_human(ch, True)
        params = unreal.MetaHumanMaterialsExportParams()
        params.project_path = BUILD
        params.apply_as_overrides = True
        unreal.MetaHumanCharacterExportBlueprintLibrary.export_materials(ch, params)
        assert EAL.save_loaded_asset(ch, False)
        print("TEEN persistent material export returned; inspect outputs before runtime assignment")
    elif STEP == "body_export":
        params = unreal.MetaHumanGeometryExportParams()
        params.project_path = BUILD + "/Body"
        params.head_skeletal_mesh = False
        params.body_skeletal_mesh = True
        params.full_body_skeletal_mesh = True
        params.overwrite_existing_assets = True
        unreal.MetaHumanCharacterExportBlueprintLibrary.export_geometry(ch, params)
        out = "P:/FoA-Assets/MetaTailor/NaturalTeen"
        os.makedirs(out, exist_ok=True)
        for name in ("MHC_Face_N_Body", "MHC_Face_N_FullBody"):
            mesh = unreal.load_asset(params.project_path + "/" + name)
            assert isinstance(mesh, unreal.SkeletalMesh), name
            assert EAL.save_loaded_asset(mesh, False)
            task = unreal.AssetExportTask()
            task.object = mesh
            task.filename = out + "/" + name + ".fbx"
            task.automated, task.prompt, task.replace_identical = True, False, True
            options = unreal.FbxExportOption()
            options.level_of_detail = False
            options.export_morph_targets = False
            task.options = options
            assert unreal.Exporter.run_asset_export_task(task), task.filename
            assert os.path.getsize(task.filename) > 10000, task.filename
        assert EAL.save_loaded_asset(ch, False)
        print("TEEN natural body/full-body geometry and FBX saved for profile review", out)
    elif STEP == "head":
        params = unreal.MetaHumanGeometryExportParams()
        params.project_path = BUILD
        params.head_skeletal_mesh = True
        params.body_skeletal_mesh = False
        params.full_body_skeletal_mesh = False
        params.overwrite_existing_assets = True
        unreal.MetaHumanCharacterExportBlueprintLibrary.export_geometry(ch, params)
        head = unreal.load_asset(params.project_path + "/MHC_Face_N_Head")
        assert head and head.get_editor_property("asset_user_data"), "Head export must preserve new facial DNA"
        assert EAL.save_loaded_asset(head, False)
        print("TEEN rigged head saved; topology materials require finalization")
    elif STEP == "finish":
        assert EAL.save_directory(BUILD, False, True)
        assert EAL.save_loaded_asset(ch, False)
        SUB.remove_object_to_edit(ch)
        print("TEEN source saved and Creator session released")
    else:
        assert STEP == "status", STEP
        print("TEEN can_build", SUB.can_build_meta_human(ch, True))
        assert EAL.save_loaded_asset(ch, False)
