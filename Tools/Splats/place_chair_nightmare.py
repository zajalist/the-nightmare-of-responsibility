"""Place only the owned chair-vision controller and bind existing room references."""
import json,sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
import editor_lock
P='/Game/FoA/Gameplay/Ambient/BP_ChairNightmare';C=P+'.BP_ChairNightmare_C'
WORLD='/Game/FoA/Maps/L_Tutorial_Bedroom.L_Tutorial_Bedroom:PersistentLevel.'
def call(cmd,**p):
    r=h.call(cmd,p);assert r.get('ok'),r
    return r['data']
assert not call('editor_get_state')['pie_running']
actors=call('actor_list',class_filter='StaticMeshActor')['actors']
chair=next(a for a in actors if a['label']=='Chair');room=call('actor_list',class_filter='BP_RoomTakeover_C')['actors'][0]
chairpath=WORLD+chair['id']+'.StaticMeshComponent0'
names=['StaticMesh','OverrideMaterials','OverlayMaterial','RelativeLocation','RelativeRotation','RelativeScale3D','bVisible','bHiddenInGame','BodyInstance']
before=call('object_get_property',path=chairpath,names=names)
lease=h.lease_acquire(h.agent_id(),editor_lock.actor_keys(new_prefixes=['ChairNightmare']),ttl_s=60,wait_s=30)
try:
    found=call('actor_list',class_filter='BP_ChairNightmare_C')['actors']
    actor=found[0] if found else call('actor_spawn',class_path=C,location=[0,0,0],label='ChairNightmare')
    aid=actor.get('id',actor.get('actor_id'));path=WORLD+aid
    call('object_set_property',path=path,properties={'ChairMesh':chairpath,'Takeover':WORLD+room['id']})
    after=call('object_get_property',path=chairpath,names=names)
    assert before['properties']==after['properties'],'Chair modified during placement'
    report={'controller':path,'chair':chairpath,'chair_snapshot':before['properties'],'takeover':WORLD+room['id']}
    out=Path('P:/FoA/Saved/WorldShots/chair_nightmare');out.mkdir(parents=True,exist_ok=True)
    (out/'editor_snapshot.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:h.release(h.agent_id(),lease)
