"""Distribute contact-only wrist twist onto its forearm, after IK and before wrist rotation."""
import unreal
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
P='/Game/FoA/Characters/Player/ABP_FoAPlayer_MH';B=unreal.BlueprintEditorLibrary;L=unreal.BlueprintGraphPinLibrary
bp=unreal.load_asset(P);unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
ed=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'AnimGraph');nodes=list(ed.list_all_nodes())
def pin(n,name,out=False):return next(p for p in (B.list_output_pins(n) if out else B.list_input_pins(n)) if str(L.get_pin_name(p))==name)
def wire(a,ap,b,bp):assert L.try_create_connection(pin(a,ap,True),pin(b,bp))
def bone(n):return str(n.get_editor_property('node').get_editor_property('bone_to_modify').get_editor_property('bone_name'))
mods=[n for n in nodes if n.get_class().get_name()=='AnimGraphNode_ModifyBone']
if not any(bone(n)=='lowerarm_l' for n in mods):
 wrist=next(n for n in mods if bone(n)=='hand_l');dest=pin(wrist,'ComponentPose');previous=list(L.list_connected_pins(dest));assert len(previous)==1
 pos=B.get_node_pos(wrist);name=min((str(x) for x in ed.list_available_nodes([]) if 'SkeletalControls' in str(x) and 'Modify' in str(x)),key=len)
 fore=ed.create_node_from_name(name,unreal.Vector2D(pos.x,pos.y-450),[])
 ref=unreal.BoneReference();ref.set_editor_property('bone_name','lowerarm_l');n=fore.get_editor_property('node')
 for k,v in [('bone_to_modify',ref),('translation_mode',unreal.BoneModificationMode.BMM_IGNORE),('rotation_mode',unreal.BoneModificationMode.BMM_REPLACE),('scale_mode',unreal.BoneModificationMode.BMM_IGNORE),('rotation_space',unreal.BoneControlSpace.BCS_WORLD_SPACE),('alpha',0.)]:n.set_editor_property(k,v)
 fore.set_editor_property('node',n);L.break_pin_links(dest);assert L.try_create_connection(previous[0],pin(fore,'ComponentPose'));wire(fore,'Pose',wrist,'ComponentPose')
 made=[fore]
 for i,(var,key) in enumerate((('EnvironmentForearmRotation','Rotation'),('EnvironmentHandWeight','Alpha'))):
  node=ed.add_get_member_variable_node(var,'');B.set_node_pos(node,unreal.IntPoint(pos.x-350,pos.y-450+i*180));wire(node,var,fore,key);made.append(node)
 c=ed.add_comment_to_nodes('Forearm shares the grasp',made,40);B.set_comment_color(c,unreal.LinearColor(.3,.22,.1,1))
 for prop in ('comment_bubble_visible_in_details_panel','color_comment_bubble'):c.set_editor_property(prop,True)
mods=[n for n in ed.list_all_nodes() if n.get_class().get_name()=='AnimGraphNode_ModifyBone']
if not any(bone(n)=='upperarm_l' for n in mods):
 fore=next(n for n in mods if bone(n)=='lowerarm_l');dest=pin(fore,'ComponentPose');previous=list(L.list_connected_pins(dest));assert len(previous)==1
 pos=B.get_node_pos(fore);name=min((str(x) for x in ed.list_available_nodes([]) if 'SkeletalControls' in str(x) and 'Modify' in str(x)),key=len)
 upper=ed.create_node_from_name(name,unreal.Vector2D(pos.x-500,pos.y-450),[])
 ref=unreal.BoneReference();ref.set_editor_property('bone_name','upperarm_l');n=upper.get_editor_property('node')
 for k,v in [('bone_to_modify',ref),('translation_mode',unreal.BoneModificationMode.BMM_IGNORE),('rotation_mode',unreal.BoneModificationMode.BMM_ADDITIVE),('scale_mode',unreal.BoneModificationMode.BMM_IGNORE),('rotation_space',unreal.BoneControlSpace.BCS_BONE_SPACE),('alpha',0.)]:n.set_editor_property(k,v)
 upper.set_editor_property('node',n);L.break_pin_links(dest);assert L.try_create_connection(previous[0],pin(upper,'ComponentPose'));wire(upper,'Pose',fore,'ComponentPose')
 made=[upper]
 for i,(var,key) in enumerate((('EnvironmentUpperarmRotation','Rotation'),('EnvironmentHandWeight','Alpha'))):
  node=ed.add_get_member_variable_node(var,'');B.set_node_pos(node,unreal.IntPoint(pos.x-850,pos.y-450+i*180));wire(node,var,upper,key);made.append(node)
 c=ed.add_comment_to_nodes('Share large grasp rotation',made,40);B.set_comment_color(c,unreal.LinearColor(.3,.22,.1,1))
 for prop in ('comment_bubble_visible_in_details_panel','color_comment_bubble'):c.set_editor_property(prop,True)
print('Contact pronation staged; native compile/save required')
