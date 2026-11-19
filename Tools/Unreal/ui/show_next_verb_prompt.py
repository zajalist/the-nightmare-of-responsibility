"""Name the primary action when Q switches back from Inspect; native HUD-only patch."""
import json,sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch,inspect,find
P='/Game/FoA/UI/Game/WBP_HUD'
def c(n,**kw):
 r=h.call(n,kw);assert r.get('ok'),r
 d=r.get('data',{});assert d.get('ok',True),d
 return d
assert not c('editor_get_state')['pie_running'],'PIE active'
owner='room-takeover';lease=h.lease_acquire(owner,['asset:'+P],ttl_s=60,wait_s=15)
try:
 assert not c('editor_get_state')['pie_running'],'PIE started while waiting'
 ns,es=inspect(P,'HandleFocusChanged');by={n['node_id']:n for n in ns}
 select=next(n for n in ns if n['title']=='SelectString' and any(p.get('default_value')=='\nQ  Inspect' for p in n.get('pins',[])))
 if not any(e['to_node']==select['node_id'] and e['to_pin']=='A' for e in es):
  entry=find(ns,'HandleFocusChanged')
  convert=next(e['to_node'] for e in es if e['from_node']==entry and e['from_pin']=='Prompt' and by[e['to_node']]['title']=='To String (Text)')
  b=Batch(P,'HandleFocusChanged');b.fn('nextAction','/Script/Engine.KismetStringLibrary:Concat_StrStr',1450,1850,A='\nQ  ')
  b.link(convert,'ReturnValue','nextAction','B');b.link('nextAction','ReturnValue',select['node_id'],'A')
  b.comment('Name the next action',['nextAction']);b.run()
 compiled=c('blueprint_compile',path=P);c('asset_save',asset_paths=[P])
 ns,es=inspect(P,'HandleFocusChanged')
 Path('P:/FoA/Saved/LookDev/prompt_audit/next_action_prompt.json').write_text(json.dumps({'compile':compiled,'nodes':ns,'edges':es},indent=1))
 print('Q now names the primary action instead of Back to action; compiled and saved')
finally:h.release(owner,lease)
