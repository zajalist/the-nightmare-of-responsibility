"""Select a key pinch inside the existing right-finger layer. Compile/save through Hayba afterwards."""
import unreal
PATH='/Game/FoA/Characters/Player/ABP_FoAPlayer'
POSE='/Game/FoA/Characters/Player/Anims/Hands/AS_FoA_Grip_Key_R'
BEL=unreal.BlueprintEditorLibrary;PIN=unreal.BlueprintGraphPinLibrary
bp=unreal.load_asset(PATH);seq=unreal.load_asset(POSE);assert seq
assert 'KeyGrip' in [str(n) for n in BEL.list_member_variable_names(bp)]
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
ed=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'AnimGraph')
nodes=list(ed.list_all_nodes())
existing=[n for n in nodes if n.get_class().get_name()=='AnimGraphNode_SequenceEvaluator'
          and n.get_editor_property('node').get_editor_property('sequence')==seq]

def pin(n,name,direction):
    values=BEL.list_output_pins(n) if direction=='out' else BEL.list_input_pins(n)
    return next(p for p in values if str(PIN.get_pin_name(p))==name)

def link(a,ap,b,bp):
    assert PIN.try_create_connection(pin(a,ap,'out'),pin(b,bp,'in')),(ap,bp)

if not existing:
    layer=next(n for n in nodes if n.get_class().get_name()=='AnimGraphNode_LayeredBoneBlend')
    dest=pin(layer,'BlendPoses_0','in');old=list(PIN.list_connected_pins(dest));assert len(old)==1
    palette=[str(n) for n in ed.list_available_nodes([])]
    blend_name=next(n for n in palette if 'blendposesbybool' in n.replace(' ','').replace('_','').lower())
    pos=BEL.get_node_pos(layer)
    key=ed.create_node_from_name("Animation|Sequences|Evaluate'AS_FoA_Grip_Key_R'",unreal.Vector2D(pos.x-700,pos.y+650),[]);assert key
    node=key.get_editor_property('node');node.set_editor_property('explicit_time',0.0);key.set_editor_property('node',node)
    blend=ed.create_node_from_name(blend_name,unreal.Vector2D(pos.x-350,pos.y+400),[]);assert blend
    value=ed.add_get_member_variable_node('KeyGrip','');BEL.set_node_pos(value,unreal.IntPoint(pos.x-700,pos.y+900))
    assert PIN.try_create_connection(old[0],pin(blend,'BlendPose_1','in'))
    link(key,'Pose',blend,'BlendPose_0');link(value,'KeyGrip',blend,'bActiveValue')
    link(blend,'Pose',layer,'BlendPoses_0')
    c=ed.add_comment_to_nodes('Choose the grip',[key,blend,value],40)
    BEL.set_comment_color(c,unreal.LinearColor(.3,.22,.1,1))
    for prop in ('comment_bubble_visible_in_details_panel','color_comment_bubble'):
        c.set_editor_property(prop,True)
    print('Key grip layer written; native compile/save pending')
else:
    key=existing[0]
    link_out=list(PIN.list_connected_pins(pin(key,'Pose','out')));assert len(link_out)==1
    blend=PIN.get_owning_node(link_out[0])
    if str(PIN.get_pin_name(link_out[0]))!='BlendPose_0':
        tool=list(PIN.list_connected_pins(pin(blend,'BlendPose_0','in')));assert len(tool)==1
        PIN.break_pin_links(pin(blend,'BlendPose_0','in'));PIN.break_pin_links(pin(blend,'BlendPose_1','in'))
        assert PIN.try_create_connection(tool[0],pin(blend,'BlendPose_1','in'))
        link(key,'Pose',blend,'BlendPose_0')
    print('Key true pose index0, screwdriver false pose index1 verified')
