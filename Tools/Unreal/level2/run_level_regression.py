"""Run the existing QA plans in the coordinator's explicitly owned integration window."""
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path[:0]=['P:/FoA/Tools/QA','P:/FoA/Tools/Unreal']
import playtest_all as qa


def player_save_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def check_result(result):
    proof=result.get('result')
    assert isinstance(proof,dict),result
    assert proof.get('why')=='done' and proof.get('steps',0)>0 and proof.get('passed')==proof['steps'],result


owner='main-level-regression'
hold=Path('P:/FoA/Saved/FoA_editor.lock')
assert json.loads(hold.read_text())['owner'] in ('main:MAINTENANCE level integration','main:MAINTENANCE playtest feedback')
qa.OWNER=owner
os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner,FOA_CALLER=owner)
qa.maintenance=lambda:False  # This coordinator owns the verified maintenance window above.
out=Path('P:/FoA/Saved/Codex/level_regression');out.mkdir(parents=True,exist_ok=True)
save=Path('P:/FoA/Saved/SaveGames/FoA.sav')
prefs=save.with_name('Settings.sav')
before=player_save_hash(save)
settings=prefs.read_bytes() if prefs.exists() else None
results=[]
try:
    qa.forbid_delegates()
    for plan in sys.argv[1:]:
        assert json.loads(hold.read_text())['owner'] in ('main:MAINTENANCE level integration','main:MAINTENANCE playtest feedback')
        assert plan in qa.ALL,plan
        result=qa.burst(plan,str(out/plan),48)
        results.append(result)
        (out/'bursts.json').write_text(json.dumps(results,indent=1))
        print(json.dumps(result),flush=True)
        assert player_save_hash(save)==before,'Player save changed'
        check_result(result)
finally:
    if settings is not None:prefs.write_bytes(settings)
    elif prefs.exists():prefs.unlink()
    assert player_save_hash(save)==before,'Player save changed'
    print('Player save unchanged; settings restored',flush=True)
