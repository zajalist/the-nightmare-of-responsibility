"""Layer real modular clothes over the starter outfit without duplicate cloth. Declare/compile then body/compile.
Footwear materials2/3 belong to SetBootsWorn; this helper owns only shirt0 and trousers1 at the pinned LOD0.
"""
import os
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
PATH='/Game/FoA/Characters/Player/BP_FoAPlayer'
SELF=PATH+'.BP_FoAPlayer_C'
g=Graph.function(PATH,'RefreshStarterCoverage')
if os.environ.get('FOA_PHASE')!='declare':
    e=g.at(entry_node(g),0,0);starter=g.get('StartOutfit',32,224);tail=e
    for i,(part,section) in enumerate((('Shirt',0),('Trousers',1))):
        x=320+i*1280
        comp=g.get(part,x,224)
        visible=g.call('/Script/Engine.SceneComponent:IsVisible',x+256,224)
        count=g.call('/Script/Engine.PrimitiveComponent:GetNumMaterials',x+256,448)
        real=g.call('/Script/Engine.KismetMathLibrary:Greater_IntInt',x+512,448,B=0)
        worn=g.call('/Script/Engine.KismetMathLibrary:BooleanAND',x+768,224)
        uncovered=g.call('/Script/Engine.KismetMathLibrary:Not_PreBool',x+1024,224)
        show=g.call('/Script/Engine.SkinnedMeshComponent:ShowMaterialSection',x+1280,0,
                    MaterialID=section,SectionIndex=-1,LODIndex=0)
        g.link(comp,part,visible,'self');g.link(comp,part,count,'self');g.link(count,'ReturnValue',real,'A')
        g.link(visible,'ReturnValue',worn,'A');g.link(real,'ReturnValue',worn,'B');g.link(worn,'ReturnValue',uncovered,'A')
        g.link(starter,'StartOutfit',show,'self');g.link(uncovered,'ReturnValue',show,'bShow');g.exec_chain(tail,show);tail=show
    g.comment('Only cover replaced clothing','',g.ed.list_all_nodes(),C_VISUAL)
    for name in ('Equip','UnequipAll'):
        g=Graph(PATH,name)
        if any(str(BEL.get_node_title(n)).replace(' ','')=='RefreshStarterCoverage' for n in g.ed.list_all_nodes()):continue
        if name=='Equip':
            candidates=[n for n in g.ed.list_all_nodes() if str(BEL.get_node_title(n)).replace(' ','')=='SetVisibility']
        else:
            candidates=[n for n in g.ed.list_nodes_of_class(unreal.K2Node_CallFunction)
                        if PIN.is_valid(BEL.find_then_pin(n)) and not PIN.list_connected_pins(BEL.find_then_pin(n))]
        assert len(candidates)==1,(name,[str(BEL.get_node_title(n)) for n in candidates])
        tail=candidates[0];pos=BEL.get_node_pos(tail);old=list(PIN.list_connected_pins(BEL.find_then_pin(tail)))
        refresh=g.call(SELF+':RefreshStarterCoverage',pos.x+320,pos.y-192)
        PIN.break_pin_links(BEL.find_then_pin(tail));g.exec_chain(tail,refresh)
        for pin in old:assert PIN.try_create_connection(BEL.find_then_pin(refresh),pin)
        g.comment('Keep starter coverage correct','',[refresh],C_VISUAL)
unreal.EditorAssetLibrary.save_loaded_asset(unreal.load_asset(PATH),False)
print('Starter coverage',os.environ.get('FOA_PHASE'),'saved; compile in same asset lease')
