"""Read-only FBX export of actual imported bind data for comparison; no world actors or asset writes."""
import unreal
for name,path in (("original","/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Body/SKM_MHC_Protagonist_BodyMesh"),
                  ("suited","/Game/FoA/Characters/Player/Clothing/SK_FoA_Body_Suited"),
                  ("suit","/Game/FoA/Characters/Player/Clothing/SK_FoA_Suit")):
    task=unreal.AssetExportTask()
    task.object=unreal.load_asset(path)
    task.filename="P:/FoA/Saved/CharacterShots/rig_"+name+".fbx"
    task.automated=True;task.prompt=False;task.replace_identical=True
    options=unreal.FbxExportOption();options.level_of_detail=False;options.export_morph_targets=False
    task.options=options
    assert unreal.Exporter.run_asset_export_task(task),name
print("Actual original/suited/suit FBX bind data exported for offline comparison")
