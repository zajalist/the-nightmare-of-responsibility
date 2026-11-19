"""Coordinator-only final compile receipts and read-only world/save audit.

No PIE, map switching, map saves, layout changes or cleanup. Imports are offline
safe. `run` needs an explicit editor writer window; `inventory` only observes.
Each Blueprint compile/save uses its own short exact-asset lease.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path('P:/FoA')
OUT=ROOT/'Saved/Integration/level_continuity_validation'
BEDROOM='/Game/FoA/Maps/L_Tutorial_Bedroom'
# Prior level_integration_final_compile.json ownership, plus the new stop/phone
# assets and the L1 worker's explicitly owned player-camera patch.
BLUEPRINTS=(
    '/Game/FoA/Level2/Transition/BP_DreamThreshold',
    '/Game/FoA/Level2/Transition/WBP_DreamThreshold',
    '/Game/FoA/Level2/Journey/BP_L2Journey',
    '/Game/FoA/Level2/Journey/WBP_L2Journey',
    '/Game/FoA/Level2/Journey/WBP_L2Interview',
    '/Game/FoA/Level2/Journey/BP_L2Merge',
    '/Game/FoA/Level2/Journey/BP_L2StopSet',
    '/Game/FoA/Level2/Drive/BP_L2Car',
    '/Game/FoA/Level2/Drive/BP_L2RoadNetwork',
    '/Game/FoA/Level2/Drive/BP_Meteor',
    '/Game/FoA/Level2/Drive/WBP_L2Drive',
    '/Game/FoA/Gameplay/BP_BeatDirector',
    '/Game/FoA/UI/Framework/BP_FoAFrontEnd',
    '/Game/FoA/Audio/BP_RoomAudio',
    '/Game/FoA/Gameplay/BPC_Interactor',
    '/Game/FoA/Gameplay/Encounter/BP_Encounter',
    '/Game/FoA/Gameplay/Encounter/BP_Garment',
    '/Game/FoA/Gameplay/Encounter/WBP_Encounter',
    '/Game/FoA/Characters/Player/BP_FoAPlayer',
    '/Game/FoA/UI/Game/BP_Phone',
    '/Game/FoA/UI/Game/WBP_Phone',
    '/Game/FoA/UI/Game/WBP_HUD',
)
SEQUENCES=tuple('/Game/FoA/Level2/Transition/'+name for name in (
    'LS_DreamThreshold','LS_DreamThreshold_ReducedMotion','LS_DreamFall','LS_DreamFall_ReducedMotion'))+(
    '/Game/FoA/Cinematics/BattleIntro/LS_BattleIntro',
    '/Game/FoA/Cinematics/BattleIntro/LS_BattleIntro_Short',
)
EXISTS_ONLY=('/Game/FoA/UI/Game/WBP_Debug',)
PROTECTED=('Saved/SaveGames/FoA.sav','Saved/SaveGames/Settings.sav',
           'Saved/Config/WindowsEditor/GameUserSettings.ini',
           'Content/FoA/Maps/L_Tutorial_Bedroom.umap')


def hashes(root=ROOT):
    return {name:hashlib.sha256((root/name).read_bytes()).hexdigest() if (root/name).exists() else None
            for name in PROTECTED}


def validate_inventory(row):
    assert not row['pie_running'],'PIE is running'
    assert row['world'].split('.')[0]==BEDROOM,row['world']
    assert row['actor_count']==236,('Bedroom actor count changed',row['actor_count'])
    assert not row['temporary_actors'],row['temporary_actors']
    core=row['essential_actors']
    assert core['BP_BeatDirector_C'] and 'Encounter_T8' in core['BP_Encounter_C'] and core['PlayerStart'],core
    assert all(item['exists'] and item['on_disk'] for item in row['assets']),row['assets']
    dirty=set(row['dirty_assets'])|set(row['dirty_maps'])
    assert not dirty.intersection(SEQUENCES),('Sequences not saved',sorted(dirty.intersection(SEQUENCES)))


def run(mode='run'):
    assert mode in ('run','inventory'),mode
    sys.path.insert(0,str(ROOT/'Tools/Unreal'))
    import editor_lock
    from finalize_l2_graphs import call, checked_compile
    owner='main-level2-validation'
    os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner,FOA_CALLER=owner)
    OUT.mkdir(parents=True,exist_ok=True)
    stamp=time.time();before=hashes();receipt=dict(started=stamp,mode=mode,passed=False,hashes_before=before,compiles={})
    def inventory(label):
        editor_lock.acquire(owner,wait_s=5,ttl=45)
        try:
            assert not call('editor_get_state')['pie_running']
            call('python_exec_file',path=str(ROOT/'Tools/Unreal/level2/level_validation_inventory.py'),
                 env={'FOA_VALIDATION_LABEL':label},resources=['global'])
            path=OUT/(label+'.json');assert path.stat().st_mtime>=stamp,'Stale inventory receipt'
            row=json.loads(path.read_text());validate_inventory(row)
            return row
        finally:editor_lock.release(owner)
    try:
        receipt['before']=inventory('before')
        if mode=='run':
            for path in BLUEPRINTS:
                editor_lock.acquire(owner,wait_s=5,ttl=60,areas=[path])
                try:
                    assert not call('editor_get_state')['pie_running']
                    result=checked_compile(path)
                    receipt['compiles'][path]=dict(errors=result['error_count'],warnings=result['warning_count'],saved=True)
                finally:editor_lock.release(owner)
                (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2))
                print('COMPILE 0/0 SAVED',path,flush=True)
        receipt['after']=inventory('after')
        if mode=='run':
            remaining=set(receipt['after']['dirty_assets']).intersection(BLUEPRINTS)
            assert not remaining,('Owned Blueprint packages remain dirty',sorted(remaining))
        receipt['passed']=True
    finally:
        receipt['hashes_after']=hashes()
        receipt['protected_unchanged']=receipt['hashes_after']==before
        receipt['passed']=receipt['passed'] and receipt['protected_unchanged']
        receipt['elapsed']=round(time.time()-stamp,3)
        (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2))
        assert receipt['protected_unchanged'],'Player/settings/bedroom disk bytes changed during validation'
    print(json.dumps(dict(passed=True,compiles=len(receipt['compiles']),
                         protected_unchanged=True,dirty_maps=receipt['after']['dirty_maps'],
                         dirty_assets=receipt['after']['dirty_assets'])),flush=True)


if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else 'run')
