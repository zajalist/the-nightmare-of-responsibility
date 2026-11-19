"""Keep objectives inside the safe area and expose the existing inspect action."""
import sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch,inspect,find
P='/Game/FoA/UI/Game/WBP_HUD'

def call(name,**args):
 r=h.call(name,args);assert r.get('ok'),r
 d=r.get('data',{});assert d.get('ok',True) and not d.get('failed'),d
 return d
def main():
 assert not call('editor_get_state')['pie_running']
 owner=h.agent_id();token=h.lease_acquire(owner,['asset:'+P],ttl_s=90,wait_s=30)
 try:
  for name,slot in [('Safe_Frame',dict(horizontal_alignment='Fill',vertical_alignment='Fill')),
    ('Txt_Objective',dict(horizontal_alignment='Left',vertical_alignment='Top',padding=[48,42,48,0])),
    ('Size_ContextPrompt',dict(horizontal_alignment='Center',vertical_alignment='Bottom',padding=[40,0,40,78])),
    ('Brd_Narration',dict(horizontal_alignment='Center',vertical_alignment='Bottom',padding=[40,0,40,188]))]:
   call('ui_set_widget_properties',widget_blueprint_path=P,widget_name=name,slot_props=slot)
  for name,size in [('Txt_Objective',28),('Txt_Prompt',24)]:
   call('ui_set_widget_properties',widget_blueprint_path=P,widget_name=name,
    properties=dict(Font=f'(FontObject="/Script/Engine.Font\'/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI\'",TypefaceFontName="SemiBold",Size={size})',
      AutoWrapText=False,WrapTextAt=640,ShadowOffset='(X=0,Y=2)',ShadowColorAndOpacity='(R=0,G=0,B=0,A=0.8)'))
  call('ui_set_widget_properties',widget_blueprint_path=P,widget_name='Txt_Narration',properties=dict(AutoWrapText=False,WrapTextAt=760))
  # Reading time follows text length while retaining subtitle preferences and tool ownership.
  ns,es=inspect(P,'HandleNarration');timers=[n for n in ns if n['title']=='SetTimerbyFunctionName' or n['title']=='Set Timer by Function Name']
  assert len(timers)==1,[(n['title']) for n in ns]
  if not any(n['title']=='Len' for n in ns):
   e=find(ns,'HandleNarration');b=Batch(P,'HandleNarration')
   b.fn('string','/Script/Engine.KismetTextLibrary:Conv_TextToString',0,1000);b.link(e,'Line','string','InText')
   b.fn('chars','/Script/Engine.KismetStringLibrary:Len',300,1000);b.link('string','ReturnValue','chars','S')
   b.fn('number','/Script/Engine.KismetMathLibrary:Conv_IntToDouble',600,1000);b.link('chars','ReturnValue','number','InInt')
   b.fn('reading','/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble',900,1000,B=.047);b.link('number','ReturnValue','reading','A')
   b.fn('lead','/Script/Engine.KismetMathLibrary:Add_DoubleDouble',1200,1000,B=1.7);b.link('reading','ReturnValue','lead','A')
   b.fn('duration','/Script/Engine.KismetMathLibrary:FClamp',1500,1000,Min=3.5,Max=8.5);b.link('lead','ReturnValue','duration','Value')
   b.link('duration','ReturnValue',timers[0]['node_id'],'Time');b.comment('Time to read',['string','chars','number','reading','lead','duration']);b.run()
  ns,es=inspect(P,'HandleFocusChanged')
  if not any(n['title']=='Length' for n in ns):
   entry=find(ns,'HandleFocusChanged');setter=next(n for n in ns if n['title'].startswith('SetText'))
   old=next(e for e in es if e['to_node']==setter['node_id'] and e['to_pin']=='InText')
   b=Batch(P,'HandleFocusChanged')
   b.fn('current','/Script/Engine.KismetTextLibrary:Conv_TextToString',1500,600);b.link(old['from_node'],old['from_pin'],'current','InText')
   b.fn('count','/Script/Engine.KismetArrayLibrary:Array_Length',0,900);b.link(entry,'Verbs','count','TargetArray')
   b.fn('multiple','/Script/Engine.KismetMathLibrary:Greater_IntInt',300,900,B=1);b.link('count','ReturnValue','multiple','A')
   b.fn('looking','/Script/Engine.KismetMathLibrary:Greater_IntInt',300,1100,B=0);b.link(entry,'VerbIndex','looking','A')
   b.fn('hint','/Script/Engine.KismetMathLibrary:SelectString',600,1100,A='\nQ  Back to action',B='\nQ  Inspect');b.link('looking','ReturnValue','hint','bPickA')
   b.fn('optional','/Script/Engine.KismetMathLibrary:SelectString',900,900);b.link('multiple','ReturnValue','optional','bPickA');b.link('hint','ReturnValue','optional','A')
   b.fn('combined','/Script/Engine.KismetStringLibrary:Concat_StrStr',1800,700);b.link('current','ReturnValue','combined','A');b.link('optional','ReturnValue','combined','B')
   b.fn('text','/Script/Engine.KismetTextLibrary:Conv_StringToText',2100,700);b.link('combined','ReturnValue','text','InString')
   b.cut(old['from_node'],old['from_pin'],setter['node_id'],'InText');b.link('text','ReturnValue',setter['node_id'],'InText')
   b.comment('Explain the other action',['current','count','multiple','looking','hint','optional','combined','text'])
   # The native generic call node does not specialize array pins; repair before compiling.
   call('blueprint_graph_batch',path=P,graph_name='HandleFocusChanged',ops=b.ops,compile=False,save=False)
   import ue_remote
   assert ue_remote.run_hayba(str(Path(__file__).with_name('repair_hud_array_pin.py')),{},['asset:'+P],owner,token)
  call('blueprint_compile',path=P)
  print('HUD layout, inspect hint, and reading time saved; visual verification pending')
 finally:h.release(owner,token)
if __name__=='__main__':main()
