"""Door-tool lane: the screwdriver view. SetDoorToolPresentation frames the door tool with three Selects (A = the
screwdriver, B = the key): the camera's place, its aim (both in the door's frame, cm) and its field of view. This sets
only their A pins. One Hayba batch, compiled 0/0 and saved, or nothing is saved.
  $env:HAYBA_AGENT_ID='doortool'; python Tools/Unreal/doortool/door_view.py show
  $env:HAYBA_AGENT_ID='doortool'; python Tools/Unreal/doortool/door_view.py set CAM=x,y,z AIM=x,y,z FOV=50
(hold a lease on /Game/FoA/Gameplay/BP_Door first)"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
from held_tool_graphs import Batch, inspect  # noqa: E402

DOOR = '/Game/FoA/Gameplay/BP_Door'
G = 'SetDoorToolPresentation'


def nums(text):
    try:
        return [round(float(x), 3) for x in str(text).replace('(', '').replace(')', '').replace('X=', '').replace('Y=', '')
                .replace('Z=', '').split(',')]
    except ValueError:
        return None


def selects():
    """The three framing Selects: the ones whose B pin holds the key's frame (camera -30,-144,102; aim -7,-84,88; fov 36)."""
    nodes, _ = inspect(DOOR, G)
    found = {}
    for n in nodes:
        if not n['title'].startswith('Select'):
            continue
        pins = {p.get('name'): p.get('default_value') for p in n.get('pins', [])}
        b = nums(pins.get('B'))
        for role, key in (('CAM', [-30.0, -144.0, 102.0]), ('AIM', [-7.0, -84.0, 88.0]), ('FOV', [36.0])):
            if b == key:
                assert role not in found, ('two Selects carry the key frame for', role)
                found[role] = (n['node_id'], pins.get('A'))
    assert set(found) == {'CAM', 'AIM', 'FOV'}, found
    return found


def main():
    found = selects()
    for role, (node, a) in sorted(found.items()):
        print(role, node, 'A =', a)
    if sys.argv[1] == 'show':
        return
    args = dict(a.split('=', 1) for a in sys.argv[2:])
    b = Batch(DOOR, G)
    for role, value in args.items():
        assert role in found and len(nums(value)) == (1 if role == 'FOV' else 3), (role, value)
        b.pin(found[role][0], 'A', value)
    b.run()
    for role, (node, a) in sorted(selects().items()):
        print('now', role, 'A =', a)


if __name__ == '__main__':
    main()
