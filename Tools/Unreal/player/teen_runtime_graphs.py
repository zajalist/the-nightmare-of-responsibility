"""Keep the player API and replace MH-specific wardrobe/eyelid internals with Teen pieces.
Run after the component swap and inventory probe, under a player lease.
"""
import json, re, sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
from held_tool_graphs import Batch, inspect, find
P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
SC = '/Script/Engine.SceneComponent:'
SK = '/Script/Engine.SkinnedMeshComponent:'
K = '/Script/Engine.KismetMathLibrary:'
inventory = json.load(open('P:/FoA/Saved/AnimShots/teen_runtime_inventory.json'))

def replace(name):
    nodes, _ = inspect(P, name)
    entry = find(nodes, name)
    b = Batch(P, name)
    ids = [n['node_id'] for n in nodes if n['node_id'] != entry]
    if ids:
        b.ops.append(dict(op='remove', node_ids=ids))
    return b, entry

def eyes():
    b,e = replace('UpdateSleepEyes')
    b.get('face','Face',0,250); b.get('closed','SleepEyeClosure',0,450)
    last=e
    for i, eye in enumerate(('eyeBlinkLeft','eyeBlinkRight')):
        n='eye'+str(i)
        b.fn(n,'/Script/Engine.SkeletalMeshComponent:SetMorphTarget',300+i*350,0,MorphTargetName=eye)
        b.link('face','Face',n,'self'); b.link('closed','SleepEyeClosure',n,'Value')
        b.chain(last,n);last=n
    b.comment('Close sleeping eyelids',['face','closed','eye0','eye1']);b.run()

def coverage():
    b,e = replace('RefreshStarterCoverage')
    b.get('body','Body',0,250); b.get('suit','Suit',0,450); b.get('boots','BootsWornMesh',0,650)
    b.fn('suited',SC+'IsVisible',250,450);b.link('suit','Suit','suited','self')
    b.fn('shod',SC+'IsVisible',250,650);b.link('boots','BootsWornMesh','shod','self')
    b.fn('unsuited',K+'Not_PreBool',500,450);b.link('suited','ReturnValue','unsuited','A')
    last=e
    for i,(base,equipped) in enumerate((('StartOutfit','Shirt'),('StartPants','Trousers'),('StartSocks','Socks'))):
        x=800+i*900
        b.get(base,base,x,300);b.get(equipped,equipped,x,600)
        b.fn(base+'worn',SC+'IsVisible',x+200,600);b.link(equipped,equipped,base+'worn','self')
        b.fn(base+'free',K+'Not_PreBool',x+400,600);b.link(base+'worn','ReturnValue',base+'free','A')
        b.fn(base+'show',K+'BooleanAND',x+600,600);b.link(base+'free','ReturnValue',base+'show','A');b.link('unsuited','ReturnValue',base+'show','B')
        b.fn(base+'leader',SK+'SetLeaderPoseComponent',x,0,bForceUpdate='true')
        b.link(base,base,base+'leader','self');b.link('body','Body',base+'leader','NewLeaderBoneComponent')
        b.fn(base+'vis',SC+'SetVisibility',x+400,0);b.link(base,base,base+'vis','self');b.link(base+'show','ReturnValue',base+'vis','bNewVisibility')
        b.chain(last,base+'leader',base+'vis');last=base+'vis'
    # Baseline layers remain present until their matching equipped layer replaces them.
    baseline=('foa_polo_layered','toigo_wool_pants','joepal_crude_low_socks')
    pieces={'Body':'Body','StartOutfit':'Polo','StartPants':'Pants','StartSocks':'Socks','Shirt':'Polo','Trousers':'Pants','Socks':'Socks','Suit':'Suit','BootsWornMesh':'Shoes'}
    slot_x=4400
    for comp,part in pieces.items():
        ref='mask'+comp;b.get(ref,comp,slot_x-250,350)
        for i,slot in enumerate(inventory['meshes'][part]['slots']):
            if 'under_' not in slot:
                continue
            tail=slot.split('under_',1)[1]
            n=comp+str(i)
            b.fn(n,SK+'ShowMaterialSection',slot_x,0,MaterialID=i,SectionIndex=-1,LODIndex=0,bShow='true')
            slot_x+=300
            b.link(ref,comp,n,'self')
            if any(g in tail for g in baseline):
                b.pin(n,'bShow','false')
            elif 'male_elegantsuit01' in tail:
                b.link('unsuited','ReturnValue',n,'bShow')
            elif 'shoes03' in tail:
                b.fn(n+'bare',K+'Not_PreBool',slot_x-450,650);b.link('shod','ReturnValue',n+'bare','A');b.link(n+'bare','ReturnValue',n,'bShow')
            b.chain(last,n);last=n
    b.comment('Replace starter layers',[o['ref'] for o in b.ops if 'ref' in o]);b.run()

