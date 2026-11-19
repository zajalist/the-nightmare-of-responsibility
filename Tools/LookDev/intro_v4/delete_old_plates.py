"""Delete the intro's superseded v2 textures (intro lane), only those the asset registry shows nothing referencing.
Run alone, in an EXCLUSIVE hold (asset deletes); nothing loads them first (no editor has them open); never forced:
  python Tools/Unreal/editor_lock.py acquire intro --ttl 60
  python Tools/Unreal/ue_remote.py Tools/LookDev/intro_v4/delete_old_plates.py FOA_EXCLUSIVE=1
T_Intro_Game01_Sleep and its _Near stay: the ui lane's M_UI_Panel and MI_UI_PanelNear still use them."""
import os

import unreal

DIR = '/Game/FoA/UI/Intro/Textures/'
NAMES = ['T_Intro_BedFigure', 'T_Intro_BedFx', 'T_Intro_BedMid'] + [
    f'T_Intro_Game0{i}_{n}{s}' for i, n in ((2, 'BedFoot'), (3, 'Clock'), (4, 'Desk'), (5, 'Chores'), (6, 'Wardrobe'),
                                            (7, 'Door'), (8, 'Window')) for s in ('', '_Near')]
reg = unreal.AssetRegistryHelpers.get_asset_registry()
opts = unreal.AssetRegistryDependencyOptions()
gone, kept = [], []
for n in NAMES:
    path = DIR + n
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        continue
    refs = [str(r) for r in (reg.get_referencers(path, opts) or []) if str(r) != path]
    if refs:
        kept.append((n, refs))
        continue
    ok = unreal.EditorAssetLibrary.delete_asset(path)
    f = f'P:/FoA/Content/FoA/UI/Intro/Textures/{n}.uasset'
    if ok and os.path.exists(f):  # delete_asset can leave the file behind (cleanup_worker.py notes it): finish it
        os.remove(f)
    (gone if ok and not os.path.exists(f) else kept).append(n)
print('deleted', len(gone), gone)
print('kept', kept)
