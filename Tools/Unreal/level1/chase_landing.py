"""level1 lane, sweep (2026-11-18): catching the shirt after escape one, his first-person camera dove into the west
window's curtain for about 0.8 s as the pick-up bent him to the floor (run_20261118_1517 L1S7, frames 27 to 31): the
shirt landed at (-75, -160), against the curtain's hem. It now lands 25 cm east, at (-50, -160), still on the lit
boards. Sets EscapeClothingOne's landing transform and its focus point; clothing_chase_contract.LANDINGS[1] matches.
  $env:HAYBA_AGENT_ID='level1'; python Tools/Unreal/level1/chase_landing.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal/flow']
from held_tool_graphs import Batch, inspect  # noqa: E402
from clothing_chase_contract import LANDINGS  # noqa: E402

P, FN = '/Game/FoA/Gameplay/BP_BeatDirector', 'EscapeClothingOne'
X, Y, Z = LANDINGS[1]
assert X == -50.0, LANDINGS[1]
ns, _ = inspect(P, FN)
b, n = Batch(P, FN), 0
for node in ns:
    pins = {p['name']: str(p.get('default_value')) for p in node['pins']}
    if node['title'].startswith('MakeTransform') and pins.get('Location', '').startswith('-75.0,-160.0'):
        b.pin(node['node_id'], 'Location', '%s,%s,%s' % (X, Y, Z)); n += 1
    if node['title'].startswith('MakeVector') and pins.get('X') == '-75.0' and pins.get('Y') == '-160.0':
        b.pin(node['node_id'], 'X', X); n += 1
if n:
    b.run()
print('LANDING', LANDINGS[1], 'pins set', n)
