"""Reuse the real frontend boot harness, then observe actual vase geometry/timers."""
from pathlib import Path
source=Path('P:/FoA/Tools/Splats/pie_room_takeover.py').read_text()
registration="S['handle']=unreal.register_slate_post_tick_callback(tick)"
assert source.count(registration)==1
exec(compile(source.replace(registration,''),'pie_room_takeover.py','exec'),globals())
OUT='P:/FoA/Saved/WorldShots/pie_vase_boss.json'
def vase_state(w):
 a=room(w)
 return dict(active=a.get_editor_property('bVaseSceneActive'),broken=a.get_editor_property('bVaseBroken'),
  visible=[c.get_name() for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.get_name().startswith('Vase') and c.is_visible()],
  boss_scale=list(a.get_editor_property('VaseSandBoss').get_world_scale().to_tuple()),stage=a.get_editor_property('Stage'))
def vase_check(w,name,test):
 v=vase_state(w);log(name,**v);assert test(v),(name,v)
def vase_start(w):
 room(w).call_method('Reset');room(w).call_method('SetStage',(5,));clue_view(w,'Vase')
def vase_shot(w,name):
 unreal.SystemLibrary.execute_console_command(w,f'Shot showui -nosuffix filename="P:/FoA/Saved/WorldShots/vase_scene_{name}.png"')
 log('vase_'+name,**vase_state(w))
PLAN=[
 (5,vase_start),
 (5.3,lambda w:room(w).call_method('BreakVaseThenBoss')),
 (5.6,lambda w:vase_shot(w,'tip')),
 (6.2,lambda w:vase_check(w,'shattered',lambda v:v['active'] and v['broken'] and 'VaseIntact' not in v['visible'] and len([n for n in v['visible'] if n.startswith('VaseShard')])==6)),
 (6.25,lambda w:vase_shot(w,'shards')),
 (6.3,lambda w:clue_view(w,'Boss')),
 (7.2,lambda w:vase_shot(w,'forming')),
 (8.7,lambda w:vase_check(w,'formed_geometry',lambda v:v['active'] and 'VaseSandBoss' in v['visible'] and abs(v['boss_scale'][2]-.85)<.001)),
 (8.75,lambda w:vase_shot(w,'boss')),
 (9.5,lambda w:vase_check(w,'handoff',lambda v:not v['active'] and v['broken'] and 'VaseSandBoss' not in v['visible'] and 'VaseSandPile' in v['visible'])),
 (9.8,lambda w:room(w).call_method('CancelVaseFormation')),
 (10,lambda w:vase_check(w,'scene_only_reset',lambda v:v['stage']==5 and not v['active'] and not v['broken'] and v['visible']==['VaseIntact'])),
 (10.2,lambda w:room(w).call_method('BreakVaseThenBoss')),
 (10.4,lambda w:room(w).call_method('CancelVaseFormation')),
 (14.5,lambda w:vase_check(w,'cancel_pending',lambda v:v['stage']==5 and not v['active'] and not v['broken'] and v['visible']==['VaseIntact'])),
]
S['handle']=unreal.register_slate_post_tick_callback(tick)
