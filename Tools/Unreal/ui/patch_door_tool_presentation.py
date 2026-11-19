"""Feed existing physical angle/bind data into the compact HUD; no gameplay changes."""
import os,sys
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
sys.path.insert(0,'P:/FoA/Tools/Unreal/player');from held_tool_graphs import Batch,inspect,find
HUD='/Game/FoA/UI/Game/WBP_HUD';DOOR='/Game/FoA/Gameplay/BP_Door'
K='/Script/Engine.KismetMathLibrary:'

def build():
    ns,es=inspect(DOOR,'RefreshDoorTool')
    if any(n['title']=='SetToolFeedback' for n in ns):return
    shown=[n['node_id'] for n in ns if n['title']=='ShowToolStatus'];assert len(shown)==2
    targets=[next(e for e in es if e['to_node']==n and e['to_pin']=='self') for n in shown]
    assert targets[0]['from_node']==targets[1]['from_node']
    assert not [e for e in es if e['from_node'] in shown and e['from_pin']=='then']
    b=Batch(DOOR,'RefreshDoorTool')
    formats=[(n,p.get('default_text',p.get('default_value'))) for n in ns for p in n['pins'] if p['name']=='Format' and (p.get('default_text') or p.get('default_value'))]
    assert any('screw {N}' in text.lower().replace('{n}','{N}') for _,text in formats)
    assert any('{Hint}' in text for _,text in formats)
    for n,text in formats:
        wanted='Loosen screw {N} of 4' if 'screw' in text.lower() else '{Hint}'
        if text!=wanted:
            # Format Text reconstructs its argument pins. This native writer can
            # report verified:false after succeeding; verify the actual FText.
            h.call('blueprint_graph_batch',dict(path=DOOR,graph_name='RefreshDoorTool',ops=[
                dict(op='set_pin',node_id=n['node_id'],pin_name='Format',value=wanted)],compile=False,save=False))
            observed,_=inspect(DOOR,'RefreshDoorTool')
            changed=next(x for x in observed if x['node_id']==n['node_id'])
            assert next(p.get('default_text') for p in changed['pins'] if p['name']=='Format')==wanted
    hints={'Find the catch. Turn slowly.':'Find the catch',
        'It is moving. Keep gentle pressure.':'Keep gentle pressure',
        'It binds here. Ease back until it loosens.':'Ease back',
        'Try again. Keep the pressure steady.':'Turn again'}
    for n in ns:
        for p in n['pins']:
            if p.get('default_value') in hints:b.pin(n['node_id'],p['name'],hints[p['default_value']])
    b.get('mode','ToolMode',7200,600);b.fn('key',K+'EqualEqual_NameName',7500,600,B='Key');b.link('mode','ToolMode','key','A')
    b.get('angle','ToolAngle',7200,850);b.fn('range',K+'SelectFloat',7500,850,A=55.,B=720.);b.link('key','ReturnValue','range','bPickA')
    b.fn('progress',K+'Divide_DoubleDouble',7800,850);b.link('angle','ToolAngle','progress','A');b.link('range','ReturnValue','progress','B')
    b.fn('clamp',K+'FClamp',8100,850,Min=0,Max=1);b.link('progress','ReturnValue','clamp','Value')
    b.get('stage','ToolStepIndex',7200,1100);b.fn('bound_stage',K+'EqualEqual_IntInt',7500,1100,B=2);b.link('stage','ToolStepIndex','bound_stage','A')
    b.fn('bound',K+'BooleanAND',7800,1100);b.link('key','ReturnValue','bound','A');b.link('bound_stage','ReturnValue','bound','B')
    b.fn('feedback',HUD+'.WBP_HUD_C:SetToolFeedback',8400,0)
    b.link(targets[0]['from_node'],targets[0]['from_pin'],'feedback','self')
    b.link('clamp','ReturnValue','feedback','Progress');b.link('bound','ReturnValue','feedback','bBound')
    for n in shown:b.chain(n,'feedback')
    b.comment('Show the actual turn and binding point',['mode','key','angle','range','progress','clamp','stage','bound_stage','bound','feedback']);b.run()

if __name__=='__main__':
    owner='clothing_search';os.environ['HAYBA_AGENT_ID']=owner
    assert not h.call('editor_get_state')['data']['pie_running']
    token=h.lease_acquire(owner,['asset:'+HUD,'asset:'+DOOR],ttl_s=90,wait_s=3);os.environ['FOA_LEASE']=token
    try:build()
    finally:h.release(owner,token);os.environ.pop('FOA_LEASE',None)
