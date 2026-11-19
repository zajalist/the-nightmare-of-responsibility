"""Read-only complete graph snapshot for native-inspector truncation; brokered file runner."""
import json
import os
import sys
from pathlib import Path
import unreal as u
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import bp_layout

asset=os.environ['FOA_VOICE_ASSET'];name=os.environ['FOA_VOICE_GRAPH']
bp=u.load_asset(asset)
ed=u.BlueprintGraphEditor.get_graph_editor_by_name(bp,name)
bel=u.BlueprintEditorLibrary
parsed=bp_layout.parse_t3d(bp_layout.export_t3d(bp))[name]
live={n.get_name():n for n in list(ed.list_all_nodes())+list(ed.list_comment_nodes())}
guid=lambda key:parsed[key]['props']['NodeGuid']
nodes=[];edges=[]
for key,node in parsed.items():
    title='Comment' if node['cls']=='EdGraphNode_Comment' else str(bel.get_node_title(live[key])).split('\n')[0]
    nodes.append(dict(node_id=guid(key),title=title,
        pins=[dict(name=p['name'],direction='output' if p['out'] else 'input',type=p['cat']) for p in node['pins']]))
    for p in node['pins']:
        if p['out']:
            for target,pin_id in p['links']:
                other=next(x for x in parsed[target]['pins'] if x['id']==pin_id)
                edges.append(dict(from_node=guid(key),from_pin=p['name'],to_node=guid(target),to_pin=other['name']))
out=Path('P:/FoA/Saved/CharacterVoice')/(asset.rsplit('/',1)[1]+'_'+name+'_graph.json')
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(dict(nodes=nodes,edges=edges)),encoding='utf8')
print('GRAPH SNAPSHOT',len(nodes),len(edges))
