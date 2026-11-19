"""Door-tool lane: print the DTS plan's measurements (play.json): per tag the tip-to-screw distance, the tool axis
against the door normal, the hand's roll about the door normal, and the arm's bones.
  python Tools/Unreal/doortool/read_measure.py Saved/QA/run_<stamp>/DTS/play.json"""
import json
import math
import sys

log = json.load(open(sys.argv[1]))['log']
seat = None
for e in log:
    k = e.get('kind', '')
    if k.startswith('doortool_') and k != 'doortool_measure':
        print(k, {a: b for a, b in e.items() if a not in ('t', 'kind')})
    if k != 'doortool_measure':
        continue
    y = e['hand_axes']['y']  # the hand's roll about the door normal (X): its Y axis in the door's YZ plane
    roll = math.degrees(math.atan2(y[2], y[1]))
    if e['tag'] == 'seat0':
        seat = roll
    b = e['bones']
    print(f"{e['tag']:12s} i{e['index']} ang {e['angle']:6.1f} tip-screw {e['tip_to_screw_cm']:5.2f} cm  axis {e['axis_off_normal_deg']:5.1f} deg"
          f"  roll {roll:7.1f} ({(roll - seat) if seat is not None else 0:+6.1f})  hand {b['hand_r']}  elbow {b['lowerarm_r']}"
          f"  shoulder {b['upperarm_r']}  head {b['head']}  cam {e['camera']} fov {e['fov']}")
