"""Short settled-view check; the existing harness owns PIE and restores preferences."""
from pathlib import Path
source=Path('P:/FoA/Tools/Splats/pie_room_takeover.py').read_text()
exec(source.replace("S['handle']=unreal.register_slate_post_tick_callback(tick)",''))
OUT='P:/FoA/Saved/WorldShots/pie_clue_lighting.json'
PLAN=[(5,begin),(5.1,lambda w:clue_view(w,'Wardrobe')),
 (6.8,lambda w:clue_shot(w,'wardrobe_lighting')),
 (7,lambda w:(stage(w,3),clue_view(w,'Bed'))),
 (9.5,lambda w:clue_shot(w,'bed_lighting')),
 (10.2,lambda w:log('capture_drained'))]
S['handle']=unreal.register_slate_post_tick_callback(tick)
