"""Propagate owned SCS defaults to the existing room actor, preserving references.

Native template writes do not update an already placed actor's new components.
Audit first; --apply requires no PIE and a scoped world lease.
"""
import json,re,sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Splats')
from build_room_takeover import P,C,PARTS,call,h
from build_clothing_clues import layout
from build_vase_boss_scene import asset_parts
ACTOR='/Game/FoA/Maps/L_Tutorial_Bedroom.L_Tutorial_Bedroom:PersistentLevel.BP_RoomTakeover_C_1'
OUT=Path('P:/FoA/Saved/WorldShots/takeover_instance_sync.json')

def audit():
    clues,markers=layout(json.loads(Path('P:/FoA/Saved/Integration/clothing_clue_surfaces.json').read_text()))
    mesh_names=[r[0] for r in PARTS]+['ScareSuit','CanvasHorse','CanvasLion','PaintingLeak']+[r['name'] for r in clues]+[r[0] for r in asset_parts()]
    scene_names=list(markers)+['ClueFocusVase','ClueViewVase','ClueFocusBoss','ClueViewBoss']
    audio_names=['SandRise','ScareImpact','PaintingSound','VaseBreakSound','VaseSandSound']
    rows=[]
    for name in mesh_names+scene_names+audio_names:
        props=['RelativeLocation','RelativeRotation','RelativeScale3D','Mobility','bVisible']
        if name in mesh_names:props+=['StaticMesh','OverrideMaterials','CastShadow','bGenerateOverlapEvents','BodyInstance','bRenderCustomDepth','CustomDepthStencilValue']
        if name in audio_names:props+=['Sound','bAutoActivate','VolumeMultiplier']
        template=call('object_get_property',path=C+':'+name+'_GEN_VARIABLE',names=props)['properties']
        actual=call('object_get_property',path=ACTOR+'.'+name,names=props)['properties']
        # ExportText for BodyInstance is truncated by the bounded native reader.
        # Compare only the required collision state and set the short import form.
        for values in (template,actual):
            if 'BodyInstance' in values and 'CollisionEnabled=NoCollision' in values['BodyInstance']:
                values['BodyInstance']='(CollisionProfileName="NoCollision",CollisionEnabled=NoCollision)'
        changes={k:v for k,v in template.items() if v!=actual.get(k)}
        if name in [r[0] for r in PARTS]:changes.pop('RelativeScale3D',None) # Stage0 is deliberately zeroed.
        rows.append(dict(name=name,template=template,actual=actual,changes=changes))
    return rows

def native_value(key,value):
    if key in ('StaticMesh','Sound'):
        return re.search(r"'([^']+)'",value).group(1) if value!='None' else None
    if key=='OverrideMaterials':return re.findall(r"'([^']+)'",value)
    if value in ('True','False'):return value=='True'
    return value

def main():
    token=None
    try:
        if '--apply' in sys.argv:
            assert not call('editor_get_state')['pie_running']
            token=h.lease_acquire('room-takeover',['asset:'+P,'actor:'+ACTOR],ttl_s=80,wait_s=20)
            assert not call('editor_get_state')['pie_running']
        rows=audit();before=[r for r in rows if r['changes']]
        if token:
            for row in before:
                call('object_set_property',path=ACTOR+'.'+row['name'],properties={k:native_value(k,v) for k,v in row['changes'].items()})
            call('level_save')
            remaining=[r for r in audit() if r['changes']]
            assert not remaining,remaining
        else:remaining=before
        OUT.write_text(json.dumps(dict(applied=bool(token),before=before,remaining=remaining),indent=1))
        print(json.dumps(dict(applied=bool(token),changed_components=len(before),remaining=len(remaining),names=[r['name'] for r in before])))
    finally:
        if token:h.release('room-takeover',token)
if __name__=='__main__':main()
