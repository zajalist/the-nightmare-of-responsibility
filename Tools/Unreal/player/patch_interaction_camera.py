"""Restore a missing interaction look hook without rebuilding the player's camera graphs.

Import is offline-safe. Run only in an assigned, non-PIE Player asset window.
Existing interaction-look hooks are preserved; only a confirmed torso-feedback
connection is redirected to the previous control view.
"""
import json
import os
from pathlib import Path
import shutil
import sys

sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch,inspect

P='/Game/FoA/Characters/Player/BP_FoAPlayer'
F='UpdateFirstPersonVisibility'
K='/Script/Engine.KismetMathLibrary:'
GS='/Script/Engine.GameplayStatics:'
SC='/Script/Engine.SceneComponent:'
MARKER='Keep interaction contact in view'


def norm(title):return title.replace(' ','').replace('_','').lower()


def unique(nodes,title):
    ids=[n['node_id'] for n in nodes if norm(n['title'])==norm(title)]
    assert len(ids)==1,(title,ids)
    return ids[0]


def following(edges,node):
    hits=[e for e in edges if e['from_node']==node and e['from_pin']=='then' and e['to_pin']=='execute']
    assert len(hits)==1,('Expected one preserved execution successor',node,hits)
    return hits[0]


def remember_plan(nodes,edges):
    b=Batch(P,'EventGraph')
    if any(norm(n['title'])=='setinteractlook' for n in nodes):return b
    entry=unique(nodes,'Event LockForInteraction');after=following(edges,entry)
    b.set('remember_contact','InteractLook',300,-200)
    b.link(entry,'Target','remember_contact','InteractLook')
    b.cut(entry,'then',after['to_node'],after['to_pin'])
    b.chain(entry,'remember_contact');b.link('remember_contact','then',after['to_node'],after['to_pin'])
    b.comment('Remember interaction target',['remember_contact'])
    return b


