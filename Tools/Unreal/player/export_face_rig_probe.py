"""Read-only export of shipped and native-exported Face bind/weights for offline comparison."""
import unreal
for label,path in (('face_original','/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Face/SKM_MHC_Protagonist_FaceMesh'),('face_teen','/Game/FoA/Characters/Protagonist/Teen/Built/MHC_Teen_Head')):
 task=unreal.AssetExportTask();task.object=unreal.load_asset(path)
 task.filename='P:/FoA/Saved/CharacterShots/rig_'+label+'.fbx';task.automated=True;task.prompt=False;task.replace_identical=True
 options=unreal.FbxExportOption();options.level_of_detail=False;options.export_morph_targets=False;task.options=options
 assert unreal.Exporter.run_asset_export_task(task),label
 print('EXPORTED face bind+weights',label)
