"""One left-hand world contact control after retargeting; existing right tool rig is unchanged."""
import unreal
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
P='/Game/FoA/Characters/Player/ABP_FoAPlayer_MH'
B=unreal.BlueprintEditorLibrary;L=unreal.BlueprintGraphPinLibrary
bp=unreal.load_asset(P);unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
ed=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'AnimGraph');nodes=list(ed.list_all_nodes())
assert not any(n.get_class().get_name()=='AnimGraphNode_TwoBoneIK' and str(n.get_editor_property('node').get_editor_property('ik_bone').get_editor_property('bone_name'))=='hand_l' for n in nodes),'Left hand IK already installed'
def pin(n,name,output=False):return next(p for p in (B.list_output_pins(n) if output else B.list_input_pins(n)) if str(L.get_pin_name(p))==name)
def wire(a,ap,b,bp):assert L.try_create_connection(pin(a,ap,True),pin(b,bp)),(ap,bp)
tail=next(n for n in nodes if 'ComponentToLocalSpace' in n.get_class().get_name())
dest=pin(tail,'ComponentPose');previous=list(L.list_connected_pins(dest));assert len(previous)==1
pos=B.get_node_pos(tail);palette=[str(n) for n in ed.list_available_nodes([])]
def create(*terms):
 name=min((n for n in palette if all(t.lower() in n.replace(' ','').lower() for t in terms)),key=len)
 return ed.create_node_from_name(name,unreal.Vector2D(pos.x,pos.y),[])
ik=create('SkeletalControls','TwoBoneIK');wrist=create('SkeletalControls','Modify')
B.set_node_pos(wrist,unreal.IntPoint(pos.x+500,pos.y));B.set_node_pos(tail,unreal.IntPoint(pos.x+1000,pos.y))
bone=unreal.BoneReference();bone.set_editor_property('bone_name','hand_l')
n=ik.get_editor_property('node')
for key,value in [('ik_bone',bone),('effector_location_space',unreal.BoneControlSpace.BCS_WORLD_SPACE),('joint_target_location_space',unreal.BoneControlSpace.BCS_WORLD_SPACE),('allow_stretching',False),('take_rotation_from_effector_space',False),('maintain_effector_rel_rot',True),('alpha',0.)]:n.set_editor_property(key,value)
ik.set_editor_property('node',n)
n=wrist.get_editor_property('node')
for key,value in [('bone_to_modify',bone),('translation_mode',unreal.BoneModificationMode.BMM_IGNORE),('rotation_mode',unreal.BoneModificationMode.BMM_REPLACE),('scale_mode',unreal.BoneModificationMode.BMM_IGNORE),('rotation_space',unreal.BoneControlSpace.BCS_WORLD_SPACE),('alpha',0.)]:n.set_editor_property(key,value)
wrist.set_editor_property('node',n)
L.break_pin_links(dest);assert L.try_create_connection(previous[0],pin(ik,'ComponentPose'))
wire(ik,'Pose',wrist,'ComponentPose');wire(wrist,'Pose',tail,'ComponentPose')
made=[ik,wrist]
for i,(name,node,key) in enumerate((('EnvironmentHandTarget',ik,'EffectorLocation'),('EnvironmentElbowTarget',ik,'JointTargetLocation'),('EnvironmentHandWeight',ik,'Alpha'),('EnvironmentHandRotation',wrist,'Rotation'))):
 v=ed.add_get_member_variable_node(name,'');B.set_node_pos(v,unreal.IntPoint(pos.x-280+(500 if node==wrist else 0),pos.y+300+i*150));wire(v,name,node,key);made.append(v)
 if name=='EnvironmentHandWeight':wire(v,name,wrist,'Alpha')
c=ed.add_comment_to_nodes('Left hand follows the handle',made,48);B.set_comment_color(c,unreal.LinearColor(.3,.22,.1,1))
for prop in ('comment_bubble_visible_in_details_panel','color_comment_bubble'):c.set_editor_property(prop,True)
print('Left contact controls staged; native compile/save required')
