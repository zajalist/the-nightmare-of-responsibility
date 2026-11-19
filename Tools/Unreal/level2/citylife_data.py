"""City life (Level 2 drive): constants and the offline pavement table for BP_L2CityLife.

Ground things (walkers, rolling chairs) stand on a pavement beside the car's rail. LANES is one fixed-width string:
rail i owns characters [i*BUCKETS, (i+1)*BUCKETS), one per 10 m of rail. 'B' both pavements are clear, 'L' only the
left, 'R' only the right, '0' neither (a wall within reach, a corner, or within reach of a stop). The Blueprint reads
it with GetSubstring(LANES, RailIndex*BUCKETS + floor(Distance/1000), 1), like the drive's SpanTable.
  python -B Tools/Unreal/level2/citylife_data.py   # selftest + table summary
"""
import json
from math import atan2, degrees, dist
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import drive_data as D

ROOT = '/Game/FoA/Level2/CityLife'
BP = ROOT + '/BP_L2CityLife'
BUCKET = 1000.0                   # cm of rail per table character
BUCKETS = 80                      # the longest rail is 795 m
LEFT, RIGHT = -950.0, 620.0       # pavement lateral from the rail (the rail runs 150 cm right of the centreline)
BODY = 100.0                      # a walker's half width plus margin to a wall
REACH = 2000.0                    # a walker covers about this much pavement before the car passes
STOP_CLEAR = (3500.0, 4000.0)     # nothing within 35 m of the leg's start or 40 m of its stop (signs, the stop scene)
STRAIGHT = 10.0                   # max heading change (deg) over +-REACH for a straight pavement
AHEAD = (5500.0, 11500.0)         # a pooled thing re-forms this far ahead of the car
GAP_GROUND = (600.0, 1200.0)      # each new ground thing forms this far past the previous one (no crowds in one spot)
GAP_AIR = (1200.0, 2500.0)        # and each new flyer this far past the previous flyer
STALE = 5000.0                    # a marker this far past the window is from another leg: start again at the window
BEHIND, FAR = 3000.0, 16000.0     # ...once it is this far behind the car, or this far from it
CRUMBLE = 800.0                   # ground things crumble into sand as the car draws within this of them
GROUND_Z = -65.0                  # the road under the rail (the rail is at the car's actor height)
STEP = .25                        # timer period (s)
# Walkers, in pairs: commuter Walk_Formal_Loop, commuter Jog_Fwd_Loop (late), faceless applicant Zombie_Walk_Fwd_Loop,
# faceless applicant Walk_Loop (Lux3D auto-rig + retarget, in-place clips; citylife_templates.WALKERS)
WALK_SPEEDS = (140.0, 330.0, 70.0, 130.0)   # cm/s, matched by eye to each clip's stride
WALK_FWD = (0.0, 1.0, 0.0)        # the rigged mesh faces its local +Y (Mixamo-style import)
WALK_YAW = -90.0                  # so the component turns -90 from the heading it walks
# Flyers over the road: (lateral from the rail, height above the road) per flock; flock 0-1 crows, 2 resume pages,
# 3 briefcases, 4 umbrellas. Lowest flyer stays 5 m up, clear of the car and its chase camera.
# (CL run 14:15: at 11-15 m the flocks read as specks against the black sky; lower and over the pavements they stand
# against the bright facades, still above the chase camera)
FLOCK_PLACES = ((-750.0, 750.0), (450.0, 900.0), (-650.0, 600.0), (-150.0, 650.0), (300.0, 550.0))
PHONE_PLACE = (-500.0, 600.0)
CULL = 12000.0                    # max draw distance of every pooled thing (cm)
# Instanced flocks: (mesh name, count, ring radius, height spread, scale, yaw of the mesh's nose, bank, tumble, spin deg/s)
# Lux3D orientation (glb_preview): the crow's head is +Y (wingspan 1.9 m along X); briefcase long side X; umbrella dome +Y
FLOCKS = (('Crow', 6, 550.0, 250.0, .95, -90.0, 18.0, False, 34.0),
          ('Crow', 7, 500.0, 300.0, .85, -90.0, 14.0, False, -26.0),
          ('ResumePage', 9, 260.0, 450.0, 2.6, 0.0, 0.0, True, 120.0),
          ('Briefcase', 5, 520.0, 220.0, 2.2, 0.0, 10.0, False, 38.0),
          ('Umbrella', 4, 380.0, 120.0, 1.3, 0.0, 80.0, False, 16.0))
