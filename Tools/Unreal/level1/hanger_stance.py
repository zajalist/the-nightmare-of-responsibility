"""level1 lane, T7: the hanger's wire crossed his right knee and shin as he hooked and pulled the shirt (filmed under the
bed, run_20261118_1454: the hanger's box cut 6 to 8 cm into the right thigh and shin for most of the extraction).
The kneel now stands 40 cm left of the snag instead of 26 (the hand's target, the hook, does not move), so the right
leg is 14 cm further from the wire. Sets the two live pins (StartClothingHanger's teleport and UpdateClothingHanger's
per-tick body point); clothing_hanger_graphs.py STANCE_X matches. Idempotent.
  $env:HAYBA_AGENT_ID='level1'; python Tools/Unreal/level1/hanger_stance.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal/flow']
from held_tool_graphs import Batch, inspect  # noqa: E402
from clothing_chase_contract import SNAG  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
X = round(SNAG[0] - 40.0, 3)


def put(fn, title, pin, value):
    ns, _ = inspect(P, fn)
    hit = [n for n in ns if n['title'].split('\n')[0] == title and any(
        p['name'] == pin and '243.759' in str(p.get('default_value')) for p in n['pins'])]
    if not hit:
        return 'kept'
    b = Batch(P, fn)
    b.pin(hit[0]['node_id'], pin, value)
    b.run()
    return 'set'


if __name__ == '__main__':
    print('STANCE', X, dict(start=put('StartClothingHanger', 'Teleport', 'DestLocation', '%s,-95,87.15' % X),
                            update=put('UpdateClothingHanger', 'MakeVector', 'X', X)))
