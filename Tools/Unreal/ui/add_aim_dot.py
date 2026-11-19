"""Small camera-centred interaction marker. Run only in a stopped-PIE HUD lease.

Native tree calls add the two widgets in place; `graph` runs through editor Python.
The HUD's existing opacity/visibility still owns phone and story transitions.
"""
import sys

HUD='/Game/FoA/UI/Game/WBP_HUD'
SIZE=6.0
TREE={'class':'SizeBox','name':'Size_AimDot',
      'properties':{'WidthOverride':SIZE,'HeightOverride':SIZE,
                    'bOverride_WidthOverride':True,'bOverride_HeightOverride':True,
                    'Visibility':'HitTestInvisible','RenderOpacity':0.0},
      'slot_props':{'horizontal_alignment':'Center','vertical_alignment':'Center','padding':[0,0,0,0]},
      'children':[{'class':'Image','name':'Img_AimDot','properties':{
          'Visibility':'HitTestInvisible',
          'Brush':'(ImageSize=(X=6,Y=6),DrawAs=RoundedBox,TintColor=(SpecifiedColor=(R=1,G=1,B=1,A=1)),OutlineSettings=(RoundingType=HalfHeightRadius,Width=1,Color=(SpecifiedColor=(R=0,G=0,B=0,A=0.9))))'}}]}


def graph():
    import unreal
    sys.path.insert(0,'P:/FoA/Tools/Unreal/ui')
    from bp_graph import Graph,entry_node,BEL,PIN,C_VISUAL
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
    g=Graph.function(HUD,'RefreshAimDot');e=entry_node(g)
    dot=g.get('Size_AimDot',0,800)
    pc=g.call('/Script/UMG.UserWidget:GetOwningPlayer',0,200)
    pawn=g.call('/Script/UMG.UserWidget:GetOwningPlayerPawn',0,400)
    valid=[]
    for i,n in enumerate((pc,pawn)):
        v=g.call('/Script/Engine.KismetSystemLibrary:IsValid',280,200+i*200)
        g.link(n,'ReturnValue',v,'Object');valid.append(v)
    both=g.call('/Script/Engine.KismetMathLibrary:BooleanAND',560,200)
    g.link(valid[0],'ReturnValue',both,'A');g.link(valid[1],'ReturnValue',both,'B')
    guard=g.branch(800,0);g.exec_chain(e,guard);g.link(both,'ReturnValue',guard,'Condition')
    casts=[name for name in g.ed.list_available_nodes([]) if name.endswith('CastToBP_FoAPlayer')]
    assert len(casts)==1,casts
    player=g.node(casts[0],1080,0);g.link(pawn,'ReturnValue',player,'Object')
    cinematic=g.get('bCinematic',1360,850,'/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C')
    g.link(player,'AsBP_FoAPlayer',cinematic,'self')
    view=g.call('/Script/Engine.PlayerController:GetViewTarget',800,250)
    g.link(pc,'ReturnValue',view,'self')
    same=g.call('/Script/Engine.KismetMathLibrary:EqualEqual_ObjectObject',1080,250)
    g.link(view,'ReturnValue',same,'A');g.link(pawn,'ReturnValue',same,'B')
    locked=g.call('/Script/Engine.Controller:IsLookInputIgnored',800,450)
    g.link(pc,'ReturnValue',locked,'self')
    paused=g.call('/Script/Engine.GameplayStatics:IsGamePaused',800,650)
    blocked=g.call('/Script/Engine.KismetMathLibrary:BooleanOR',1080,500)
    g.link(locked,'ReturnValue',blocked,'A');g.link(paused,'ReturnValue',blocked,'B')
    unavailable=g.call('/Script/Engine.KismetMathLibrary:BooleanOR',1640,650)
    g.link(blocked,'ReturnValue',unavailable,'A');g.link(cinematic,'bCinematic',unavailable,'B')
    free=g.call('/Script/Engine.KismetMathLibrary:Not_PreBool',1920,500)
    g.link(unavailable,'ReturnValue',free,'A')
    show=g.call('/Script/Engine.KismetMathLibrary:BooleanAND',1640,300)
    g.link(same,'ReturnValue',show,'A');g.link(free,'ReturnValue',show,'B')
    opacity=g.call('/Script/Engine.KismetMathLibrary:SelectFloat',1920,300,A=1.0,B=0.0)
    g.link(show,'ReturnValue',opacity,'bPickA')
    apply=g.call('/Script/UMG.Widget:SetRenderOpacity',2200,0)
    g.link(dot,'Size_AimDot',apply,'self');g.link(opacity,'ReturnValue',apply,'InOpacity')
    hide=g.call('/Script/UMG.Widget:SetRenderOpacity',1080,-250,InOpacity=0.0)
    g.link(dot,'Size_AimDot',hide,'self')
    g.link(guard,'True',player,'execute');g.link(player,'then',apply,'execute')
    g.link(guard,'False',hide,'execute');g.link(player,'CastFailed',hide,'execute')
    g.comment('Aim during camera control','',g.ed.list_all_nodes(),C_VISUAL)
    # Keep other Tick consumers intact, including any subsequently authored animation.
    g=Graph(HUD)
    calls=[n for n in g.ed.list_all_nodes() if BEL.get_node_title(n).replace(' ','').split('\n')[0]=='RefreshAimDot']
    if not calls:
        ticks=[n for n in g.ed.list_all_nodes() if BEL.get_node_title(n)=='Event Tick']
        tick=ticks[0] if ticks else g.event('Tick',0,4000)
        call=g.call(HUD+'.WBP_HUD_C:RefreshAimDot',400,4000)
        outgoing=list(PIN.list_connected_pins(g.pin(tick,'then')))
        PIN.break_pin_links(g.pin(tick,'then'))
        for pin in outgoing:
            assert PIN.try_create_connection(g.pin(call,'then'),pin)
        g.exec_chain(tick,call)
        g.comment('Interaction aim','',[call],C_VISUAL)


if __name__=='__main__':
    graph()