PHONE = ('DeskPhone', 6.0, 22.0)  # mesh, scale (a 1.5 m phone), spin deg/s
CHAIR = ('OfficeChair', 1.0, 55.0)
CHAIR_LIFT = 52.0                 # the Lux3D chair is centred on its origin (105 cm tall): lift it onto the road
# Walker i: (character, clip); the retarget FBX meshes are centred on their hips (feet 79 cm below the origin at 180 cm),
# so each stands HEIGHTS/2 above the road once scaled to its height (citylife_facing.py measured foot, toe and head)
WALKERS = [('Commuter', 'Walk_Formal_Loop'), ('Commuter', 'Walk_Formal_Loop'), ('Commuter', 'Jog_Fwd_Loop'),
           ('Commuter', 'Jog_Fwd_Loop'), ('Faceless', 'Zombie_Walk_Fwd_Loop'), ('Faceless', 'Zombie_Walk_Fwd_Loop'),
           ('Faceless', 'Walk_Loop'), ('Faceless', 'Walk_Loop')]
HEIGHTS = {'Commuter': 178.0, 'Faceless': 192.0}


def flock_instances(count, radius, spread, scale, nose, bank, tumble, seed):
    """Local transforms (x, y, z, pitch, yaw, roll, scale) on a ring, noses along the circling direction."""
    import random
    rnd = random.Random(seed)
    out = []
    for i in range(count):
        a = 360.0 * i / count + rnd.uniform(-12, 12)
        r = radius * rnd.uniform(.75, 1.1)
        from math import cos, radians, sin
        x, y = r * cos(radians(a)), r * sin(radians(a))
        z = rnd.uniform(-spread / 2, spread / 2)
        if tumble:
            pitch, yaw, roll = rnd.uniform(-70, 70), rnd.uniform(0, 360), rnd.uniform(-70, 70)
        else:
            pitch, yaw, roll = rnd.uniform(-6, 6), a + 90.0 + nose, bank + rnd.uniform(-5, 5)
        out.append((round(x, 1), round(y, 1), round(z, 1), round(pitch, 1), round(yaw, 1), round(roll, 1),
                    round(scale * rnd.uniform(.85, 1.15), 2)))
    return out


def _walls():
    source = Path(D.SOURCE)
    corr = json.loads((source / 'corridor.json').read_text())
    (ox, oy), (ax, ay), (lx, ly) = corr['origin_utm_m'], corr['along_utm'], corr['left_utm']
    walls = []
    for record in json.loads((source / 'buildings.json').read_text())['records']:
        geometry = json.loads(record['geometry'])
        rings = [geometry['coordinates'][0]] if geometry['type'] == 'Polygon' else [p[0] for p in geometry['coordinates']]
        for ring in rings:
            pts = [(((e - ox) * ax + (n - oy) * ay) * 100, -((e - ox) * lx + (n - oy) * ly) * 100) for e, n, *_ in ring]
            walls += list(zip(pts, pts[1:]))
    return walls


def _near_wall(p, walls, radius):
    for (x1, y1), (x2, y2) in walls:
        if min(x1, x2) - radius > p[0] or max(x1, x2) + radius < p[0] or min(y1, y2) - radius > p[1] or max(y1, y2) + radius < p[1]:
            continue
        dx, dy = x2 - x1, y2 - y1
        t = max(0, min(1, ((p[0] - x1) * dx + (p[1] - y1) * dy) / (dx * dx + dy * dy or 1)))
        if dist(p, (x1 + t * dx, y1 + t * dy)) < radius:
            return True
    return False