def camera_plan(nodes,edges):
    b=Batch(P,F)
    if any(norm(n['title'])=='getinteractlook' for n in nodes):return b
    setter=unique(nodes,'Set FPViewRotation');after=following(edges,setter)
    b.get('target','InteractLook',1700,-500)
    b.fn('valid','/Script/Engine.KismetSystemLibrary:IsValid',1950,-500)
    b.link('target','InteractLook','valid','Object')
    b.get('locked','bInteractionLocked',1700,-700)
    b.fn('held',K+'BooleanAND',2200,-700)
    b.link('locked','bInteractionLocked','held','A');b.link('valid','ReturnValue','held','B')
    b.get('cine','bCinematic',1700,-1000);b.get('battle','bBattleActive',1700,-1150)
    b.fn('authored',K+'BooleanOR',1950,-1000)
    b.link('cine','bCinematic','authored','A');b.link('battle','bBattleActive','authored','B')
    b.fn('available',K+'Not_PreBool',2200,-1000);b.link('authored','ReturnValue','available','A')
    b.fn('pc',GS+'GetPlayerController',1700,-1350,PlayerIndex=0)
    b.fn('view','/Script/Engine.PlayerController:GetViewTarget',1950,-1350);b.link('pc','ReturnValue','view','self')
    b.node('me','self',1950,-1500);b.fn('direct',K+'EqualEqual_ObjectObject',2200,-1350)
    b.link('view','ReturnValue','direct','A');b.link('me','self','direct','B')
    b.fn('owns',K+'BooleanAND',2450,-1000)
    b.link('available','ReturnValue','owns','A');b.link('direct','ReturnValue','owns','B')
    b.fn('allowed',K+'BooleanAND',2700,-700)
    b.link('held','ReturnValue','allowed','A');b.link('owns','ReturnValue','allowed','B')
    b.node('guard','branch',2950,-900);b.link('allowed','ReturnValue','guard','Condition')
    # Bounds are only evaluated behind the valid-target execution branch.
    b.fn('bounds','/Script/Engine.Actor:GetActorBounds',2200,-250,bOnlyCollidingComponents=True)
    b.link('target','InteractLook','bounds','self')
    b.get('mesh','EnvironmentContactMesh',2200,100)
    b.fn('contact_valid','/Script/Engine.KismetSystemLibrary:IsValid',2450,100)
    b.link('mesh','EnvironmentContactMesh','contact_valid','Object')
    b.get('contact','EnvironmentContactAim',2450,250)
    b.fn('point',K+'SelectVector',2700,100)
    b.link('contact','EnvironmentContactAim','point','A');b.link('bounds','Origin','point','B')
    b.link('contact_valid','ReturnValue','point','bPickA')
    b.get('camera','FollowCamera',2450,-400)
    b.fn('eye',SC+'K2_GetComponentLocation',2700,-400);b.link('camera','FollowCamera','eye','self')
    b.fn('aim',K+'FindLookAtRotation',2950,-250)
    b.link('eye','ReturnValue','aim','Start');b.link('point','ReturnValue','aim','Target')
    # Ease from the previous control view without feeding the torso clamp back into it each frame.
    b.fn('current','/Script/Engine.Controller:GetControlRotation',2950,100);b.link('pc','ReturnValue','current','self')
    b.fn('dt',GS+'GetWorldDeltaSeconds',2950,250)
    b.fn('ease',K+'RInterpTo',3200,-250,InterpSpeed=4.5)
    b.link('current','ReturnValue','ease','Current');b.link('aim','ReturnValue','ease','Target');b.link('dt','ReturnValue','ease','DeltaTime')
    b.fn('parts',K+'BreakRotator',3450,-250);b.link('ease','ReturnValue','parts','InRot')
    b.fn('pitch',K+'FClamp',3700,-250,Min=-65,Max=65);b.link('parts','Pitch','pitch','Value')
    b.fn('flat',K+'MakeRotator',3950,-250,Roll=0)
    b.link('pitch','ReturnValue','flat','Pitch');b.link('parts','Yaw','flat','Yaw')
    b.set('look','FPViewRotation',4200,-900);b.link('flat','ReturnValue','look','FPViewRotation')
    b.cut(setter,'then',after['to_node'],after['to_pin']);b.chain(setter,'guard','look')
    b.link('guard','else',after['to_node'],after['to_pin']);b.link('look','then',after['to_node'],after['to_pin'])
    b.get('viewnow','FPViewRotation',4450,-250)
    for edge in edges:
        if edge['from_node']==setter and edge['from_pin']=='Output_Get':
            b.cut(setter,'Output_Get',edge['to_node'],edge['to_pin'])
            b.link('viewnow','FPViewRotation',edge['to_node'],edge['to_pin'])
    b.comment(MARKER,[o['ref'] for o in b.ops if 'ref' in o])
    return b


def legacy_feedback_plan(nodes,edges):
    """Keep an existing target-look extension, but stop resetting its easing to torso clamp."""
    b=Batch(P,F);byid={n['node_id']:n for n in nodes}
    aims={n['node_id'] for n in nodes if norm(n['title'])=='findlookatrotation'}
    eases={e['to_node'] for e in edges if e['from_node'] in aims and e['to_pin']=='Target'
           and norm(byid[e['to_node']]['title'])=='rinterpto'}
    assert len(eases)==1,('Ambiguous interaction look interpolation',eases)
    ease=next(iter(eases))
    current=next(e for e in edges if e['to_node']==ease and e['to_pin']=='Current')
    if norm(byid[current['from_node']]['title'])=='getcontrolrotation':return b
    assert norm(byid[current['from_node']]['title'])=='setfpviewrotation',current
    control=unique(nodes,'GetControlRotation')
    b.cut(current['from_node'],current['from_pin'],ease,'Current')
    b.link(control,'ReturnValue',ease,'Current')
    return b


