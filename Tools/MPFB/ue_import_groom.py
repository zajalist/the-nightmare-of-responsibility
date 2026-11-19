"""Import the approved short01 scalp Alembic; binding is a separate short editor step.
Run through ue_remote with FOA_STEP=import|render|binding. Never replaces existing hair assets.
"""
import os
import json
from pathlib import Path
import unreal


def run():
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Wait for PIE to stop'
    folder = '/Game/FoA/Characters/Teen/Hair'
    path = folder + '/GR_Teen_Scalp'
    if os.environ.get('FOA_STEP', 'import') == 'import':
        assert not unreal.EditorAssetLibrary.does_asset_exist(path), 'Groom already exists; review before replacing'
        unreal.load_module('AlembicHairTranslatorModule')
        options = unreal.GroomImportOptions()
        conversion = unreal.GroomConversionSettings()
        conversion.rotation = unreal.Vector(90,0,0)
        conversion.scale = unreal.Vector(100,-100,100)
        options.conversion_settings = conversion
        task = unreal.AssetImportTask()
        task.filename = 'P:/FoA-Assets/character/mpfb/export/hair/SM_Teen_Groom_Scalp.abc'
        task.destination_path = folder
        task.destination_name = 'GR_Teen_Scalp'
        task.automated = True
        task.save = True
        task.replace_existing = False
        task.factory = unreal.HairStrandsFactory()
        task.options = options
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        assert isinstance(unreal.load_asset(path), unreal.GroomAsset), task.imported_object_paths
        print('TEEN_GROOM_IMPORTED', task.imported_object_paths)
    elif os.environ['FOA_STEP'] == 'render':
        groom=unreal.load_asset(path)
        assert groom
        width=float(os.environ.get('FOA_HAIR_WIDTH','.036'))
        tip=float(os.environ.get('FOA_HAIR_TIP','.15'))
        stable=os.environ.get('FOA_HAIR_STABLE','1')=='1'
        groups=list(groom.get_editor_property('hair_groups_rendering'))
        for group in groups:
            geometry=group.get_editor_property('geometry_settings')
            geometry.set_editor_property('hair_width',width)
            geometry.set_editor_property('hair_width_override',True)
            geometry.set_editor_property('hair_tip_scale',tip)
            group.set_editor_property('geometry_settings',geometry)
            advanced=group.get_editor_property('advanced_settings')
            advanced.set_editor_property('use_stable_rasterization',stable)
            group.set_editor_property('advanced_settings',advanced)
        groom.set_editor_property('hair_groups_rendering',groups)
        material=unreal.HairGroupsMaterial()
        material.set_editor_property('material',unreal.load_asset(folder+'/MI_Teen_Strands'))
        material.set_editor_property('slot_name','None')
        groom.set_editor_property('hair_groups_materials',[material])
        info=groom.get_editor_property('hair_groups_info')
        report=[{key:g.get_editor_property(key) for key in ('num_curves','num_curve_vertices','num_guides','max_curve_length')} for g in info]
        assert sum(g['num_curves'] for g in report)==31994,report
        assert all(0<g['max_curve_length']<30 for g in report),report
        for row,group in zip(report,groom.get_editor_property('hair_groups_rendering')):
            geometry=group.get_editor_property('geometry_settings')
            row['width_cm']=geometry.get_editor_property('hair_width')
            row['tip_scale']=geometry.get_editor_property('hair_tip_scale')
            row['stable_rasterization']=group.get_editor_property('advanced_settings').get_editor_property('use_stable_rasterization')
            assert abs(row['width_cm']-width)<1e-6 and abs(row['tip_scale']-tip)<1e-6 and row['stable_rasterization']==stable,row
        unreal.EditorAssetLibrary.save_loaded_asset(groom,only_if_is_dirty=False)
        Path('P:/FoA/Saved/CharacterShots/mpfb/hair/ue_groom_validation.json').write_text(json.dumps(report,indent=2))
        print('TEEN_GROOM_RENDER',report)
        print('TEEN_GROOM_SETTINGS',[(g.get_editor_property('geometry_settings').get_editor_property('hair_width'),
                                     g.get_editor_property('geometry_settings').get_editor_property('hair_tip_scale'),
                                     g.get_editor_property('advanced_settings').get_editor_property('use_stable_rasterization'))
                                    for g in groom.get_editor_property('hair_groups_rendering')])
    else:
        binding_path = folder + '/GB_Teen_Scalp_Head'
        assert not unreal.EditorAssetLibrary.does_asset_exist(binding_path), 'Binding already exists'
        groom = unreal.load_asset(path)
        head = unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Head')
        assert groom and head
        binding = unreal.GroomLibrary.create_new_groom_binding_asset_with_path(binding_path, groom, head, 100)
        assert binding, 'Groom binding failed'
        unreal.EditorAssetLibrary.save_loaded_asset(binding, only_if_is_dirty=False)
        info=binding.get_editor_property('group_infos')
        roots=sum(g.get_editor_property('ren_root_count') for g in info)
        assert roots==31994, roots
        assert binding.get_editor_property('target_skeletal_mesh')==head
        report={'binding':binding.get_path_name(),'target':head.get_path_name(),'roots':roots}
        Path('P:/FoA/Saved/CharacterShots/mpfb/hair/ue_binding_validation.json').write_text(json.dumps(report,indent=2))
        print('TEEN_GROOM_BOUND', report)


run()
