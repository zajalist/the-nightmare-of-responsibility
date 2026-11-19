"""Persistent sleeping eyelids after CopyPose; owner-driven in game and Sequencer preview."""
import unreal,os
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py',encoding='utf-8').read())
FACE='/Game/FoA/Characters/Teen/Anim/ABP_FoA_TeenHead'
PLAYER='/Game/FoA/Characters/Player/BP_FoAPlayer'
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
bp=unreal.load_asset(FACE)
def palette(ed,*parts):
 norm=lambda s:str(s).replace(' ','').replace('_','').lower()
 return min((str(n) for n in ed.list_available_nodes([]) if all(norm(p) in norm(n) for p in parts)),key=len)
if os.environ.get('FOA_PHASE')=='declare':
 ensure_vars(FACE,[('SleepEyeClosure',ptype('real'),'0.0','Sleep',False)])
else:
 g=Graph(FACE,'EventGraph')
 nodes=list(g.ed.list_all_nodes())
 event=next(n for n in nodes if 'BlueprintUpdateAnimation' in BEL.get_node_title(n).replace(' ',''))
 assert not PIN.list_connected_pins(BEL.find_then_pin(event)), 'Keep any existing head update work'
 owner=g.call('/Script/Engine.AnimInstance:GetOwningActor',0,300)
 cast=g.node(palette(g.ed,'CastToBP_FoAPlayer'),300,0);g.link(owner,'ReturnValue',cast,'Object')
 source=g.get('SleepEyeClosure',600,300,PLAYER+'.BP_FoAPlayer_C');g.link(cast,'AsBP_FoAPlayer',source,'self')
 clamp=g.call('/Script/Engine.KismetMathLibrary:FClamp',850,300,Min=0.0,Max=1.0);g.link(source,'SleepEyeClosure',clamp,'Value')
 target=g.set('SleepEyeClosure',1100,0);g.link(clamp,'ReturnValue',target,'SleepEyeClosure');g.exec_chain(event,cast,target)
 g.comment('Read sleeping expression','Owner property also evaluates on cinematic spawnables',[owner,cast,source,clamp,target],C_DATA)
 ed=GE.get_graph_editor_by_name(bp,'AnimGraph');nodes=list(ed.list_all_nodes())
 pose=next(n for n in nodes if isinstance(n,unreal.AnimGraphNode_CopyPoseFromMesh));output=next(n for n in nodes if isinstance(n,unreal.AnimGraphNode_Root))
 assert not any(isinstance(n,unreal.AnimGraphNode_ModifyCurve) for n in nodes)
 curve=ed.create_node_from_name(palette(ed,'ModifyCurve'),V2(0,0),[])
 data=curve.get_editor_property('node');data.set_editor_property('curve_map',{unreal.Name('eyeBlinkLeft'):1.0,unreal.Name('eyeBlinkRight'):1.0});data.set_editor_property('apply_mode',unreal.ModifyCurveApplyMode.BLEND);data.set_editor_property('alpha',0.0);curve.set_editor_property('node',data)
 PIN.break_pin_links(Graph.pin(pose,'Pose','out'))
 assert PIN.try_create_connection(Graph.pin(pose,'Pose','out'),Graph.pin(curve,'SourcePose','in'))
 assert PIN.try_create_connection(Graph.pin(curve,'Pose','out'),Graph.pin(output,'Result','in'))
 value=ed.add_get_member_variable_node('SleepEyeClosure','')
 assert PIN.try_create_connection(Graph.pin(value,'SleepEyeClosure','out'),Graph.pin(curve,'Alpha','in'))
 for node,x,y in [(pose,-400,0),(curve,0,0),(output,400,0),(value,0,250)]:BEL.set_node_pos(node,P(x,y))
compile_save(FACE)
