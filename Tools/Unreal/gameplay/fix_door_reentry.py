"""Native, narrow edit: a door action owns the session through its release phase."""
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
    g=call('blueprint_inspect_graph',path=path,graph_name='ApplyRow')
    active=next(n['node_id'] for n in g['nodes'] if n['title']=='Get bToolActive')
    committing=next(n['node_id'] for n in g['nodes'] if n['title']=='Get bToolCommitting')
    transaction=next(e['to_node'] for e in g['edges'] if e['from_node']==committing and e['to_pin']=='Condition')
    entry=next(e for e in g['edges'] if e['from_node']==transaction and e['from_pin']=='else')
    if not any(n['title']=='Get bToolReleasing' for n in g['nodes']):
        ops=[dict(op='add_node',ref='releasing',node_type='variable_get',variable_name='bToolReleasing',x=900,y=1250),
            dict(op='add_node',ref='busy',node_type='call_function',function_name='/Script/Engine.KismetMathLibrary:BooleanOR',x=1200,y=1150),
            dict(op='add_node',ref='guard',node_type='branch',x=1500,y=1000),
            dict(op='connect',from_node=active,from_pin='bToolActive',to_node='busy',to_pin='A'),
            dict(op='connect',from_node='releasing',from_pin='bToolReleasing',to_node='busy',to_pin='B'),
            dict(op='connect',from_node='busy',from_pin='ReturnValue',to_node='guard',to_pin='Condition'),
            dict(op='disconnect',node_id=transaction,pin_name='else'),
            dict(op='connect',from_node=transaction,from_pin='else',to_node='guard',to_pin='execute'),
            dict(op='connect',from_node='guard',from_pin='else',to_node=entry['to_node'],to_pin=entry['to_pin']),
            dict(op='comment',title='Finish the current action',node_ids=['releasing','busy','guard'],color=[.2,.35,.4])]
        call('blueprint_graph_batch',path=path,graph_name='ApplyRow',ops=ops,compile=True,save=True)
    compiled=call('blueprint_compile',path=path,save=True)
    assert compiled['error_count']==0 and compiled['warning_count']==0 and compiled['saved'],compiled
    after=call('blueprint_inspect_graph',path=path,graph_name='ApplyRow')
    Path('P:/FoA/Saved/Integration/door_reentry_fix.json').write_text(json.dumps(dict(before=g,after=after,compile=compiled),indent=1))
    print('Saved ApplyRow session guard; active/releasing blocks new work, current commit remains allowed')
finally:h.release(owner,token)