def _sample(rail, s):
    """Point and heading (rad) at arc length s along a polyline rail."""
    acc = 0.0
    for p, q in zip(rail, rail[1:]):
        seg = dist(p[:2], q[:2])
        if acc + seg >= s or q is rail[-1]:
            t = 0 if seg == 0 else min(1, max(0, (s - acc) / seg))
            return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t), atan2(q[1] - p[1], q[0] - p[0])
        acc += seg


def _turn(a, b):
    return abs(degrees((b - a + 3.141592653589793) % 6.283185307179586 - 3.141592653589793))


def bucket_flag(rail, length, k, walls):
    mid = (k + .5) * BUCKET
    if mid < STOP_CLEAR[0] or mid > length - STOP_CLEAR[1]:
        return '0'
    heads = [_sample(rail, max(0, min(length, mid + o)))[1] for o in (-REACH, -REACH / 2, 0, REACH / 2, REACH)]
    if max(_turn(heads[0], h) for h in heads) > STRAIGHT:
        return '0'
    ok = []
    for lateral in (LEFT, RIGHT):
        clear = True
        for o in range(int(k * BUCKET - REACH), int((k + 1) * BUCKET + REACH) + 1, 250):
            (x, y), h = _sample(rail, max(0, min(length, o)))
            from math import cos, sin
            spot = (x - sin(h) * lateral, y + cos(h) * lateral)
            if _near_wall(spot, walls, BODY):
                clear = False
                break
        ok.append(clear)
    return {(True, True): 'B', (True, False): 'L', (False, True): 'R'}.get(tuple(ok), '0')


def lanes(walls=None):
    walls = _walls() if walls is None else walls
    out = []
    for rail, length in zip(D.RAILS, D.ROUTE_LENGTHS):
        n = min(BUCKETS, int(length // BUCKET) + 1)
        row = ''.join(bucket_flag(rail, length, k, walls) for k in range(n))
        out.append(row.ljust(BUCKETS, '0'))
    return ''.join(out)


def selftest():
    assert max(D.ROUTE_LENGTHS) < BUCKETS * BUCKET, 'a rail outgrew the table'
    # a corridor with one wall: a pavement spot 50 cm from it is not clear, one 3 m away is
    wall = [((0, 1000), (100000, 1000))]
    assert _near_wall((500, 950), wall, BODY) and not _near_wall((500, 700), wall, BODY)
    straight = [(0, 0, 2), (100000, 0, 2)]
    # walls 10 m right of a straight rail: right pavement (620 + 100 reach) clear, left clear too
    assert bucket_flag(straight, 100000, 50, [((0, 1000), (100000, 1000))]) == 'B'
    # walls 6.5 m right: the right pavement (620) is within BODY of it, so only the left
    assert bucket_flag(straight, 100000, 50, [((0, 650), (100000, 650))]) == 'L'
    # the start and the stop are never used
    assert bucket_flag(straight, 100000, 0, []) == '0' and bucket_flag(straight, 100000, 99, []) == '0'
    # a right-angle corner inside the reach is never used
    corner = [(0, 0, 2), (50000, 0, 2), (50000, 50000, 2)]
    assert bucket_flag(corner, 100000, 49, []) == '0'
    assert LEFT <= -(320 + 150 + 100) and RIGHT >= 320 + 150 + 100, 'ground things keep 1.5 m clear of the car corridor'
    print('citylife_data selftest OK')


if __name__ == '__main__':
    selftest()
    table = lanes()
    assert len(table) == len(D.RAILS) * BUCKETS
    for i, key in enumerate(D.ROUTE_KEYS):
        row = table[i * BUCKETS:(i + 1) * BUCKETS]
        used = int(D.ROUTE_LENGTHS[i] // BUCKET) + 1
        print(i, key, f'{D.ROUTE_LENGTHS[i] / 100:.0f} m', row[:used],
              f'usable {sum(c != "0" for c in row[:used])}/{used}')
    Path(__file__).with_name('citylife_lanes.txt').write_text(table)
