"""Selected opponent, corner stats and one bottom command dock. Native properties; existing widgets retained.
--calls emits C++ calls. Run graph phase through ue_remote after properties, then compile/save atomically.
"""
import json
import sys

WBP = '/Game/FoA/Gameplay/Encounter/WBP_Encounter'
FONT = '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'


def calls():
    out = []
    def props(name, values=None, slot=None):
        p = dict(widget_blueprint_path=WBP, widget_name=name)
        if values: p['properties'] = values
        if slot: p['slot_props'] = slot
        out.append(dict(cmd='ui_set_widget_properties', params=p))
    def text(name, size, **extra):
        props(name, dict(Font=dict(FontObject=FONT, TypefaceFontName='SemiBold', Size=size),
                         ColorAndOpacity=dict(SpecifiedColor=[.92,.92,.92,1]), **extra))
    def box(name, child_names):
        out.append(dict(cmd='ui_build_tree', params=dict(widget_blueprint_path=WBP,
            parent_widget_name='CmdButtons', tree=dict(**{'class':'HorizontalBox'},name=name,
            children=[dict(**{'class':'VerticalBox'},name=n,slot_props=dict(fill=1,padding=[40,0,0,0] if n=='UtilityRight' else [0,0,0,0])) for n in child_names]))))
    props('CommandPanel',dict(Padding='(Left=28,Top=18,Right=28,Bottom=18)'),
          dict(anchors_min=[0,1],anchors_max=[1,1],alignment=[0,1],position=[48,-48],size=[48,208],auto_size=False))
    props('EnemyPanel',dict(Padding='(Left=20,Top=16,Right=20,Bottom=16)'),
          dict(anchors_min=[0,0],anchors_max=[0,0],alignment=[0,0],position=[48,48],size=[560,150],auto_size=False))
    props('SelfBox',None,dict(anchors_min=[1,0],anchors_max=[1,0],alignment=[1,0],position=[-48,48],size=[320,160],auto_size=False))
    props('LogPanel',dict(Padding='(Left=24,Top=12,Right=24,Bottom=12)'),
          dict(anchors_min=[.5,1],anchors_max=[.5,1],alignment=[.5,1],position=[0,-280],size=[1160,64],auto_size=False))
    text('Txt_Narration',26,AutoWrapText=True,WrapTextAt=1100)
    props('Txt_BattlePhase',dict(Visibility='Collapsed'))
    text('Txt_BattleHelp',18,Text='Use arrows to choose. Enter confirms.')
    props('Txt_BattleHelp',None,dict(anchors_min=[0,1],anchors_max=[0,1],alignment=[0,1],position=[60,-14],size=[1000,26],auto_size=False))
    props('ActBox',None,dict(fill=.8,padding=[0,0,32,0]))
    props('CmdButtons',None,dict(fill=1.2))
    text('Txt_Target',28,Text='Act')
    props('Txt_Target',None,dict(padding=[0,0,0,8]))
    box('UtilityColumns', ['UtilityLeft','UtilityRight'])
    for i in range(5):
        text('Txt_Enemy'+str(i),26)
        text('Txt_Intent'+str(i),22,AutoWrapText=True,WrapTextAt=500)
        props('Row'+str(i),None,dict(padding=[0,0,0,0]))
    for name in ['Btn_Act0','Btn_Act1','Btn_Act2','Btn_Breathe','Btn_Mirror','Btn_Items','Btn_Flee','Btn_NextTarget']:
        props(name,dict(bPlainLabel=True,LabelSize=28.0 if name.startswith('Btn_Act') else 26.0,SandMaterial=None,TextAlphaRest=.88,TextAlphaHover=1.0,
                        TextAlphaDisabled=.4),dict(padding=[0,0,12,0]))
    for name in ['BattleActIcons','Icon_Breathe','Icon_Mirror','Icon_Items','Icon_Flee','Icon_NextTarget']:
        props(name,dict(Visibility='HitTestInvisible'))
    for stat in ['Composure','Resolve']:
        text('Txt_'+stat+'Label',24); text('Txt_'+stat,24)
        props('Size_Bar_'+stat,dict(WidthOverride=320.,bOverride_WidthOverride=True))
    text('Txt_Statuses',20,AutoWrapText=True,WrapTextAt=320)
    for c in out: print(json.dumps(c))


def graph():
    import unreal
    ns=globals(); exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read(),ns)
    bp=unreal.load_asset(WBP)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    def widget(name):
        w=unreal.find_object(None,WBP+'.WBP_Encounter:WidgetTree.'+name); assert w,name; return w
    for name,parent in [('BattleRow_Breathe','UtilityLeft'),('BattleRow_Mirror','UtilityLeft'),
                        ('BattleRow_Items','UtilityLeft'),('BattleRow_Flee','UtilityRight'),
                        ('BattleRow_NextTarget','UtilityRight')]:
        w,p=widget(name),widget(parent)
        if w.get_parent()!=p:
            w.remove_from_parent(); p.add_child(w)
    g=Graph(WBP,'RefreshRow')
    # Keep row order: the existing refresh graph indexes name, pips and intent within each VerticalBox.
    branches=g.ed.list_nodes_of_class(unreal.K2Node_IfThenElse)
    gate=sorted(branches,key=lambda n:BEL.get_node_pos(n).x)[1]
    old=PIN.list_connected_pins(BEL.find_condition_pin(gate))[0]
    if 'Only the selected garment' not in [str(BEL.get_comment_text(n)) for n in g.ed.list_comment_nodes()]:
        e=entry_node(g); enc=mget(g,'Encounter',600,1000)
        target=field(g,enc,'Target','/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C',900,1000)
        eq=fcall(g,KML+':EqualEqual_IntInt',1200,1000,A=po(e,'Index'),B=target)
        both=fcall(g,KML+':BooleanAND',1500,1000,A=po(eq))
        wire(old,pi(both,'B')); PIN.break_pin_links(BEL.find_condition_pin(gate)); wire(po(both),BEL.find_condition_pin(gate))
        box(g,'Only the selected garment','',[enc,target,eq,both],'stage')
    g=Graph(WBP,'RefreshBattlePresentation')
    for n in g.ed.list_all_nodes():
        if str(BEL.get_node_title(n)).replace(' ','')=='SetVisibility' and BEL.get_node_pos(n).y>0:
            val(n,'InVisibility','Hidden')
    e=entry_node(g)
    if not any(str(BEL.get_node_title(n)).replace(' ','')=='SetText(Text)' and BEL.get_node_pos(n).x<0 for n in g.ed.list_all_nodes()):
        old=PIN.list_connected_pins(BEL.find_then_pin(e))[0]
        label=fcall(g,'/Script/UMG.TextBlock:SetText',-700,0,self=mget(g,'Txt_Target',-1000,220),InText='Act')
        PIN.break_pin_links(BEL.find_then_pin(e)); go(e,label); wire(BEL.find_then_pin(label),old)
        box(g,'Primary action','',[label],'stage')
    unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
    import runpy
    runpy.run_path('P:/FoA/Tools/Unreal/encounter/patch_command_context.py')
    print('Battle dock, selected garment and compact commands staged; compile/save in same lease')


if __name__=='__main__':
    calls() if '--calls' in sys.argv else graph()
