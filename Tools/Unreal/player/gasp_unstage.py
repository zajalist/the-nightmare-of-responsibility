"""Anim lane: after gasp_retarget.py, drop the GASP staging (Content/Characters/UEFN_Mannequin, Content/Misc copies).
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/gasp_unstage.py FOA_STEP=check|detach|delete
check   lists every staged package that something outside the staging still references.
detach  points AS_GASP_* clips that use GASP's curve compression settings back at the engine default, then saves.
Delete the staged files only after `check` reports nothing (in a separate run, editors closed)."""
import json
import os
import sys
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
EAL = unreal.EditorAssetLibrary
staged = json.load(open('P:/FoA/Saved/AnimShots/gasp_staged.json'))
pkgs = {s['package'] for s in staged}
step = os.environ.get('FOA_STEP', 'check')
if step == 'detach':
    for path in EAL.list_assets('/Game/FoA/Characters/Player/Anims/GASP', recursive=False):
        seq = unreal.load_asset(path.split('.')[0])
        if isinstance(seq, unreal.AnimSequence):
            cc = seq.get_editor_property('curve_compression_settings')
            if cc and cc.get_path_name().split('.')[0] in pkgs:
                if unreal.AnimationLibrary.does_curve_exist(seq,'Distance',unreal.RawCurveTrackTypes.RCT_FLOAT):
                    import dm_compression
                    dm_compression.assign(seq)
                else:
                    seq.set_editor_property('curve_compression_settings', None)
                EAL.save_loaded_asset(seq, False)
                print('detached', seq.get_name())
if step == 'delete':  # FOA_EXCLUSIVE=1, in a PIE window: the GASP-only retarget rigs, then the staging
    for p in ['/Game/FoA/Characters/Player/Retarget/IK_FoA_GASP', '/Game/FoA/Characters/Player/Retarget/RTG_GASP_to_Mannequin'] + sorted(pkgs):
        if EAL.does_asset_exist(p):  # never opened in an editor; referencers checked by `check`
            print('delete', p, EAL.delete_asset(p))
outside = {}
for p in (sorted(pkgs) if step != 'delete' else []):
    refs = [r for r in EAL.find_package_referencers_for_asset(p, False) if str(r).split('.')[0] not in pkgs]
    if refs:
        outside[p] = [str(r) for r in refs]
print('OUTSIDE_REFS', json.dumps(outside)[:1500])
