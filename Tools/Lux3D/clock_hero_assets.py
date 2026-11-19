"""The Lux3D hero alarm clock's assets, to the house naming (SM_/MI_/T_Lux3D_AlarmClock*), with the brand-free dial.
  $env:FOA_AREAS='/Game/FoA/Lux3D/alarm_clock_hero'; python Tools/Unreal/ue_remote.py Tools/Lux3D/clock_hero_assets.py FOA_STEP=point
  ... FOA_STEP=rename   (a separate run: never rename in the run that edits)
point: the Interchange MI's base colour -> T_Lux3D_AlarmClock_BaseColor (the inpainted dial), 2K kept (40 cm insert),
       saves everything in the folder. rename: SM_Lux3D_AlarmClock, MI_Lux3D_AlarmClock, T_Lux3D_AlarmClock_MetallicRoughness,
       and lists the Interchange base colour for the EXCLUSIVE delete run."""
import os

import unreal

EAL = unreal.EditorAssetLibrary

def refs(path):
    """Package referencers from the asset registry (EAL.find_package_referencers_for_asset can come back empty)."""
    return [str(r) for r in (unreal.AssetRegistryHelpers.get_asset_registry().get_referencers(
        str(path).split('.')[0], unreal.AssetRegistryDependencyOptions()) or [])]

MEL = unreal.MaterialEditingLibrary
ROOT = '/Game/FoA/Lux3D/alarm_clock_hero'
BC = ROOT + '/T_Lux3D_AlarmClock_BaseColor'


def assets():
    out = {}
    for p in EAL.list_assets(ROOT, recursive=True, include_folder=False):
        out.setdefault(EAL.load_asset(p).get_class().get_name(), []).append(p.split('.')[0])
    return out


A = assets()
mi_path = [p for p in A['MaterialInstanceConstant']][0]
mi = EAL.load_asset(mi_path)
if os.environ.get('FOA_STEP') == 'point':
    t = EAL.load_asset(BC)
    t.set_editor_property('max_texture_size', 2048)
    MEL.set_material_instance_texture_parameter_value(mi, 'BaseColorTexture', t)
    for p in sum(A.values(), []):
        EAL.save_asset(p, only_if_is_dirty=False)
    print('MI base colour ->', MEL.get_material_instance_texture_parameter_value(mi, 'BaseColorTexture').get_name())
else:
    mr = MEL.get_material_instance_texture_parameter_value(mi, 'MetallicRoughnessTexture')
    old_bc = [p for p in A['Texture2D'] if p != BC and EAL.load_asset(p) != mr]
    print('rename MR', EAL.rename_asset(mr.get_path_name().split('.')[0], ROOT + '/T_Lux3D_AlarmClock_MetallicRoughness'))
    print('rename MI', EAL.rename_asset(mi_path, ROOT + '/MI_Lux3D_AlarmClock'))
    print('rename SM', EAL.rename_asset(A['StaticMesh'][0], ROOT + '/SM_Lux3D_AlarmClock'))
    for p in old_bc:   # deletes need EXCLUSIVE: listed here, deleted in the next PIE-window cleanup run
        print('ORPHAN candidate', p, 'refs', refs(p))
