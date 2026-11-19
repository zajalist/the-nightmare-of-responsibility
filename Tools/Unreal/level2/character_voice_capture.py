"""Capture only the five voice implementation graphs; no gameplay changes."""
import json
from pathlib import Path
import unreal as u

root=Path('P:/FoA/Saved/CharacterVoice/graphs');root.mkdir(parents=True,exist_ok=True)
rows=[]
for path,names in (
    ('/Game/FoA/UI/Framework/BP_FoAFrontEnd',('SayCharacter','StopCharacterVoice','PickCharacterVoice')),
    ('/Game/FoA/Level2/Journey/BP_L2Journey',('SayCharacter','StopCharacterVoice'))):
    asset=u.load_asset(path)
    assert asset.get_editor_property('status')==u.BlueprintStatus.BS_UP_TO_DATE
    for name in names:
        ed=u.BlueprintGraphEditor.get_graph_editor_by_name(asset,name)
        png=root/(asset.get_name()+'_'+name+'.png')
        u.FoAGraphToolsLibrary.capture_graph_png(asset,name,str(png),True)
        rows.append(dict(asset=path,graph=name,nodes=len(ed.list_all_nodes()),png=str(png)))
(root/'manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print('CAPTURE',len(rows))
