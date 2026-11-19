"""True masked base-material dissolve, with exact slot restoration. Declare/compile, then body/compile.
The director owns timing and hides the actor only after coverage has reached zero. No Tick or new assets.
"""
import os
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())

PATH='/Game/FoA/Characters/Player/BP_FoAPlayer'
SELF=PATH+'.BP_FoAPlayer_C'
PARTS=('Body','Face','StartOutfit','Shirt','Trousers','Socks','Tie','Suit','BootsWornMesh')
KML='/Script/Engine.KismetMathLibrary'
KAL='/Script/Engine.KismetArrayLibrary'
MESH='/Script/Engine.MeshComponent'
PRIM='/Script/Engine.PrimitiveComponent'
MI='/Script/Engine.MaterialInstanceDynamic'
ARRAY=lambda t:BEL.get_array_type(ptype(t))
SIGS={'SetSandTransition':[('Amount',ptype('real')),('Enable',ptype('bool'))],
      'CaptureSandPart':[('PartIndex',ptype('int')),('SlotIndex',ptype('int'))],
      'ApplySandPart':[('Index',ptype('int')),('Restore',ptype('bool'))]}


def fn(name):
    g=Graph.function(PATH,name,inputs=SIGS[name]);return g,g.at(entry_node(g),0,0)


def get_at(g,array,index,x,y):
    a=g.get(array,x,y)
    n=g.call(KAL+':Array_Get',x+256,y)
    g.link(a,array,n,'TargetArray');g.link(index[0],index[1],n,'Index')
    return n


if os.environ.get('FOA_PHASE')=='declare':
    ensure_vars(PATH,[('bSandTransition',ptype('bool'),'false','Sand|Transition',False),
        ('SandTransitionMID',ptype(unreal.MaterialInstanceDynamic),'','Sand|Transition',False),
        ('SandParts',ARRAY(unreal.MeshComponent),'','Sand|Transition',False),
        ('SandOriginalMeshes',ARRAY(unreal.MeshComponent),'','Sand|Transition',False),
        ('SandOriginalSlots',ARRAY('int'),'','Sand|Transition',False),
        ('SandOriginalMaterials',ARRAY(unreal.MaterialInterface),'','Sand|Transition',False),
        ('SandHairVisible',ptype('bool'),'true','Sand|Transition',False),
        ('SandBrowsVisible',ptype('bool'),'true','Sand|Transition',False)])
    for name in SIGS:fn(name)
