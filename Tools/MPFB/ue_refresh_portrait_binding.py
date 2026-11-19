"""Rebuild the existing binding in place after the face-only head reimport."""
import json
from pathlib import Path
import unreal

def run():
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    root='/Game/FoA/Characters/Teen'
    head=unreal.load_asset(root+'/Mesh/SK_Teen_Head')
    binding=unreal.load_asset(root+'/Hair/GB_Teen_Scalp_Head')
    assert binding.get_editor_property('target_skeletal_mesh')==head
    binding.build(unreal.OnGroomBindingAssetBuildComplete())
    groups=binding.get_editor_property('group_infos')
    roots=sum(g.get_editor_property('ren_root_count') for g in groups)
    assert roots==31994,roots
    unreal.EditorAssetLibrary.save_loaded_asset(binding,only_if_is_dirty=False)
    report={'binding':binding.get_path_name(),'head':head.get_path_name(),'roots':roots,
            'morphs':len(head.morph_targets),'material_paths':[s.material_interface.get_path_name() for s in head.materials],
            'bounds_positive':str(head.positive_bounds_extension),'bounds_negative':str(head.negative_bounds_extension)}
    Path('P:/FoA/Saved/CharacterShots/mpfb/portrait_face/ue_binding.json').write_text(json.dumps(report,indent=2))
    print('PORTRAIT_BINDING',json.dumps(report))

run()
