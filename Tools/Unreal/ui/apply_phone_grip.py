"""Native Phone-only socket fit; no Player, shared rig or input-lock edits."""
import json,sys,shutil,datetime
from pathlib import Path
from scipy.spatial.transform import Rotation
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch,inspect,find
P='/Game/FoA/UI/Game/BP_Phone';A='/Game/FoA/Characters/Player/Anims/AS_FoA_PhoneHold'
assert not h.call('editor_get_state')['data']['pie_running']
owner=h.agent_id();lease=h.lease_acquire(owner,['asset:'+P,'asset:'+A],ttl_s=45,wait_s=4)
try:
    folder=Path('P:/FoA/Saved/Backups/phone_grip')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');folder.mkdir(parents=True)
    for path in (P,A):shutil.copy2(Path('P:/FoA/Content')/(path.removeprefix('/Game/')+'.uasset'),folder/(path.rsplit('/',1)[1]+'.uasset'))
    result=h.call('python_exec_file',dict(path='P:/FoA/Tools/Unreal/ui/ue_fit_phone_fingers.py',env={},resources=['asset:'+A]),owner=owner,lease=lease)
    assert result.get('ok'),result
    fit=json.loads(Path('P:/FoA/Saved/UIShots/phone_grip_fit.json').read_text());roll,pitch,yaw=Rotation.from_quat(fit['relative_quaternion']).as_euler('xyz',degrees=True)
    nodes,edges=inspect(P,'OpenPhone');byid={n['node_id']:n for n in nodes}
    old=next(n['node_id'] for n in nodes if n['title'].replace(' ','')=='AttachActorToActor')
    position=next(n['node_id'] for n in nodes if n['title'].replace(' ','')=='SetActorRelativeLocation')
    rotation=next(n['node_id'] for n in nodes if n['title'].replace(' ','')=='MakeRotator')
    cast=next(n['node_id'] for n in nodes if n['title'].replace(' ','').replace('_','')=='CastToBPFoAPlayer')
    previous=next(e for e in edges if e['to_node']==old and e['to_pin']=='execute')
    b=Batch(P,'OpenPhone');b.get('gripbody','Body',1500,650,'/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C')
    b.link(cast,'AsBP Fo APlayer','gripbody','self')
    b.fn('socket','/Script/Engine.Actor:K2_AttachToComponent',1500,0,SocketName='hand_r',LocationRule='KeepRelative',RotationRule='KeepRelative',ScaleRule='KeepWorld',bWeldSimulatedBodies=False)
    b.link('gripbody','Body','socket','Parent');b.cut(previous['from_node'],previous['from_pin'],old,'execute')
    b.link(previous['from_node'],previous['from_pin'],'socket','execute');b.link('socket','then',position,'execute')
    b.ops.append(dict(op='remove',node_ids=[old]))
    b.pin(position,'NewRelativeLocation','(X=%0.9f,Y=%0.9f,Z=%0.9f)'%tuple(fit['relative_location']))
    for pin,value in [('Roll',-roll),('Pitch',-pitch),('Yaw',yaw)]:b.pin(rotation,pin,value)
    b.comment('Phone corner held by live fingers',['gripbody','socket']);b.run()
finally:h.release(owner,lease)