def contact_guard_plan(nodes,edges):
    """A live hand contact can exist without LockForInteraction's optional Target."""
    b=Batch(P,F)
    byid={n['node_id']:n for n in nodes}
    target=unique(nodes,'Get InteractLook')
    if any(e['from_node']==target and e['to_pin']=='Option 1'
           and norm(byid[e['to_node']]['title'])=='select' for e in edges):return b
    valid=next(e['to_node'] for e in edges if e['from_node']==target and e['to_pin']=='Object')
    bounds=next(e['to_node'] for e in edges if e['from_node']==target and e['to_pin']=='self'
                and norm(byid[e['to_node']]['title'])=='getactorbounds')
    mesh=unique(nodes,'Get EnvironmentContactMesh')
    live=next(e['to_node'] for e in edges if e['from_node']==mesh and e['to_pin']=='Object')
    guard=next(e for e in edges if e['from_node']==valid and norm(byid[e['to_node']]['title'])=='andboolean')
    b.fn('hascontact',K+'BooleanOR',2200,-1100)
    b.link(valid,'ReturnValue','hascontact','A');b.link(live,'ReturnValue','hascontact','B')
    b.cut(valid,'ReturnValue',guard['to_node'],guard['to_pin'])
    b.link('hascontact','ReturnValue',guard['to_node'],guard['to_pin'])
    # SelectVector evaluates both pure inputs: give its unused bounds input a valid actor.
    b.node('camera_self','self',1700,-1500)
    b.node('safeactor','select',1950,-1400)
    b.link(target,'InteractLook','safeactor','Option 1');b.link('camera_self','self','safeactor','Option 0')
    b.link(valid,'ReturnValue','safeactor','Index')
    b.cut(target,'InteractLook',bounds,'self');b.link('safeactor','ReturnValue',bounds,'self')
    b.pin(bounds,'bOnlyCollidingComponents','true')
    b.comment('Aim at live contact safely',['hascontact','camera_self','safeactor'])
    return b


def apply_missing():
    nodes,edges=inspect(P,F)
    b=camera_plan(nodes,edges)
    if not b.ops:
        b=legacy_feedback_plan(nodes,edges)
        changed=bool(b.ops)
        if b.ops:b.run()
        contact=contact_guard_plan(*inspect(P,F))
        if contact.ops:contact.run();changed=True
        print('Existing interaction look preserved; contact and prior-view repairs applied',changed)
        return changed
    result=h.call('blueprint_add_variable',dict(path=P,variable_name='InteractLook',variable_type='object:/Script/Engine.Actor',
                  instance_editable=False,update_existing=True,category='Camera'))
    assert result.get('ok'),result
    remembering=remember_plan(*inspect(P,'EventGraph'))
    if remembering.ops:remembering.run()
    b.run()
    contact=contact_guard_plan(*inspect(P,F))
    if contact.ops:contact.run()
    return True


def main():
    owner=h.agent_id() or 'main-level1-camera'
    os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner)
    assert not h.call('editor_get_state',{},owner=owner)['data']['pie_running']
    token=h.lease_acquire(owner,['asset:'+P],ttl_s=60,wait_s=3)
    old=os.environ.get('FOA_LEASE');os.environ['FOA_LEASE']=token
    try:
        out=Path('P:/FoA/Saved/Integration/l1_interaction_camera');out.mkdir(parents=True,exist_ok=True)
        for graph in ('EventGraph',F):
            nodes,edges=inspect(P,graph)
            (out/(graph+'_before.json')).write_text(json.dumps(dict(nodes=nodes,edges=edges),indent=1))
        backup=Path('P:/FoA/Saved/Backups/level-integration-20261111/BP_FoAPlayer_before_interaction_camera.uasset')
        if not backup.exists():
            backup.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2('P:/FoA/Content/FoA/Characters/Player/BP_FoAPlayer.uasset',backup)
        changed=apply_missing()
        (out/'result.json').write_text(json.dumps(dict(changed=changed)))
        if changed:
            for graph in ('EventGraph',F):
                nodes,edges=inspect(P,graph)
                (out/(graph+'_after.json')).write_text(json.dumps(dict(nodes=nodes,edges=edges),indent=1))
    finally:
        h.release(owner,token)
        if old is None:os.environ.pop('FOA_LEASE',None)
        else:os.environ['FOA_LEASE']=old


if __name__=='__main__':main()
