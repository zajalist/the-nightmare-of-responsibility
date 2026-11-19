"""M_UI_Scrim: swap its MPC_UI 'Soot' CollectionParameter (which no longer resolves: "invalid parameter None") for a plain
VectorParameter 'Soot' with the same value, through Hayba. Run outside the editor, holding the UI lease.
  python Tools/Unreal/ui/fix_scrim_hayba.py"""
import json
import re
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
from hayba_call import call  # noqa: E402

M = '/Game/FoA/UI/Materials/M_UI_Scrim'


def hb(cmd, **p):
    r = call(cmd, p)
    assert r.get('ok'), f'{cmd}: {json.dumps(r)[:400]}'
    return r


info = hb('material_get_info', path=M)['data']
mpc = [e for e in info['expressions'] if e['class'] == 'MaterialExpressionCollectionParameter']
for e in mpc:
    hb('material_delete_node', material_path=M, node_id=e['id'])
r = hb('material_add_node', material_path=M, expression_class='MaterialExpressionVectorParameter', node_pos=[-288, -64],
       properties={'ParameterName': 'Soot', 'DefaultValue': '(R=0.004,G=0.004,B=0.004,A=1.0)'})
soot = re.search(r'"(MaterialExpressionVectorParameter_\d+)"', json.dumps(r)).group(1)
hb('material_connect_nodes', material_path=M, from_node=soot, from_output_index=0, to_property='emissive')
r = hb('material_compile', material_path=M)
d = r.get('data', r)
print('scrim', 'removed', len(mpc), 'MPC nodes; compile ok', d.get('ok'), 'saved', d.get('saved'), d.get('errors'))
