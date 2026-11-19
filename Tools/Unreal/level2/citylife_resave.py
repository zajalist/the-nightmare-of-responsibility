"""City life lane: re-save every package under /Game/FoA/Level2/CityLife so saved references carry the renamed paths
(the 14:05 renames saved each clip before its skeleton was renamed: on disk the clips pointed at Fbx/..._Skeleton,
which crashed the cook). Prints each clip's and mesh's skeleton so the fix is visible."""
import unreal

EAL = unreal.EditorAssetLibrary
ROOT = '/Game/FoA/Level2/CityLife'
for p in EAL.list_assets(ROOT, recursive=True, include_folder=False):
    a = EAL.load_asset(p)
    if not a or a.get_path_name().split('.')[0] != p.split('.')[0]:  # a redirector: load_asset followed it elsewhere
        print('skip redirect', p)
        continue
    if isinstance(a, unreal.AnimSequence):
        print('clip', a.get_name(), '->', a.get_editor_property('skeleton').get_path_name())
    elif isinstance(a, unreal.SkeletalMesh):
        print('mesh', a.get_name(), '->', a.skeleton.get_path_name(), a.get_editor_property('physics_asset').get_path_name()
              if a.get_editor_property('physics_asset') else None)
    EAL.save_asset(p.split('.')[0], only_if_is_dirty=False)
print('resaved', ROOT)
