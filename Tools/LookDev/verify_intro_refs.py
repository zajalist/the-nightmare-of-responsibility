"""Read only the saved intro texture arrays and their underlying capture assets."""
import json
from pathlib import Path
import unreal
c=unreal.load_class(None,'/Game/FoA/UI/Intro/WBP_IntroStory.WBP_IntroStory_C');d=unreal.get_default_object(c)
r={}
for n in ('Panels','NearPanels'):
 v=list(d.get_editor_property(n));assert len(v)==8,(n,len(v))
 r[n]=[t.get_path_name() for t in v]
 assert all('/T_Intro_Game' in p for p in r[n])
assert all('_Near.' in p for p in r['NearPanels'])
r['seconds']=list(d.get_editor_property('Seconds'))
r['lines']=list(d.get_editor_property('Lines'))
r['first_foreground_size']=[d.get_editor_property('NearPanels')[0].blueprint_get_size_x(),d.get_editor_property('NearPanels')[0].blueprint_get_size_y()]
Path('P:/FoA/Saved/LookDev/intro_restored/actual_game_refs.json').write_text(json.dumps(r,indent=1))
print('Eight actual-game background references and eight matching foreground references verified')
