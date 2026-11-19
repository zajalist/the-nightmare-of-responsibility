"""MI_Jumpscare_Monster look: black wet sand over the Lux3D sculpt. Dark base, wet but broken specular, crumbling grain
from the fireplace's tileable grunge normal (reused, tiled), ridge-only specular from T_Jumpscare_Monster_S.
Material-instance parameters only.
  $env:FOA_AREAS='Gameplay'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/look_monster_mi.py [FOA_TILE=4] [FOA_NSCALE=1.5]"""
import os

import unreal

MEL = unreal.MaterialEditingLibrary


def main():
    mi = unreal.load_asset('/Game/FoA/Gameplay/Jumpscare/MI_Jumpscare_Monster')
    tile = float(os.environ.get('FOA_TILE', '4'))
    MEL.set_material_instance_static_switch_parameter_value(mi, 'bHasNormalTexture', True)
    MEL.set_material_instance_texture_parameter_value(mi, 'NormalTexture', unreal.load_asset('/Game/FoA/Fireplace/Textures/T_FP_GrungeNormal'))
    MEL.set_material_instance_vector_parameter_value(mi, 'NormalTexture_OffsetScale', unreal.LinearColor(0, 0, tile, tile))
    MEL.set_material_instance_scalar_parameter_value(mi, 'NormalScale', float(os.environ.get('FOA_NSCALE', '1.5')))
    MEL.set_material_instance_scalar_parameter_value(mi, 'RoughnessFactor', float(os.environ.get('FOA_ROUGH', '0.5')))
    spec = unreal.load_asset('/Game/FoA/Gameplay/Jumpscare/T_Jumpscare_Monster_S')
    if spec:  # ridge-only specular, none in the eye and mouth voids (make_monster_maps.py)
        spec.set_editor_property('srgb', False)
        spec.set_editor_property('max_texture_size', 1024)
        unreal.EditorAssetLibrary.save_asset(spec.get_path_name().split('.')[0], only_if_is_dirty=False)
        MEL.set_material_instance_static_switch_parameter_value(mi, 'bHasSpecularTexture', True)
        MEL.set_material_instance_texture_parameter_value(mi, 'SpecularTexture', spec)
        MEL.set_material_instance_scalar_parameter_value(mi, 'SpecularFactor', 1.0)
    MEL.set_material_instance_vector_parameter_value(mi, 'BaseColorFactor', unreal.LinearColor(0.018, 0.018, 0.018, 1))
    MEL.update_material_instance(mi)
    unreal.EditorAssetLibrary.save_asset(mi.get_path_name(), only_if_is_dirty=False)
    print('MI look set', tile)


main()
