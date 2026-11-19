"""Acceptance outranks the optional preference for an 18-degree wrist."""
import ast
import copy
from pathlib import Path
tree=ast.parse(Path(__file__).with_name('screwdriver_twin.py').read_text())
scope={}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('cost','ok')],type_ignores=[]),'<cost>','exec'),scope)
good=dict(pen=0,clear_min_mm=1.5,contact_min_mm=2,pads={'index_pad':2,'pinky_pad':2,'thumb_pad':2},inline_deg=20,wrist_deg=20,butt_cm=1,elbow_deg=112,miss_cm=0)
bad=copy.deepcopy(good);bad.update(inline_deg=17,wrist_deg=17,butt_cm=.99)
assert scope['ok'](good) and not scope['ok'](bad)
assert scope['cost'](good)<scope['cost'](bad)
print('Screw cost: feasible grip outranks softer but unsupported wrist')