def finish():
    # SetSuitedBody retains its existing visibility behavior but must never restore a MetaHuman mesh.
    nodes,_=inspect(P,'SetSuitedBody');b=Batch(P,'SetSuitedBody')
    for n in nodes:
        if any(p['name']=='NewMesh' for p in n['pins']):
            b.pin(n['node_id'],'NewMesh',inventory['meshes']['Body']['path'])
    b.run()
    # Old slipper material IDs belonged to the combined MH pajama mesh, not the new polo.
    nodes,edges=inspect(P,'SetBootsWorn');b=Batch(P,'SetBootsWorn')
    old=[n['node_id'] for n in nodes if n['title'].replace(' ','')=='ShowMaterialSection']
    if old:
        incoming=next(e for e in edges if e['to_node'] in old and e['to_pin']=='execute' and e['from_node'] not in old)
        outgoing=next(e for e in edges if e['from_node'] in old and e['from_pin']=='then' and e['to_node'] not in old)
        b.ops.append(dict(op='remove',node_ids=old))
        b.link(incoming['from_node'],incoming['from_pin'],outgoing['to_node'],outgoing['to_pin'])
    b.run()
    nodes,edges=inspect(P,'SetBootsWorn')
    if not any(n['title']=='RefreshStarterCoverage' for n in nodes):
        boots=find(nodes,'Get BootsWornMesh')
        vis_ids={n['node_id'] for n in nodes if n['title'].replace(' ','')=='SetVisibility'}
        visible=next(e['to_node'] for e in edges if e['from_node']==boots and e['to_node'] in vis_ids)
        after=next(e for e in edges if e['from_node']==visible and e['from_pin']=='then')
        b=Batch(P,'SetBootsWorn');b.cut(visible,'then',after['to_node'],after['to_pin'])
        b.fn('coverage',P+'.BP_FoAPlayer_C:RefreshStarterCoverage',820,0)
        b.chain(visible,'coverage');b.link('coverage','then',after['to_node'],after['to_pin']);b.run()
    # Construction initializes the starter leaders for both gameplay and Sequencer-spawned players.
    nodes,edges=inspect(P,'UserConstructionScript')
    if not any(n['title']=='RefreshStarterCoverage' for n in nodes):
        tails=[n for n in nodes if any(p['name']=='then' for p in n['pins']) and not any(e['from_node']==n['node_id'] and e['from_pin']=='then' for e in edges)]
        assert len(tails)==1, tails
        b=Batch(P,'UserConstructionScript');b.fn('coverage',P+'.BP_FoAPlayer_C:RefreshStarterCoverage',5000,0)
        b.chain(tails[0]['node_id'],'coverage');b.run()

def face_mask():
    sys.path.insert(0,'P:/FoA/Tools/Unreal/wakeup')
    import wake_math as m
    raw=inventory['head_transform']
    def values(group):
        return tuple(float(v) for v in re.findall(r'[XYZW]=([^,)]+)',re.search(group+r'=\(([^)]+)\)',raw).group(1)))
    q=m.qinv(values('Rotation'));t=values('Translation');scale=values('Scale3D')[0]
    center=m.mul(m.qrot(q,m.sub((0,16.6,175.5),t)),1/scale)
    front=m.qrot(q,(0,1,0));right=m.qrot(q,(-1,0,0))
    vec=lambda v:','.join(str(x) for x in v)
    b,e=replace('UpdateFaceMaskPose')
    b.get('face','Face',0,300)
    b.fn('head',SC+'GetSocketTransform',250,300,InSocketName='head',TransformSpace='RTS_World')
    b.link('face','Face','head','self')
    for name,local,fn,y in [('center',vec(center),'TransformLocation',300),
                           ('front',vec(front),'TransformDirection',600),
                           ('right',vec(right),'TransformDirection',900)]:
        b.fn(name,K+fn,600,y,Location=local) if fn=='TransformLocation' else b.fn(name,K+fn,600,y,Direction=local)
        b.link('head','ReturnValue',name,'T')
    last=e
    for i,(source,param,alpha) in enumerate((('center','FaceOrigin',8*.9444444444),('front','FaceForward',3.2),('right','FaceRight',7.5*.9444444444))):
        b.fn(source+'xyz',K+'BreakVector',900,300+i*300);b.link(source,'ReturnValue',source+'xyz','InVec')
        b.fn(source+'color',K+'MakeColor',1150,300+i*300,A=alpha)
        for a,c in zip(('X','Y','Z'),('R','G','B')):b.link(source+'xyz',a,source+'color',c)
        b.fn(source+'mpc','/Script/Engine.KismetMaterialLibrary:SetVectorParameterValue',1500+i*350,0,
             Collection='/Game/FoA/PostProcess/MPC_Dream.MPC_Dream',ParameterName=param)
        b.link(source+'color','ReturnValue',source+'mpc','ParameterValue');b.chain(last,source+'mpc');last=source+'mpc'
    b.comment('Follow teen face',[o['ref'] for o in b.ops if 'ref' in o]);b.run()

def sand():
    nodes,edges=inspect(P,'SetSandOverlay')
    if any(n['title']=='Get StartPants' for n in nodes):return
    starter=find(nodes,'Get StartOutfit')
    apply=next(e['to_node'] for e in edges if e['from_node']==starter and e['to_pin']=='self')
    after=next((e for e in edges if e['from_node']==apply and e['from_pin']=='then'),None)
    mid=next(e for e in edges if e['to_node']==apply and e['to_pin']=='NewOverlayMaterial')
    b=Batch(P,'SetSandOverlay')
    if after:b.cut(apply,'then',after['to_node'],after['to_pin'])
    last=apply
    for i,name in enumerate(('StartPants','StartSocks')):
        b.get(name,name,5500+i*400,350)
        b.fn(name+'sand','/Script/Engine.MeshComponent:SetOverlayMaterial',5500+i*400,0)
        b.link(name,name,name+'sand','self');b.link(mid['from_node'],mid['from_pin'],name+'sand','NewOverlayMaterial')
        b.chain(last,name+'sand');last=name+'sand'
    if after:b.link(last,'then',after['to_node'],after['to_pin'])
    b.comment('Sand covers starter layers',['StartPants','StartPantssand','StartSocks','StartSockssand']);b.run()

{'eyes':eyes,'coverage':coverage,'finish':finish,'face_mask':face_mask,'sand':sand}[sys.argv[1]]()
