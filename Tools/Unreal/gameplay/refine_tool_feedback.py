"""Narrow native BP_Door feedback edit; no animation or player changes."""
import json,sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
path='/Game/FoA/Gameplay/BP_Door';owner='door-mechanics';token=None
def call(name,**args):
    r=h.call(name,args,owner=owner,lease=token);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True),d;return d
assert not call('editor_get_state')['pie_running']
token=h.lease_acquire(owner,['asset:'+path],ttl_s=60,wait_s=5)
try:
    g=json.loads(Path('P:/FoA/Saved/Integration/tool_refresh_untruncated.json').read_text())
    nodes=g['nodes'];edges=g['edges']
    fmt=next(n['node_id'] for n in nodes if n['title']=='Format Text')
    angle=next(n['node_id'] for n in nodes if n['title']=='Get ToolAngle')
    screwline=next(e['to_node'] for e in edges if e['from_node']==fmt and e['to_pin']=='LineText')
    keyline=next(n['node_id'] for n in nodes if 'ShowToolStatus' in n['title'].replace(' ','') and n['node_id']!=screwline)
    assert not any(n['title']=='Get ToolInputAngle' for n in nodes),'Feedback already applied; inspect rather than duplicate'
    ops=[]
    def add(ref,kind,x,y,**kw):ops.append(dict(op='add_node',ref=ref,node_type=kind,x=x,y=y,**kw))
    def calc(ref,name,x,y):add(ref,'call_function',x,y,function_name='/Script/Engine.KismetMathLibrary:'+name)
    def link(a,ap,b,bp):ops.append(dict(op='connect',from_node=a,from_pin=ap,to_node=b,to_pin=bp))
    def pin(n,p,v):ops.append(dict(op='set_pin',node_id=n,pin_name=p,value=str(v)))
    assert next(n for n in nodes if n['node_id']==fmt)['pins']['Format']=='Screw {N} of 4 ({Progress}%)\nD Turn   A Reverse   Q Cancel\nGamepad: right stick turns, B cancels.'
    calc('percent','Multiply_DoubleDouble',3900,2200);pin('percent','B',100/720);link(angle,'ToolAngle','percent','A')
    calc('rounded','Round',4200,2200);link('percent','ReturnValue','rounded','A');link('rounded','ReturnValue',fmt,'Progress')
    add('inputangle','variable_get',3600,2500,variable_name='ToolInputAngle')
    calc('caught','GreaterEqual_DoubleDouble',3900,2500);pin('caught','B',45);link('inputangle','ToolInputAngle','caught','A')
    calc('copy','SelectString',4200,2500)
    pin('copy','A','Key caught. Keep pressure on it.\nD Force   A Ease back   Q Cancel\nGamepad: right stick turns, B cancels.')
    pin('copy','B','Turn the key.\nD Turn   A Reverse   Q Cancel\nGamepad: right stick turns, B cancels.')
    link('caught','ReturnValue','copy','bPickA')
    add('textcopy','call_function',4500,2500,function_name='/Script/Engine.KismetTextLibrary:Conv_StringToText')
    link('copy','ReturnValue','textcopy','InString');link('textcopy','ReturnValue',keyline,'LineText')
    ops.append(dict(op='comment',title='Resistance and screw progress',node_ids=['percent','rounded','inputangle','caught','copy','textcopy'],color=[.2,.35,.4]))
    batch=call('blueprint_graph_batch',path=path,graph_name='RefreshDoorTool',ops=ops,compile=True,save=True)
    compiled=call('blueprint_compile',path=path,save=True)
    assert compiled['error_count']==0 and compiled['warning_count']==0 and compiled['saved'],compiled
    Path('P:/FoA/Saved/Integration/door_feedback_fix.json').write_text(json.dumps(dict(before=g,batch=batch,compile=compiled),indent=1))
    print('Saved tool resistance and per-screw feedback; runtime readability still requires proof')
finally:h.release(owner,token)
