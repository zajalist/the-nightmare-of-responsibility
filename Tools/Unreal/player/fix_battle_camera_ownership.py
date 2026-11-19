"""Cache public SetBattle ownership before the anim cast; exclude it from free-FP body yaw."""
import datetime,hashlib,json,os,shutil,sys
from pathlib import Path
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch,inspect
P='/Game/FoA/Characters/Player/BP_FoAPlayer';owner=os.environ.get('FOA_AGENT','character_camera');os.environ['HAYBA_AGENT_ID']=owner
assert not h.call('editor_get_state')['data']['pie_running']
token=h.lease_acquire(owner,['asset:'+P],ttl_s=50,wait_s=3)
norm=lambda t:''.join(t.lower().split())
try:
    backup=Path('P:/FoA/Saved/Backups/battle_camera_ownership')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
    shutil.copy2('P:/FoA/Content/FoA/Characters/Player/BP_FoAPlayer.uasset',backup/'BP_FoAPlayer.uasset')
    protected=['Content/FoA/Cinematics/LS_WakeUp_ManualPose.uasset','Content/FoA/Cinematics/WakeUp/AS_FoA_Wake_Lying.uasset']
    hashes=lambda:{p:hashlib.sha256(Path('P:/FoA',p).read_bytes()).hexdigest() for p in protected}
    before=hashes();report=dict(backup=str(backup),protected=before)
    r=h.call('blueprint_add_variable',dict(path=P,variable_name='bBattleActive',variable_type='bool',default_value='false',instance_editable=False,category='Camera',update_existing=True));assert r.get('ok'),r
    nodes,edges=inspect(P,'SetBattle');entry=next(n['node_id'] for n in nodes if norm(n['title'])=='setbattle')
    if not any(norm(n['title'])=='setbbattleactive' for n in nodes):
        nexts=[e for e in edges if e['from_node']==entry and e['from_pin']=='then'];assert len(nexts)==1
        b=Batch(P,'SetBattle');b.set('owned','bBattleActive',180,-180);b.link(entry,'bEnable','owned','bBattleActive')
        b.fn('refresh',P+'.BP_FoAPlayer_C:UpdateFirstPersonVisibility',440,-180)
        e=nexts[0];b.cut(entry,'then',e['to_node'],e['to_pin']);b.chain(entry,'owned','refresh');b.link('refresh','then',e['to_node'],e['to_pin'])
        b.comment('Battle owns body facing',['owned','refresh']);report['SetBattle']=b.run()
    nodes,edges=inspect(P,'UpdateFirstPersonVisibility')
    if not any(norm(n['title'])=='getbbattleactive' for n in nodes):
        yaw=next(n['node_id'] for n in nodes if norm(n['title'])=='setbusecontrollerrotationyaw')
        free=next(e['from_node'] for e in edges if e['to_node']==yaw and e['to_pin']=='bUseControllerRotationYaw')
        source=next(e for e in edges if e['to_node']==free and e['to_pin']=='A')
        b=Batch(P,'UpdateFirstPersonVisibility');b.get('battleowned','bBattleActive',300,1250)
        b.fn('authored_battle','/Script/Engine.KismetMathLibrary:BooleanOR',600,1150)
        b.cut(source['from_node'],source['from_pin'],free,'A');b.link(source['from_node'],source['from_pin'],'authored_battle','A');b.link('battleowned','bBattleActive','authored_battle','B');b.link('authored_battle','ReturnValue',free,'A')
        b.comment('Keep encounter facing',['battleowned','authored_battle']);report['FP']=b.run()
    c=h.call('blueprint_compile',dict(path=P,save=True))['data'];assert c['error_count']==0 and c['warning_count']==0 and c['saved'],c
    assert hashes()==before
    report.update(compile=c,protected_after=hashes())
    Path('P:/FoA/Saved/Integration/cinematic_audit/battle_camera_ownership.json').write_text(json.dumps(report,indent=2))
    print('BATTLE_FACING ownership saved',c)
finally:h.release(owner,token)
