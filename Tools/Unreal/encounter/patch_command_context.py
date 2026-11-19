"""A truthful action hint during player command replaces stale introduction narration."""
exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read())
PATH='/Game/FoA/Gameplay/Encounter/WBP_Encounter'
g=Graph(PATH,'RefreshBattlePresentation')
for node in g.ed.list_all_nodes():
    key=BEL.find_input_pin(node,'B')
    if PIN.is_valid(key) and str(PIN.get_pin_value(key))=='Sock':
        val(node,'B','Socks')
if not any(str(BEL.get_comment_text(n))=='Explain the current choice' for n in g.ed.list_comment_nodes()):
    native=[n for n in g.ed.list_all_nodes() if str(BEL.get_node_title(n)).replace(' ','')=='SetVisibility'
            and BEL.get_node_pos(n).y<0]
    on=native[0];old=list(PIN.list_connected_pins(BEL.find_then_pin(on)));assert len(old)==1
    enc=mget(g,'Encounter',0,2200)
    garment=fcall(g,'/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C:TargetGarment',300,2200,self=enc)
    data=field(g,po(garment,'Garment'),'Data','/Game/FoA/Gameplay/Encounter/BP_Garment.BP_Garment_C',600,2200)
    kind=field(g,data,'GarmentId',OPP_C,900,2200)
    line='Your turn. Choose an Act or take a deep breath.'
    for i,(name,hint) in enumerate((('Shirt','Find Armhole strengthens Button Up.'),
          ('Socks','Match the pair, then pull the sock on.'),('Trousers','Untwist the leg, then step in.'),
          ('Tie','Loosen the tie before tying the knot.'))):
        x=1200+i*640
        same=fcall(g,KML+':EqualEqual_NameName',x,2400,A=kind,B=name)
        line=fcall(g,KML+':SelectString',x,2200,A=hint,B=line,bPickA=same)
    text=fcall(g,KTL+':Conv_StringToText',3880,2200,InString=line)
    show=fcall(g,'/Script/UMG.TextBlock:SetText',4200,1900,self=mget(g,'Txt_Narration',3880,1900),InText=text)
    PIN.break_pin_links(BEL.find_then_pin(on));go(on,show);wire(BEL.find_then_pin(show),old[0])
    box(g,'Explain the current choice','',[enc,garment,data,kind,text,show],'stage')
unreal.EditorAssetLibrary.save_loaded_asset(g.bp,False)
print('Player-command context saved; compile in same lease')
