"""Offline graph-plan check; does not claim engine compilation or runtime correctness."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import build_drive as b

def inspect(path,name):return ([dict(node_id='entry',title=name)],[])
b.inspect=inspect
plans=[]
def record(self):plans.append(self)
b.G.run=record
for name,fn in b.STEPS.items():
    if name.startswith(('BP_L2Car.','BP_Meteor.')):fn()
import drive_camera
b.call=lambda *args,**kwargs:{'functions':['UpdateCamera']}
drive_camera.build()
for plan in plans:
    refs={'entry'};inputs=set()
    for op in plan.ops:
        if op['op']=='add_node':
            assert op['ref'] not in refs;refs.add(op['ref'])
        if op['op']=='connect':
            assert op['from_node'] in refs and op['to_node'] in refs,(plan.graph,op)
            pin=(op['to_node'],op['to_pin'])
            # Merging execution branches is legal; data inputs have exactly one source.
            if op['to_pin']!='execute':assert pin not in inputs,(plan.graph,pin)
            inputs.add(pin)
        if op['op']=='set_pin':assert op['node_id'] in refs and op['value']!=''
# Rails (2026-11-17): the car follows its rail, so CheckDestination no longer builds turn signs or shelters.
guide=next(plan for plan in plans if plan.graph=='CheckDestination')
assert not any(op.get('value') in ('TURN RIGHT','TURN LEFT') for op in guide.ops)
assert not any(op.get('function_name','').endswith(':AdvanceRail') for plan in plans for op in plan.ops)
print('Drive graph plans passed:',len(plans),'functions,',sum(len(p.ops) for p in plans),'operations')

# Exercise the actual setup helper without loading Unreal: promoting the current root can self-parent it.
import ast
from types import SimpleNamespace as NS
setup=ast.parse(Path(__file__).with_name('drive_setup.py').read_text())
function=next(n for n in setup.body if isinstance(n,ast.FunctionDef) and n.name=='templates')
calls=[];already_root=True
lib=NS(get_data=lambda h:h,get_variable_name=lambda h:h,is_root_component=lambda h:already_root,
       get_object_for_blueprint=lambda h,bp:h)
sds=NS(k2_gather_subobject_data_for_blueprint=lambda bp:['Context','Root','Rail0'],
       make_new_scene_root=lambda *args:calls.append(args) or True,attach_subobject=lambda parent,child:parent!=child)
sub=NS(select_nothing=lambda:None,close_all_editors_for_asset=lambda bp:None)
engine=NS(load_asset=lambda p:p,EditorActorSubsystem=1,AssetEditorSubsystem=2,SubobjectDataSubsystem=3,
          SubobjectDataBlueprintFunctionLibrary=lib,get_editor_subsystem=lambda cls:sub,get_engine_subsystem=lambda cls:sds)
env={'unreal':engine}
exec(compile(ast.Module(body=[function],type_ignores=[]),'<root regression>','exec'),env)
env['templates']('Road');assert not calls,'An existing root must never be promoted again'
already_root=False;env['templates']('Road');assert len(calls)==1
print('Root setup regression passed: existing root untouched, replacement promoted once')

# A stale world or actor must short-circuit before any method is called on it.
proof=ast.parse(Path(__file__).with_name('drive_proof.py').read_text())
guard=next(n for n in ast.walk(proof) if isinstance(n,ast.FunctionDef) and n.name=='world_alive')
world=object();active_world=world
class Actor:
    alive=True
    def get_world(self):
        assert self.alive,'Touched a destroyed actor'
        return world
car,meteor,road,pc,manager,gi=(Actor() for _ in range(6))
engine=NS(SystemLibrary=NS(is_valid=lambda obj:obj is world or getattr(obj,'alive',False)))
env={'unreal':engine,'w':world,'UES':NS(get_game_world=lambda:active_world),
     'car':car,'meteor':meteor,'road':road,'pc':pc,'manager':manager,'gi':gi}
exec(compile(ast.Module(body=[guard],type_ignores=[]),'<PIE guard regression>','exec'),env)
assert env['world_alive']()
car.alive=False;assert not env['world_alive']()
car.alive=True;meteor.alive=False;assert not env['world_alive']()
meteor.alive=True;road.alive=False;assert not env['world_alive']()
road.alive=True;active_world=object();assert not env['world_alive']()
print('PIE guard regression passed: destroyed actor and replaced world short-circuit')
