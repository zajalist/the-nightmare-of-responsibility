"""Read-only diagnostic widget and frontend lifecycle. Editor script; native compile queued."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
D='/Game/FoA/UI/Game/WBP_Debug';F='/Game/FoA/UI/Framework/BP_FoAFrontEnd'
DIRECTOR='/Game/FoA/Gameplay/BP_BeatDirector';PLAYER='/Game/FoA/Characters/Player/BP_FoAPlayer'
INTER='/Game/FoA/Gameplay/BPC_Interactor';BAG='/Game/FoA/Gameplay/BPC_Inventory';ENCOUNTER='/Game/FoA/Gameplay/Encounter/BP_Encounter'
K='/Script/Engine.KismetSystemLibrary:';M='/Script/Engine.KismetMathLibrary:';S='/Script/Engine.KismetStringLibrary:';GS='/Script/Engine.GameplayStatics:'
UW='/Script/UMG.UserWidget:';TX='/Script/Engine.KismetTextLibrary:'
C=lambda p:p+'.'+p.rsplit('/',1)[1]+'_C'

def fn(path,name):
    g=Graph.function(path,name);return g,entry_node(g)
def read(g,obj,pin,var,cls,x,y):
    n=g.get(var,x,y,C(cls));g.link(obj,pin,n,'self');return n,var

def join(g,parts,x=700,y=300):
    # Parts are literals or (node,pin,conversion-kind) values.
    last=None
    for i,part in enumerate(parts):
        xx=x+i*300
        if isinstance(part,str):
            n=g.call(K+'MakeLiteralString',xx,y,Value=part);value=(n,'ReturnValue')
        else:
            node,pin,kind=part
            if kind=='string':value=(node,pin)
            else:
                conv={'int':(S+'Conv_IntToString','InInt'),'bool':(S+'Conv_BoolToString','InBool'),'name':(S+'Conv_NameToString','InName'),'text':(TX+'Conv_TextToString','InText'),'object':(K+'GetDisplayName','Object'),'vector':(S+'Conv_VectorToString','InVec')}[kind]
                n=g.call(conv[0],xx,y);g.link(node,pin,n,conv[1]);value=(n,'ReturnValue')
        if last:
            n=g.call(S+'Concat_StrStr',xx,y+180);g.link(*last,n,'A');g.link(*value,n,'B');last=(n,'ReturnValue')
        else:last=value
    return last

def text(g,e,name,parts,y=900):
    value=join(g,parts,y=y);end=1000+len(parts)*300
    target=g.get(name,end,300);cv=g.call(TX+'Conv_StringToText',end,y+180);g.link(*value,cv,'InString')
    out=g.call('/Script/UMG.TextBlock:SetText',end+350,0);g.link(target,name,out,'self');g.link(cv,'ReturnValue',out,'InText');g.exec_chain(e,out)

def actor(g,path,x=0,y=300):
    n=g.call(GS+'GetActorOfClass',x,y,ActorClass=C(path));return n,'ReturnValue'
def valid(g,e,ref):
    n=g.call(K+'IsValid',300,160);g.link(*ref,n,'Object');b=g.branch(600,0);g.link(n,'ReturnValue',b,'Condition');g.exec_chain(e,*([ref[0]] if any(str(PIN.get_pin_name(p))=='execute' for p in BEL.list_all_pins(ref[0])) else []),b);return b

def category(name,path,widget,fields):
    g,e=fn(D,name);ref=actor(g,path);b=valid(g,e,ref);parts=[]
    for i,(label,var,kind) in enumerate(fields):parts.extend([label,(*read(g,*ref,var,path,700+i*280,500),kind)])
    text(g,b,widget,parts)
    g.comment('Read current state','',g.ed.list_all_nodes())

# Existing widget identity and tree are created by the native UI setup first.
for name in ('RefreshDebug','RefreshStory','RefreshInteraction','RefreshCamera','RefreshLocks','RefreshInventory','RefreshBattle'):
    Graph.function(D,name)
category('RefreshStory',DIRECTOR,'Txt_Story',[('Story beat  ', 'BeatIndex','int'),('    Search  ','ClothingSearchStage','int')])
category('RefreshBattle',ENCOUNTER,'Txt_Battle',[('Battle active  ','bActive','bool'),('    Player turn  ','bPlayerTurn','bool')])
category('RefreshLocks',PLAYER,'Txt_Locks',[('Cinematic  ','bCinematic','bool'),('    Interaction lock  ','bInteractionLocked','bool')])
# Camera and controller input flags.
g,e=fn(D,'RefreshCamera');pc=g.call(GS+'GetPlayerController',0,300);view=g.call('/Script/Engine.PlayerController:GetViewTarget',250,300);g.link(pc,'ReturnValue',view,'self')
cm=g.call(GS+'GetPlayerCameraManager',0,500);loc=g.call('/Script/Engine.PlayerCameraManager:GetCameraLocation',250,500);g.link(cm,'ReturnValue',loc,'self')
mv=g.call('/Script/Engine.Controller:IsMoveInputIgnored',250,700);lk=g.call('/Script/Engine.Controller:IsLookInputIgnored',250,900)
for n in (mv,lk):g.link(pc,'ReturnValue',n,'self')
text(g,e,'Txt_Camera',['View  ',(view,'ReturnValue','object'),'\nCamera  ',(loc,'ReturnValue','vector'),'\nMove ignored  ',(mv,'ReturnValue','bool'),'    Look ignored  ',(lk,'ReturnValue','bool')]);g.comment('Observe camera ownership','',g.ed.list_all_nodes())

def interactor(g,e):
    p=g.call(GS+'GetPlayerCharacter',0,350);c=g.call('/Script/Engine.Actor:GetComponentByClass',300,350,ComponentClass=C(INTER));g.link(p,'ReturnValue',c,'self')
    return (c,'ReturnValue'),valid(g,e,(c,'ReturnValue'))
g,e=fn(D,'RefreshInteraction');ref,b=interactor(g,e)
text(g,b,'Txt_Interaction',['Target  ',(*read(g,*ref,'Target',INTER,700,500),'object'),'\nAction  ',(*read(g,*ref,'Prompt',INTER,1000,500),'text')]);g.comment('Read interaction focus','',g.ed.list_all_nodes())
# Inventory array is read in its actual order; no fixed-capacity assumptions.
ensure_vars(D,[('InventoryReadout',ptype('string'),'','Debug',False)])
g,e=fn(D,'RefreshInventory');ref,b=interactor(g,e);bag=read(g,*ref,'Inventory',INTER,650,450);items=read(g,*bag,'Items',BAG,950,450)
clear=g.set('InventoryReadout',900,0);g.default(clear,'InventoryReadout','Inventory  ');g.exec_chain(b,clear)
loops=[n for n in g.ed.list_available_nodes([]) if n.rsplit('|',1)[-1].replace(' ','')=='ForEachLoop'];assert loops, 'ForEachLoop missing'
loop=g.node(loops[0],1200,0);g.link(*items,loop,'Array');g.link(clear,'then',loop,'Exec')
current=g.get('InventoryReadout',1250,500);nm=g.call(S+'Conv_NameToString',1500,600);g.link(loop,'Array Element',nm,'InName')
a=g.call(S+'Concat_StrStr',1750,500);g.link(current,'InventoryReadout',a,'A');g.link(nm,'ReturnValue',a,'B')
c=g.call(S+'Concat_StrStr',2000,500,B='  ');g.link(a,'ReturnValue',c,'A');store=g.set('InventoryReadout',2250,0);g.link(c,'ReturnValue',store,'InventoryReadout');g.link(loop,'Loop Body',store,'execute')
# A separate custom event-like callable chain after loop completion.
sel=read(g,*bag,'Selected',BAG,1500,850);held=g.call(C(BAG)+':GetHeld',1800,850);g.link(*bag,held,'self')
value=join(g,[(current,'InventoryReadout','string'),'\nSelected slot  ',(*sel,'int'),'    Held  ',(held,'Item','name')],x=2600,y=1400)
target=g.get('Txt_Inventory',3000,250);cv=g.call(TX+'Conv_StringToText',3400,250);g.link(*value,cv,'InString');out=g.call('/Script/UMG.TextBlock:SetText',3800,0);g.link(target,'Txt_Inventory',out,'self');g.link(cv,'ReturnValue',out,'InText');g.link(loop,'Completed',out,'execute');g.comment('Read physical inventory','',g.ed.list_all_nodes())
# Refresh only an onscreen widget. No gameplay writes, focus, pause or input mode changes.
g,e=fn(D,'RefreshDebug');v=g.call('/Script/UMG.Widget:IsVisible',0,160);b=g.branch(250,0);g.link(v,'ReturnValue',b,'Condition');g.exec_chain(e,b);last=b
for i,name in enumerate(('RefreshStory','RefreshInteraction','RefreshCamera','RefreshLocks','RefreshInventory','RefreshBattle')):
    n=g.call(C(D)+':'+name,500+i*280,0);g.exec_chain(last,n);last=n
g.comment('Refresh visible diagnostics','',g.ed.list_all_nodes())
g=Graph(D).clear();e=g.event('Construct',0,0);r=g.call(C(D)+':RefreshDebug',250,0);t=g.call(K+'K2_SetTimer',550,0,FunctionName='RefreshDebug',Time=.25,bLooping=True);g.exec_chain(e,r,t)
x=g.event('Destruct',0,500);stop=g.call(K+'K2_ClearTimer',300,500,FunctionName='RefreshDebug');g.exec_chain(x,stop);g.comment('Visible refresh lifetime','',g.ed.list_all_nodes())
compile_save(D)
exec(open('P:/FoA/Tools/Unreal/ui/install_debug_frontend.py').read())
# Remove F9 only. F10 development failure shortcut is outside this requested change.
g=Graph(DIRECTOR)
for n in list(g.ed.list_all_nodes()):
    if n.get_class().get_name()=='K2Node_InputKey' and str(BEL.get_node_title(n))=='F9':g.ed.remove_nodes([n])
compile_save(DIRECTOR);compile_save(F)


