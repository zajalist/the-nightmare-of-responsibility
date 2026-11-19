"""Coordinator-cleared key-only constants. Does not rebuild animations or Player graphs."""
import json,os,sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch,inspect,PLAYER,DOOR

owner='clothing_search';os.environ['HAYBA_AGENT_ID']=owner
cal=json.loads(Path('Saved/AnimShots/teen_key_pinch_measured_calibration.json').read_text())
def call(name,**kw):
    r=h.call(name,kw,owner=owner);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True),d;return d

assert not call('editor_get_state')['pie_running'],'User PIE active'
token=h.lease_acquire(owner,['asset:'+PLAYER,'asset:'+DOOR],ttl_s=60,wait_s=3)
try:
    nodes,edges=inspect(PLAYER,'SetToolHandRotation');byid={n['node_id']:n for n in nodes}
    # Driver inverse reads ToolGripOffset; key inverse reads the explicit pinch transform.
    candidates=[e['from_node'] for e in edges if e['to_pin']=='T' and
        byid[e['to_node']]['title']=='InvertTransform' and byid[e['from_node']]['title']=='MakeTransform']
    assert len(candidates)==1,candidates
    pinch=candidates[0]
    rot=next(e['from_node'] for e in edges if e['to_node']==pinch and e['to_pin']=='Rotation')
    assert byid[rot]['title']=='MakeRotator'
    b=Batch(PLAYER,'SetToolHandRotation')
    b.pin(pinch,'Location',','.join(map(str,cal['location'])))
    b.pin(pinch,'Scale',','.join(map(str,cal['scale'])))
    for name,value in cal['rotation_degrees'].items():b.pin(rot,name,value)
    b.run()
    nodes,edges=inspect(DOOR,'RefreshDoorTool')
    def defaults(node):return {p['name']:p.get('default_value',p.get('default','')) for p in node.get('pins',[]) if p.get('direction')=='input'}
    candidates=[]
    for n in nodes:
        if n['title']!='SelectFloat':continue
        pins=defaults(n)
        try:
            if abs(float(pins.get('B','nan'))+16)<.001 and float(pins.get('A','nan'))<0:candidates.append(n['node_id'])
        except ValueError:pass
    assert len(candidates)==1,candidates
    b=Batch(DOOR,'RefreshDoorTool');b.pin(candidates[0],'A',-cal['key_grip_distance_cm']);b.run()
    Path('Saved/Integration/key_pinch_applied.json').write_text(json.dumps(dict(calibration=cal,
        player_nodes=[pinch,rot],door_node=candidates[0],runtime_verified=False),indent=1))
    print('Measured key-only constants saved; repeat capture required')
finally:h.release(owner,token)
