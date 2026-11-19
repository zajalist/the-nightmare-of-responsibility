"""15lm shirt-only contact readability, owned by existing contact update/cleanup."""
import sys,os,json,shutil,datetime,subprocess
from pathlib import Path
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch,inspect
P='/Game/FoA/Gameplay/Encounter/BP_Garment';SC='/Script/Engine.SceneComponent:';LC='/Script/Engine.LightComponent:';K='/Script/Engine.KismetMathLibrary:'
owner='character_contact_fill';os.environ['HAYBA_AGENT_ID']=owner
norm=lambda s:''.join(s.lower().split())
def call(cmd,**kw):
    r=h.call(cmd,kw);assert r.get('ok'),r;return r['data']
assert not call('editor_get_state')['pie_running']
token=h.lease_acquire(owner,['asset:'+P],ttl_s=90,wait_s=3)
try:
    backup=Path('Saved/Backups/contact_fill')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
    shutil.copy2('Content/FoA/Gameplay/Encounter/BP_Garment.uasset',backup/'BP_Garment.uasset')
    info=call('blueprint_get_info',path=P)
    if not any(c['name']=='ContactFill' for c in info['components']):
        call('blueprint_add_component',path=P,component_class_path='/Script/Engine.PointLightComponent',component_name='ContactFill')
    call('object_set_property',path=P+'.BP_Garment_C:ContactFill_GEN_VARIABLE',properties={
        'IntensityUnits':'Lumens','Intensity':0.,'AttenuationRadius':170.,'SourceRadius':8.,'CastShadows':False,
        'VolumetricScatteringIntensity':0.,'SpecularScale':.2,'LightingChannels':'(bChannel0=False,bChannel1=True,bChannel2=False)','Mobility':'Movable'})
    # Native AddComponent replaces an inherited DefaultSceneRoot: restore a plain root
    # before any light movement can affect Mesh/Rig or actor flight.
    env=dict(os.environ,FOA_AGENT=owner,FOA_AREAS='asset:'+P,FOA_ACTORS_NEW='TMP_character_')
    subprocess.run([sys.executable,'Tools/Unreal/ue_remote.py','Tools/Unreal/encounter/fix_contact_fill_root.py'],env=env,check=True)
    for graph in ('StartPlayerContact','StepPlayerContact','StopPlayerContact'):
        ns,es=inspect(P,graph);assert not any(norm(n['title'])=='getcontactfill' for n in ns),'Already applied'
        b=Batch(P,graph);b.get('fill','ContactFill',4800,600)
        if graph=='StepPlayerContact':
            place=next(n['node_id'] for n in ns if norm(n['title'])=='setworldlocation')
            socket=next(n['node_id'] for n in ns if any(p.get('default_value')=='index_03_l' for p in n['pins']))
            target=next(e['to_node'] for e in es if e['from_node']==socket and e['from_pin']=='ReturnValue')
            ease=next(n['node_id'] for n in ns if norm(n['title'])=='ease') if any(norm(n['title'])=='ease' for n in ns) else next(n['node_id'] for n in ns if 'finterpease' in norm(n['title']))
            b.fn('pos',K+'Add_VectorVector',4200,450,B='50,-70,35');b.link(target,'ReturnValue','pos','A')
            b.fn('move',SC+'K2_SetWorldLocation',4200,100,bSweep=False,bTeleport=True);b.link('fill','ContactFill','move','self');b.link('pos','ReturnValue','move','NewLocation')
            b.fn('brightness',K+'Multiply_DoubleDouble',4500,450,B=15);b.link(ease,'ReturnValue','brightness','A')
            b.fn('intensity',LC+'SetIntensity',4800,100);b.link('fill','ContactFill','intensity','self');b.link('brightness','ReturnValue','intensity','NewIntensity');b.chain(place,'move','intensity')
        else:
            b.get('rig_fill','Rig',3000,600)
            b.fn('channels','/Script/Engine.PrimitiveComponent:SetLightingChannels',3300,100,bChannel0=True,bChannel1=graph=='StartPlayerContact',bChannel2=False);b.link('rig_fill','Rig','channels','self')
            if graph=='StartPlayerContact':
                tail=next(n['node_id'] for n in ns if norm(n['title'])=='setbplayercontact');b.chain(tail,'channels')
            else:
                entry=next(n['node_id'] for n in ns if norm(n['title'])=='stopplayercontact');edge=next(e for e in es if e['from_node']==entry and e['from_pin']=='then')
                b.fn('off',LC+'SetIntensity',3000,100,NewIntensity=0);b.link('fill','ContactFill','off','self')
                b.cut(entry,'then',edge['to_node'],edge['to_pin']);b.chain(entry,'off','channels');b.link('channels','then',edge['to_node'],edge['to_pin'])
        b.comment('Shirt contact fill',[o['ref'] for o in b.ops if 'ref' in o]);b.run()
    Path('Saved/Integration/cinematic_audit/contact_fill/apply.json').write_text(json.dumps(dict(backup=str(backup),intensity_lm=15,channel=1,off_outside_contact=True),indent=2))
finally:h.release(owner,token)