else:
    g,e=fn('CaptureSandPart')
    parts=g.get('SandParts',0,224);length=g.call(KAL+':Array_Length',256,224)
    more=g.call(KML+':Less_IntInt',512,224);part_ok=g.branch(768,0)
    g.link(parts,'SandParts',length,'TargetArray');g.link(e,'PartIndex',more,'A');g.link(length,'ReturnValue',more,'B')
    g.link(more,'ReturnValue',part_ok,'Condition');g.exec_chain(e,part_ok)
    component=get_at(g,'SandParts',(e,'PartIndex'),768,448)
    count=g.call(PRIM+':GetNumMaterials',1280,448)
    slot_more=g.call(KML+':Less_IntInt',1536,448);slot_ok=g.branch(1792,0)
    g.link(component,'Item',count,'self');g.link(e,'SlotIndex',slot_more,'A');g.link(count,'ReturnValue',slot_more,'B')
    g.link(slot_more,'ReturnValue',slot_ok,'Condition');g.link(part_ok,'True',slot_ok,'execute')
    mat=g.call(PRIM+':GetMaterial',1792,672);g.link(component,'Item',mat,'self');g.link(e,'SlotIndex',mat,'ElementIndex')
    tail=None
    for i,(array,source,pin) in enumerate((('SandOriginalMeshes',component,'Item'),('SandOriginalSlots',e,'SlotIndex'),
                                         ('SandOriginalMaterials',mat,'ReturnValue'))):
        a=g.get(array,2048+i*320,224);add=g.call(KAL+':Array_Add',2048+i*320,0)
        g.link(a,array,add,'TargetArray');g.link(source,pin,add,'NewItem')
        if tail:g.exec_chain(tail,add)
        else:g.link(slot_ok,'True',add,'execute')
        tail=add
    slot_next=g.call(KML+':Add_IntInt',2688,448,B=1);same=g.call(SELF+':CaptureSandPart',3008,0)
    g.link(e,'SlotIndex',slot_next,'A');g.link(e,'PartIndex',same,'PartIndex');g.link(slot_next,'ReturnValue',same,'SlotIndex')
    g.exec_chain(tail,same)
    part_next=g.call(KML+':Add_IntInt',2048,1024,B=1);next_part=g.call(SELF+':CaptureSandPart',2368,832,SlotIndex=0)
    g.link(e,'PartIndex',part_next,'A');g.link(part_next,'ReturnValue',next_part,'PartIndex');g.link(slot_ok,'False',next_part,'execute')
    g.comment('Remember every material slot','',g.ed.list_all_nodes(),C_DATA)

    g,e=fn('ApplySandPart')
    meshes=g.get('SandOriginalMeshes',0,224);length=g.call(KAL+':Array_Length',256,224)
    more=g.call(KML+':Less_IntInt',512,224);exists=g.branch(768,0)
    g.link(meshes,'SandOriginalMeshes',length,'TargetArray');g.link(e,'Index',more,'A');g.link(length,'ReturnValue',more,'B')
    g.link(more,'ReturnValue',exists,'Condition');g.exec_chain(e,exists)
    component=get_at(g,'SandOriginalMeshes',(e,'Index'),768,448)
    slot=get_at(g,'SandOriginalSlots',(e,'Index'),1280,448)
    original=get_at(g,'SandOriginalMaterials',(e,'Index'),1792,448)
    restore=g.branch(1280,0);g.link(e,'Restore',restore,'Condition');g.link(exists,'True',restore,'execute')
    old=g.call(PRIM+':SetMaterial',2304,-128);sand=g.call(PRIM+':SetMaterial',2304,128)
    mid=g.get('SandTransitionMID',2048,832);clear_overlay=g.call(MESH+':SetOverlayMaterial',2624,128)
    for node in (old,sand):g.link(component,'Item',node,'self');g.link(slot,'Item',node,'ElementIndex')
    g.link(original,'Item',old,'Material');g.link(mid,'SandTransitionMID',sand,'Material')
    g.link(component,'Item',clear_overlay,'self');g.link(restore,'True',old,'execute');g.link(restore,'False',sand,'execute')
    g.exec_chain(sand,clear_overlay)
    plus=g.call(KML+':Add_IntInt',2880,448,B=1);again=g.call(SELF+':ApplySandPart',3136,0)
    g.link(e,'Index',plus,'A');g.link(plus,'ReturnValue',again,'Index');g.link(e,'Restore',again,'Restore')
    g.exec_chain(old,again);g.exec_chain(clear_overlay,again)
    g.comment('Swap or restore exact slots','',g.ed.list_all_nodes(),C_VISUAL)

    g,e=fn('SetSandTransition')
    enable=g.branch(256,0);g.link(e,'Enable',enable,'Condition');g.exec_chain(e,enable)
    active=g.get('bSandTransition',256,224);already=g.branch(544,-160)
    g.link(active,'bSandTransition',already,'Condition');g.link(enable,'True',already,'execute')
    tail=already;first=None;clears=[]
    for i,array in enumerate(('SandOriginalMeshes','SandOriginalSlots','SandOriginalMaterials')):
        a=g.get(array,800+i*320,224);clear=g.call(KAL+':Array_Clear',800+i*320,-160)
        g.link(a,array,clear,'TargetArray')
        if first is None:first=clear;g.link(already,'False',clear,'execute')
        else:g.exec_chain(tail,clear)
        tail=clear;clears += [a,clear]
    parts=g.set('SandParts',1760,-160);array=g.node('Utilities|Array|MakeArray',1504,448)
    for _ in PARTS[1:]:g.ed.add_node_pin(array)
    g.link(array,'Array',parts,'SandParts')
    for i,name in enumerate(PARTS):
        p=g.get(name,1120+i*224,768);g.link(p,name,array,'['+str(i)+']')
    make=g.call('/Script/Engine.KismetMaterialLibrary:CreateDynamicMaterialInstance',2080,-160,
                Parent='/Game/FoA/VFX/Sand/M_SandOverlay.M_SandOverlay')
    remember=g.set('SandTransitionMID',2464,-160);on=g.set('bSandTransition',2784,-160)
    g.default(on,'bSandTransition',True)
    capture=g.call(SELF+':CaptureSandPart',3104,-160,PartIndex=0,SlotIndex=0)
    apply=g.call(SELF+':ApplySandPart',3424,-160,Index=0,Restore=False)
    g.exec_chain(tail,parts,make,remember,on,capture,apply);g.link(make,'ReturnValue',remember,'SandTransitionMID')
    tail=apply
    for i,(part,var) in enumerate((('Hair','SandHairVisible'),('Eyebrows','SandBrowsVisible'))):
        p=g.get(part,3744+i*960,224);visible=g.call('/Script/Engine.SceneComponent:IsVisible',3744+i*960,448)
        cache=g.set(var,4064+i*960,-160)
        g.link(p,part,visible,'self');g.link(visible,'ReturnValue',cache,var);g.exec_chain(tail,cache);tail=cache
    mid=g.get('SandTransitionMID',5664,224)
    stable=g.call(MI+':SetScalarParameterValue',5984,-160,ParameterName='Transition',Value=1.)
    amount=g.call(MI+':SetScalarParameterValue',6304,-160,ParameterName='Amount')
    g.link(mid,'SandTransitionMID',stable,'self');g.link(mid,'SandTransitionMID',amount,'self')
    g.link(e,'Amount',amount,'Value');g.exec_chain(tail,stable,amount);g.link(already,'True',stable,'execute')
    # Groom shaders cannot use the skeletal masked sand material. Keep the real curl silhouette through most
    # of erosion, hide it only below25% coverage and reveal above70% during re-form under pooled bursts.
    tail=amount
    for i,(part,var) in enumerate((('Hair','SandHairVisible'),('Eyebrows','SandBrowsVisible'))):
        x=6624+i*1280
        p=g.get(part,x,224);original=g.get(var,x,448)
        current=g.call('/Script/Engine.SceneComponent:IsVisible',x+256,224)
        high=g.call(KML+':Greater_DoubleDouble',x,672,B=.7);low=g.call(KML+':Less_DoubleDouble',x,864,B=.25)
        keep_high=g.call(KML+':BooleanAND',x+384,448)
        not_high=g.call(KML+':Not_PreBool',x+256,1088)
        keep_current=g.call(KML+':BooleanAND',x+512,864)
        choose=g.call(KML+':BooleanOR',x+768,448)
        not_low=g.call(KML+':Not_PreBool',x+512,1088)
        hide=g.call(KML+':BooleanAND',x+1024,448)
        show=g.call('/Script/Engine.SceneComponent:SetVisibility',x+1024,-160)
        g.link(p,part,current,'self');g.link(e,'Amount',high,'A');g.link(e,'Amount',low,'A')
        g.link(original,var,keep_high,'A');g.link(high,'ReturnValue',keep_high,'B')
        g.link(high,'ReturnValue',not_high,'A');g.link(current,'ReturnValue',keep_current,'A')
        g.link(not_high,'ReturnValue',keep_current,'B');g.link(keep_high,'ReturnValue',choose,'A')
        g.link(keep_current,'ReturnValue',choose,'B');g.link(low,'ReturnValue',not_low,'A')
        g.link(choose,'ReturnValue',hide,'A');g.link(not_low,'ReturnValue',hide,'B')
        g.link(p,part,show,'self');g.link(hide,'ReturnValue',show,'bNewVisibility');g.exec_chain(tail,show);tail=show
    g.comment('Begin a real grain dissolve','',[e,enable,active,already]+clears+[parts,array,make,remember,on,capture,apply,mid,stable,amount],C_VISUAL)
    restore_ok=g.branch(544,1280);g.link(active,'bSandTransition',restore_ok,'Condition');g.link(enable,'False',restore_ok,'execute')
    restore=g.call(SELF+':ApplySandPart',864,1280,Index=0,Restore=True);off=g.set('bSandTransition',1184,1280)
    g.link(restore_ok,'True',restore,'execute');g.exec_chain(restore,off);tail=off
    for i,(part,var) in enumerate((('Hair','SandHairVisible'),('Eyebrows','SandBrowsVisible'))):
        p=g.get(part,1504+i*640,1504);cached=g.get(var,1504+i*640,1728)
        show=g.call('/Script/Engine.SceneComponent:SetVisibility',1824+i*640,1280)
        g.link(p,part,show,'self');g.link(cached,var,show,'bNewVisibility');g.exec_chain(tail,show);tail=show
    reset=g.call(MI+':SetScalarParameterValue',3104,1280,ParameterName='Transition',Value=0.)
    g.link(mid,'SandTransitionMID',reset,'self');g.exec_chain(tail,reset);tail=reset
    for i,array in enumerate(('SandOriginalMeshes','SandOriginalSlots','SandOriginalMaterials','SandParts')):
        a=g.get(array,3424+i*320,1504);clear=g.call(KAL+':Array_Clear',3424+i*320,1280)
        g.link(a,array,clear,'TargetArray');g.exec_chain(tail,clear);tail=clear
    idle=g.call(SELF+':SetSandOverlay',4800,1280,Amount=.06);g.exec_chain(tail,idle)
    g.comment('Restore the visible character','',[restore_ok,restore,off,reset,idle],C_VISUAL)
unreal.EditorAssetLibrary.save_loaded_asset(unreal.load_asset(PATH),False)
print('Sand transition',os.environ.get('FOA_PHASE'),'saved; C++ compile required in same lease')
