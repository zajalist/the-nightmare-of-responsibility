"""Ordered, one-step native conversation/UI apply. No editor calls on import.

Voice skeleton must precede interview graphs; voice implementation may follow.
Drive style runs after the free-drive writer. Each step saves a compile receipt.
"""
import json
import os
from pathlib import Path
import shutil
import sys
import build_interview as interview
import build_journey as journey
import build_stop_set as stop
import build_phone_progress as phone
import l2_ink_style as ink
from finalize_l2_graphs import call,checked_compile
import editor_lock

JOURNEY_GRAPHS=('ReleaseCVPaper','OpenCVPaper','ShowCVPaper','CheckCVPaper',
                'ResumeRun','ActivateCar','RestartRun','DebugNextStep',
                'Confirm','UseStop','StageStop','StopActionFinished','StartFinale',
                'Submit','Abort','RetryDraft','RetryWithoutTiming')
ORDER=('paper.assets','stop.skeleton','journey.skeleton','interview.skeleton',
       'stop.interview_components','stop.interview_idle','stop.interview_suit','stop.stock_labels','stop.Configure','stop.PrepareInterview','stop.Restore','interview.widget','ink.import',
       'interview.widget_refresh','interview.widget_click','interview.widget_hover',
       *('interview.'+name for name in interview.GRAPHS),
       *('journey.'+name for name in JOURNEY_GRAPHS),'interview.bindings',
       'phone.allowed_phone','phone.shared_progress','phone.hooks',
       'journey.widget','ink.interview','ink.journey','ink.drive','ink.phone','ink.phone_context',
       'phone.cache_phone','phone.restore_phone','phone.refresh_phone')


def run(step):
    assert step in ORDER,step
    owner='main-city-ui';os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner,FOA_CALLER=owner)
    group,name=step.split('.',1)
    assets={'paper':['/Game/FoA/Level2/Journey/Paper','/Game/FoA/Gameplay/DT_Items'],
            'stop':[stop.BP],'journey':[journey.BP,journey.HUD],
            'interview':[interview.BP,interview.UI],
            'phone':[phone.JOURNEY,phone.WIDGET,phone.PHONE,phone.FRONT,phone.BATTLE]}
    paths=assets.get(group,[{'interview':ink.INTERVIEW,'journey':ink.JOURNEY,
                           'drive':ink.DRIVE,'phone':ink.PHONE,'phone_context':ink.PHONE}.get(name,ink.ROOT)])
    lease_paths=paths+([stop.I.IDLE] if step=='stop.interview_idle' else [])
    token=editor_lock.acquire(owner,wait_s=5,ttl=120,areas=lease_paths)
    try:
        if not token:
            held=interview.h.leases_of(owner);assert len(held)==1,held;token=held[0][0]
        assert token,'Native lease required'
        os.environ['FOA_LEASE']=token
        assert not call('editor_get_state')['pie_running']
        for path in paths:
            source=Path('P:/FoA/Content'+path[5:]+'.uasset')
            backup=Path('P:/FoA/Saved/Backups/level-integration-20261112/CityUI')/source.name
            if source.exists() and not backup.exists():
                backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
        if group=='paper':
            call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/cv_paper_setup.py',
                 env={'FOA_LEASE':token},resources=['asset:'+path for path in paths])
        elif group=='ink':
            if name=='import':ink.import_assets()
            elif name=='phone_context':ink.phone_context()
            else:ink.apply(paths[0])
        else:
            {'interview':interview,'journey':journey,'stop':stop,'phone':phone}[group].STEPS[name]()
        rows=[]
        if group!='paper' and (group!='ink' or name!='import'):
            for path in paths:
                if Path('P:/FoA/Content'+path[5:]+'.uasset').exists():rows.append(dict(asset=path,compile=checked_compile(path)))
        receipt=dict(step=step,verified=rows)
        out=Path('P:/FoA/Saved/Integration/city_ui');out.mkdir(parents=True,exist_ok=True)
        (out/(step+'.json')).write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
    except BaseException:
        for path in paths:
            if group!='paper' and Path('P:/FoA/Content'+path[5:]+'.uasset').exists():checked_compile(path)
        raise
    finally:editor_lock.release(owner)


if __name__=='__main__':
    if sys.argv[1]=='order':print('\n'.join(ORDER))
    else:run(sys.argv[1])
