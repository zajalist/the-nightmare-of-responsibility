"""Battle garments, step c (editor Python: Hayba's mesh_set_material_slot is StaticMesh only): each SK_Garment_<Name>
renders its own MI_Garment_<Name> in every slot. Saves the four meshes.
  python Tools/Unreal/ue_remote.py Tools/Unreal/face/garments_assign.py FOA_AREAS=Characters"""
import unreal

ROOT = '/Game/FoA/Characters/Garments'


def run():
    for name in ('Shirt', 'Trousers', 'Sock', 'Tie'):
        mesh = unreal.load_asset(f'{ROOT}/SK_Garment_{name}')
        mi = unreal.load_asset(f'{ROOT}/MI_Garment_{name}')
        assert mesh and mi, name
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(mesh)
        mats = list(mesh.get_editor_property('materials'))
        for m in mats:
            m.set_editor_property('material_interface', mi)
        mesh.set_editor_property('materials', mats)
        got = [m.get_editor_property('material_interface').get_name() for m in mesh.get_editor_property('materials')]
        assert all(g == mi.get_name() for g in got), (name, got)
        assert unreal.EditorAssetLibrary.save_loaded_asset(mesh, False), name
        print('FOA_GARMENT_MI', name, got)


run()
