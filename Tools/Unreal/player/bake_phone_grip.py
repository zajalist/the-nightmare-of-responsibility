"""Validate and bake the two-frame left-phone pose, preserving its existing animation asset.
Author against the native UE skin fixture with Tools/Rig/phone_native.py, then export_phone_native.py.
Copy phone_native_solution.json to phone_grip_solution.json only after its gates pass.
Offline invocation validates that solution; editor invocation writes it under an owned Characters lease.
Follow with phone_hold_attach_graphs.py --defaults-only and a guarded PIE proof.
"""
import importlib
import json
import os
import sys
from pathlib import Path
try:
    import unreal
except ImportError:
    unreal = None

sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import hand_pose_checks
importlib.reload(hand_pose_checks)
OUT = '/Game/FoA/Characters/Player/Anims/Hands/AS_FoA_Grip_Phone_L'
REF_JSON = Path('P:/FoA/Saved/AnimShots/teen_ref_pose.json')
THUMB_ONLY=os.environ.get('FOA_PHONE_THUMB_ONLY')=='1'
SOLUTION = Path(os.environ.get('FOA_PHONE_SOLUTION','P:/FoA/Saved/AnimShots/phone_grip_solution.json'))


def write(res):
    body = unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body')
    skel = body.get_editor_property('skeleton')
    seq = unreal.load_asset(OUT)
    if THUMB_ONLY:
        assert seq,'Thumb correction requires the existing left-phone animation'
        return write_thumb(seq,res)
    if not seq:
        f = unreal.AnimSequenceFactory()
        f.set_editor_property('target_skeleton', skel)
        f.set_editor_property('preview_skeletal_mesh', body)
        seq = unreal.AssetToolsHelpers.get_asset_tools().create_asset(OUT.rsplit('/', 1)[1], OUT.rsplit('/', 1)[0], unreal.AnimSequence, f)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    ctrl = seq.get_editor_property('controller')
    ctrl.open_bracket('Phone hold v2', False)
    ctrl.set_frame_rate(unreal.FrameRate(30, 1), False)
    ctrl.set_number_of_frames(unreal.FrameNumber(1), False)
    for b in res['names']:
        try:
            ctrl.add_bone_curve(b, False)
        except Exception:  # already tracked
            pass
        keys = [p.local[b] for p in (res['hold'], res['tap'])]
        ctrl.set_bone_track_keys(b, [unreal.Vector(*k[0]) for k in keys], [unreal.Quat(*k[1]) for k in keys],
                                 [unreal.Vector(*k[2]) for k in keys], False)
    ctrl.close_bracket(False)
    seq.set_editor_property('enable_root_motion', False)
    assert unreal.EditorAssetLibrary.save_loaded_asset(seq, False)


def write_thumb(seq,res):
    """Keep every existing non-thumb track, duration, notify and curve intact."""
    import datetime,shutil
    names=('thumb_01_l','thumb_02_l','thumb_03_l')
    A=unreal.AnimPoseExtensions;L=unreal.AnimPoseSpaces.LOCAL
    options=unreal.AnimPoseEvaluationOptions();options.evaluation_type=unreal.AnimDataEvalType.RAW
    length=seq.get_play_length();frames=unreal.AnimationLibrary.get_num_frames(seq)
    assert frames==1 and abs(length-1/30)<1e-5,('Unexpected phone grip timing',frames,length)
    def preserved():
        rows=[]
        for t in (0.,length/2,length):
            pose=A.get_anim_pose_at_time(seq,t,options)
            rows.append({str(n):A.get_bone_pose(pose,n,L).export_text() for n in A.get_bone_names(pose) if str(n) not in names})
        return rows
    before=preserved()
    originals={name:[] for name in names}
    for t in (0.,length):
        pose=A.get_anim_pose_at_time(seq,t,options)
        for name in names:
            key=A.get_bone_pose(pose,name,L)
            originals[name].append((tuple(key.translation.to_tuple()),tuple(key.rotation.to_tuple()),tuple(key.scale3d.to_tuple())))
    folder=Path('P:/FoA/Saved/Backups/phone_bezel')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    folder.mkdir(parents=True)
    assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False)
    shutil.copy2('P:/FoA/Content/FoA/Characters/Player/Anims/Hands/AS_FoA_Grip_Phone_L.uasset',folder/'AS_FoA_Grip_Phone_L.uasset')
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
    ctrl=seq.get_editor_property('controller')
    def put(keys_by_name,title):
        ctrl.open_bracket(title,False)
        try:
            for name,keys in keys_by_name.items():
                ctrl.set_bone_track_keys(name,[unreal.Vector(*k[0]) for k in keys],[unreal.Quat(*k[1]) for k in keys],
                                        [unreal.Vector(*k[2]) for k in keys],False)
        finally:ctrl.close_bracket(False)
    try:
        put({name:[p.local[name] for p in (res['hold'],res['tap'])] for name in names},'Rest thumb on bezel')
        assert preserved()==before,'Non-thumb animation changed'
        assert seq.get_play_length()==length and unreal.AnimationLibrary.get_num_frames(seq)==frames
        assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False)
    except Exception:
        put(originals,'Restore phone thumb')
        assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False),'Thumb rollback save failed'
        raise
    Path('P:/FoA/Saved/AnimShots/phone_bezel_preservation.json').write_text(json.dumps(dict(asset=OUT,
        changed=list(names),samples=[0,length/2,length],all_non_thumb_tracks_exact=True,
        duration=length,backup=str(folder)),indent=2))


sol = json.loads(SOLUTION.read_text())
assert SOLUTION.stat().st_mtime >= REF_JSON.stat().st_mtime, 'the solution is older than the exported reference pose'
checks = hand_pose_checks.phone(sol, json.loads(REF_JSON.read_text()))
if unreal:
    pose_of = lambda d: type('P', (), {'local': {b: (tuple(v[0]), tuple(v[1]), tuple(v[2])) for b,v in d.items()}})
    write(dict(names=sol['names'],hold=pose_of(sol['hold']),tap=pose_of(sol['tap'])))
    Path('P:/FoA/Saved/AnimShots/'+('phone_bezel_bake.json' if THUMB_ONLY else 'phone_grip_bake.json')).write_text(json.dumps(sol['out'], indent=1))
print('PHONE_GRIP', 'baked' if unreal else 'validated', {k:v['palm_facing_deg'] for k,v in checks.items()})
