"""Two narrow C++ graph fixes after editor recovery: foot_ik or wardrobe. No ABP, sleep or mesh assignment edits."""
import json
from pathlib import Path
import sys

sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as hc

OWNER='mh_cinematic_poses'
PLAYER='/Game/FoA/Characters/Player/BP_FoAPlayer'
INTERACTABLE='/Game/FoA/Gameplay/BP_Interactable'
TOKEN=None


def call(name,**params):
    response=hc.call(name,params,owner=OWNER,lease=TOKEN)
    assert response.get('ok'),response
    data=response.get('data',{});assert data.get('ok',True),data
    return data


def norm(value):return ''.join(str(value).lower().split())


def connect(a,b,ap='then',bp='execute'):
    return dict(op='connect',from_node=a,from_pin=ap,to_node=b,to_pin=bp)


def foot_ik(graph):
    nodes=graph['nodes'];edges=graph['edges'];by_id={n['node_id']:n for n in nodes}
    setter=next(n for n in nodes if norm(n['title'])=='setfootikenabled')
    edge=next(e for e in edges if e['to_node']==setter['node_id'] and e['to_pin']=='FootIKEnabled')
    invert=by_id[edge['from_node']]
    assert norm(invert['title']) in ('not','notboolean','not(boolean)'),invert
    source=next(e for e in edges if e['to_node']==invert['node_id'] and e['to_pin']=='A')
    if norm(by_id[source['from_node']]['title']) in ('or','orboolean','or(boolean)'):
        assert any(norm(n['title']) in ('getbinteractionlocked','getinteractionlocked') for n in nodes)
        return []
    assert norm(by_id[source['from_node']]['title']) in ('getbcinematic','getcinematic'),source
    return [dict(op='disconnect',node_id=invert['node_id'],pin_name='A'),
        dict(op='add_node',ref='interaction_pose',node_type='variable_get',variable_name='bInteractionLocked',x=1400,y=760),
        dict(op='add_node',ref='authored_pose',node_type='call_function',
             function_name='/Script/Engine.KismetMathLibrary:BooleanOR',x=1700,y=600),
        connect(source['from_node'],'authored_pose',source['from_pin'],'A'),
        connect('interaction_pose','authored_pose','bInteractionLocked','B'),
        connect('authored_pose',invert['node_id'],'ReturnValue','A'),dict(op='fit_comments')]


def wardrobe(graph):
    nodes=graph['nodes'];edges=graph['edges'];by_id={n['node_id']:n for n in nodes}
    event=next(n for n in nodes if norm(n['title'])=='wardrobebeginfall')
    entry=next(e for e in edges if e['from_node']==event['node_id'] and e['from_pin']=='then')
    gate=by_id[entry['to_node']];assert norm(gate['title'])=='branch',gate
    old=next(e for e in edges if e['from_node']==gate['node_id'] and e['from_pin']=='then')
    if norm(by_id[old['to_node']]['title']).startswith('playanimmontage'):return []
    assert norm(by_id[old['to_node']]['title']).startswith('movecomponentto'),old
    return [dict(op='disconnect',node_id=gate['node_id'],pin_name='then'),
        dict(op='add_node',ref='reaction_player',node_type='call_function',
             function_name='/Script/Engine.GameplayStatics:GetPlayerCharacter',x=1152,y=2480),
        dict(op='set_pin',node_id='reaction_player',pin_name='PlayerIndex',value='0'),
        dict(op='add_node',ref='fall_reaction',node_type='call_function',
             function_name='/Script/Engine.Character:PlayAnimMontage',x=1472,y=2256),
        dict(op='set_pin',node_id='fall_reaction',pin_name='AnimMontage',
             value='/Game/FoA/Characters/Player/Montages/AM_FoA_Startle.AM_FoA_Startle'),
        connect('reaction_player','fall_reaction','ReturnValue','self'),
        connect(gate['node_id'],'fall_reaction'),connect('fall_reaction',old['to_node'],'then',old['to_pin']),
        dict(op='comment',title='React to the falling wardrobe',node_ids=['reaction_player','fall_reaction'],color=[.22,.4,.2]),
        dict(op='fit_comments')]


def main():
    global TOKEN
    mode=sys.argv[1];assert mode in ('foot_ik','wardrobe')
    path,graph_name=(PLAYER,'PushAnimState') if mode=='foot_ik' else (INTERACTABLE,'EventGraph')
    assert not call('editor_get_state')['pie_running'],'User/coordinator must end PIE before mutations'
    TOKEN=hc.lease_acquire(OWNER,['asset:'+path],ttl_s=90,wait_s=15)
    try:
        before=call('blueprint_inspect_graph',path=path,graph_name=graph_name)
        ops=(foot_ik if mode=='foot_ik' else wardrobe)(before)
        if ops:call('blueprint_graph_batch',path=path,graph_name=graph_name,ops=ops,compile=True,save=True)
        compiled=call('blueprint_compile',path=path,save=True)
        assert compiled['error_count']==0 and compiled['warning_count']==0 and compiled['saved'] and not compiled['dirty'],compiled
        after=call('blueprint_inspect_graph',path=path,graph_name=graph_name)
        assert not (foot_ik if mode=='foot_ik' else wardrobe)(after),'Patch did not survive compile'
        Path('P:/FoA/Saved/CharacterShots/cinematic_'+mode+'_fix.json').write_text(json.dumps(
            dict(mode=mode,path=path,operations=ops,compile=compiled,before=before,after=after),indent=2))
        print('Saved clean cinematic pose fix:',mode,'; actual visible montage proof still required')
    finally:hc.release(OWNER,TOKEN)


if __name__=='__main__':main()
