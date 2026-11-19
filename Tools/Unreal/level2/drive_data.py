"""Drive constants. Coordinates traced from queen_600m ground image and building footprints, in UE centimetres."""
from math import atan2, cos, degrees, dist, floor, pi, sin, tan

ROOT = '/Game/FoA/Level2/Drive'
MAP = '/Game/FoA/Level2/Maps/L_L2_DriveProto'
CITY = '/Game/FoA/Level2/Maps/L_L2_CityTest'
CITY_EXPANDED = '/Game/FoA/Level2/Maps/L_L2_CityTest2'
BEDROOM = '/Game/FoA/Maps/L_Tutorial_Bedroom'
SOURCE = 'P:/FoA-Assets/level2/toronto/processed/queen_600m'
OWNER = 'l2_mech'
# Rails/QTE drive (2026-11-17): the design's 2.5 s telegraph; a generous 0.6 s brace window and 0.25 s late grace.
TELEGRAPH, BRACE_WINDOW, LATE_GRACE = 2.5, .6, .25
METEOR_COUNTS = (1, 4, 6)
CITY_FIRST_STRIKE = (1.8, 3.3)
CITY_STRIKE_INTERVAL = (3.5, 6.8)
CITY_STRIKE_DRIFT = 850.0
CITY_PRESSURE_RADIUS, CITY_PRESSURE_COST = 1100.0, 8
COSTS = (0, 0, 15, 40)
MAX_SPEED = 1200.0
VEHICLE_ROOT_LIFT = 65.0
IMPACT_ATTACK, IMPACT_DURATION, IMPACT_RADIUS = .25, 3.0, 1800.0
# The chase camera sees about 12 m up at the strike point: the meteor falls from there so it is seen arriving.
FALL_HEIGHT, FALL_CONTACT = 1000., 70.
STORM_MIN_RADIUS, STORM_MAX_RADIUS = 1400., 5200.
GOALS=((15535,80,2),(33200,8650,2),(45400,-6800,2))
SHELTERS=((23900,17800,2),(44700,-14900,2))
# One visual/gameplay wave contract; values are UE centimetres and seconds.
SHOCKWAVE_SPEED, SHOCKWAVE_DURATION, SHOCKWAVE_BAND = 1800., 3., 450.
SHOCKWAVE_FADE_IN, SHOCKWAVE_FADE_OUT = .12, .45
SHOCKWAVE_NUDGE_SPEED, SHOCKWAVE_NUDGE_DECEL = 60., 240.
# ---- Rails: the car follows the road on its own; the player only answers QTEs ----------------------------------
CAR_Z = 2.0  # actor height of the parked/active car (its body root sits 65 cm lower, on City_Ground)
LANE = 150.0  # drive right of the centreline; clear of Queen's eastbound traffic lane
CORNER_RADIUS = 900.0
CRUISE, CORNER_SPEED, ACCEL, BRAKE = 1100.0, 620.0, 520.0, 420.0
LOOKAHEAD = 1500.0  # corner speed reads the road this far ahead
MAX_STEP = .35  # rails have no collision to tunnel through: keep true speed even when the editor throttles to 3 fps
PROMPT_LEAD = 1.6  # the key prompt appears this long before impact; the ring meets the key when the window opens
DODGE_CLOSE = .2  # a dodge must be committed this long before impact
DODGE_SHIFT, DODGE_MISS_SHIFT, STRIKE_SIDE = 450.0, 130.0, 140.0
FIRST_STRIKE, STRIKE_GAP, END_CLEAR = 1.6, 6.4, 1800.0
KINDS = (0, 1, 0, -1, 1, 0, -1, 0, 1, -1)  # per strike in a leg: 0 brace (Space), 1 dodge right (D), -1 dodge left (A)
TEACH_DILATION, GOOD_DILATION, HIT_DILATION = .45, .3, .45
GOOD_SLOW, HIT_SLOW = .35, .3  # real seconds of the slow-motion beat after a result
RESULT_CLEAR = 1.5  # game seconds a result keeps the screen before another strike may arm
# Sand props: Lux3D (Aholo) splat objects form out of black sand ahead and crumble as the car passes. A pool of
# four, reused round robin along the rail; Low and Medium view distance use the two light ones only.
V = '/Game/FoA/VFX/Splats'
PROPS = (  # (mesh, material, scale): hourglass 8k splats, alarm clock 12k, the suit 9k, the Nightmare 40k
    (V + '/Meshes/SM_SandHourglass/SM_SandHourglass/StaticMeshes/SM_SandHourglass', V + '/Instances/MI_Sand_Hourglass', 4.2),
    (V + '/Meshes/SM_AlarmClockSplats/SM_AlarmClockSplats/StaticMeshes/SM_AlarmClockSplats', V + '/Instances/MI_Sand_AlarmClock', 4.0),
    (V + '/Meshes/SM_SandSuit/SM_SandSuit/StaticMeshes/SM_SandSuit', V + '/Instances/MI_Sand_Suit', 2.4),
    (V + '/Meshes/SM_TheNightMare', V + '/Instances/MI_Splat_NightMare', 1.5))
PROP_FIRST, PROP_GAP, PROP_AHEAD, PROP_PASS, PROP_GONE = 3200.0, 2900.0, 4200.0, 350.0, 2600.0
PROP_FORM, PROP_CRUMBLE, PROP_RIGHT, PROP_LEFT = 2.2, 1.6, 520.0, -620.0
LOW_PROPS, LOW_TRAFFIC = 2, 7
# Traffic: outer lanes only (450 cm right of each direction's centreline), so it never shares the rail's lane.
TRAFFIC_LANE = 450.0
# Centrelines. Queen from lidar sidewalk midlines; side streets from building-footprint midlines.
QUEEN = ((5000, 180), (15535, 150), (23800, 60), (30000, 25), (41000, 75), (54000, 60))


def queen_y(x):
    for (x0, y0), (x1, y1) in zip(QUEEN, QUEEN[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    raise ValueError(x)


NODES = {'S': (9000, queen_y(9000)), 'J0': (15535, queen_y(15535)), 'QA': (23800, queen_y(23800)),
         'QA2': (25650, queen_y(25650)), 'QC': (36800, queen_y(36800)), 'QB': (45300, queen_y(45300)),
         'B': (48844, queen_y(48844)), 'SA': (23800, 10600), 'J1': (33200, 9120), 'SB': (45450, 8850),
         'J2': (45160, -6800), 'N1': (25650, -13825), 'N2': (36150, -13850), 'N2b': (36450, -15800),
         'N3': (44600, -15650)}
EDGES = {  # undirected, with interior centreline points
    ('S', 'J0'): (), ('J0', 'QA'): (), ('QA', 'QA2'): (), ('QA2', 'QC'): ((30000, 25),), ('QC', 'QB'): ((41000, 75),),
    ('QB', 'B'): (), ('QA', 'SA'): (), ('SA', 'J1'): ((25000, 10335), (27000, 9786), (29000, 9434), (31000, 9230)),
    ('J1', 'SB'): ((37000, 9059), (41000, 8955)), ('SB', 'QB'): ((45450, 2000),), ('QB', 'J2'): ((45160, -2000),),
    ('QA2', 'N1'): ((25700, -2000), (25720, -8000)), ('N1', 'N2'): ((30000, -13850),),
    ('QC', 'N2'): ((36500, -2000), (36250, -8000), (36100, -13000)), ('N2', 'N2b'): (),
    ('N2b', 'N3'): ((40000, -15800),), ('J2', 'N3'): ((45100, -12000),)}
FROMS, TOS = ('S', 'J0', 'J1', 'J2'), ('J0', 'J1', 'J2', 'B')  # TOS index = the journey's Stop (3 = interview)
ROUTE_KEYS = (('S', 'J0'), ('J0', 'J1'), ('J0', 'J2'), ('J0', 'B'), ('J1', 'J0'), ('J1', 'J2'), ('J1', 'B'),
              ('J2', 'J0'), ('J2', 'J1'), ('J2', 'B'))
CANON_FROM = ('S', 'J0', 'J1', 'J1')  # where a leg starts when the car is placed without a parking spot
# The two legs every run drives take the long way round the blocks (the user: longer drives, not a slower car).
# The first leg stays short: the market is 65 m from the parked car and any detour would drive past it first.
ROUTE_VIA = {('J0', 'J1'): ('J0', 'QA', 'QA2', 'N1', 'N2', 'QC', 'QA2', 'QA', 'SA', 'J1'),
             ('J1', 'B'): ('J1', 'SB', 'QB', 'J2', 'N3', 'N2b', 'N2', 'QC', 'QB', 'B')}


def _edge(a, b):
    if (a, b) in EDGES:
        return [NODES[a], *EDGES[(a, b)], NODES[b]]
    return [NODES[a], *reversed(EDGES[(b, a)]), NODES[b]]


def _length(points):
    return sum(dist(p, q) for p, q in zip(points, points[1:]))


def node_path(a, b):
    """Shortest centreline polyline between two nodes (Dijkstra over EDGES)."""
    best, todo = {a: (0, [a])}, [a]
    while todo:
        todo.sort(key=lambda n: best[n][0])
        here = todo.pop(0)
        for (p, q) in EDGES:
            for u, v in ((p, q), (q, p)):
                if u != here:
                    continue
                cost = best[here][0] + _length(_edge(u, v))
                if v not in best or cost < best[v][0]:
                    best[v] = (cost, best[here][1] + [v]); todo.append(v)
    names = best[b][1]
    points = [NODES[a]]
    for u, v in zip(names, names[1:]):
        points += _edge(u, v)[1:]
    return names, points


def _fillet(points, radius=CORNER_RADIUS, step=5.0):
    """Round every turn with an arc (sampled every `step` degrees), limited by the neighbouring segment lengths."""
    out = [points[0]]
    for i in range(1, len(points) - 1):
        p0, p1, p2 = points[i - 1], points[i], points[i + 1]
        a1, a2 = atan2(p1[1] - p0[1], p1[0] - p0[0]), atan2(p2[1] - p1[1], p2[0] - p1[0])
        turn = (a2 - a1 + pi) % (2 * pi) - pi
        if abs(degrees(turn)) < 4:
            out.append(p1); continue
        half = max(abs(tan(turn / 2)), 1e-6)
        r = min(radius, .45 * dist(p0, p1) / half, .45 * dist(p1, p2) / half)
        cut = r * half
        start = (p1[0] - cos(a1) * cut, p1[1] - sin(a1) * cut)
        side = 1 if turn > 0 else -1  # UE Y is right: a positive turn is a right turn
        centre = (start[0] - sin(a1) * r * side, start[1] + cos(a1) * r * side)
        steps = max(2, int(abs(degrees(turn)) / step))
        for k in range(steps + 1):
            h = a1 + turn * k / steps
            out.append((centre[0] + sin(h) * r * side, centre[1] - cos(h) * r * side))
    out.append(points[-1])
    return out


def _offset(points, lane=LANE):
    """Shift a polyline to the right of travel (UE right of yaw h is (-sin h, cos h))."""
    out = []
    for i, p in enumerate(points):
        a = points[max(i - 1, 0)]; b = points[min(i + 1, len(points) - 1)]
        h = atan2(b[1] - a[1], b[0] - a[0])
        out.append((round(p[0] - sin(h) * lane, 1), round(p[1] + cos(h) * lane, 1)))
    return out


def route(a, b):
    via = ROUTE_VIA.get((a, b))
    points = node_path(a, b)[1] if via is None else [NODES[a]]
    for u, v in zip(via or (), (via or ())[1:]):
        points += _edge(u, v)[1:]
    return [(x, y, CAR_Z) for x, y in _offset(_fillet(points))]


def route_index(frm, to):
    """Rail index for a (from node, Stop) pair; the same node falls through to the canonical next stop."""
    key = (FROMS[frm], TOS[to])
    return ROUTE_KEYS.index(key) if key in ROUTE_KEYS else -1


def strikes(length):
    """Strikes that fit a route: after the start, spaced, and clear of the stop."""
    usable = length / CRUISE - FIRST_STRIKE - TELEGRAPH - END_CLEAR / CRUISE
    return max(1, min(len(KINDS), 1 + floor(usable / STRIKE_GAP)))


def _lane(a, b, side=TRAFFIC_LANE):
    """A straight traffic lane from a to b, shifted right of its own direction."""
    h = atan2(b[1] - a[1], b[0] - a[0])
    off = (-sin(h) * side, cos(h) * side)
    return (round(a[0] + off[0]), round(a[1] + off[1])), (round(b[0] + off[0]), round(b[1] + off[1]))


_Q = [(6500, queen_y(6500)), (53500, queen_y(53500))]
_S = [(31000, 9230), (57500, 8590)]
_B = [(45450, 8500), (45100, -12000)]
LANES = [_lane(*_Q), _lane(*_Q[::-1]), _lane(*_S), _lane(*_S[::-1]), _lane(*_B), _lane(*_B[::-1])]
# (lane, speed cm/s, start cm). Interleaved so the Low tier's first seven still cover every street.
TRAFFIC = ((0, 640, 9000), (1, 700, 30000), (2, 560, 4000), (3, 600, 15000), (4, 520, 6000), (5, 540, 9000),
           (0, 720, 27000), (1, 600, 7000), (2, 620, 18000), (3, 520, 2000), (4, 600, 15000), (5, 480, 1000),
           (0, 560, 41000), (1, 660, 19000))
# The free drive's five Queen cars keep their box bodies; the rest are mesh-only components.
TRAFFIC_NAMES = ('TrafficEastACollision', 'TrafficWestACollision', 'TrafficEastBCollision', 'TrafficWestBCollision',
                 'TrafficEastCCollision') + tuple(f'Traffic{i}' for i in range(5, len(TRAFFIC)))


# Rail<i> on BP_L2RoadNetwork is ROUTE_KEYS[i]: world space (the network spawns at the origin), actor height.
RAILS = [route(a, b) for a, b in ROUTE_KEYS]
ROUTE_LENGTHS = [_length(r) for r in RAILS]
ROUTE_STRIKES = [1 if key == ('S', 'J0') else strikes(n) for key, n in zip(ROUTE_KEYS, ROUTE_LENGTHS)]


def impact_cost(inside, brace_age):
    if not inside:
        return 0
    if TELEGRAPH - BRACE_WINDOW <= brace_age < TELEGRAPH:
        return 0
    return 15 if TELEGRAPH <= brace_age <= TELEGRAPH + LATE_GRACE else 40


def impact_progress(age):
    return max(0, min(1, age/IMPACT_ATTACK, (IMPACT_DURATION-age)/(IMPACT_DURATION-IMPACT_ATTACK)))


# ---- Round 3 (coordinator 11-18 03:2x): perfect brace, set-piece, traffic to sand, streak mood ------------------------
PERFECT = .2                       # a brace in the last 0.2 s of the 0.6 s window is perfect: the near miss
PERFECT_DILATION, PERFECT_SLOW = .15, .9
# One set-piece per long leg, on a straight (a 120 m scan for the least heading change): the Nightmare rises out of
# the road 90 m ahead, rears over it, and the car drives through it as it bursts back into sand.
SET_PIECE_AT = {1: 42500.0, 6: 28000.0}             # rail index: distance along the rail (cm)
SET_PIECE_RISE, SET_PIECE_BURST, SET_PIECE_GONE = 9000.0, 1200.0, 3000.0
SET_PIECE_SCALE, SET_PIECE_FORM, SET_PIECE_CRUMBLE = 6.0, 2.4, 1.0
SET_PIECE_CLEAR = (12000.0, 2500.0)                 # no strike arms from 120 m before to 25 m after it
TRAFFIC_SAND = 1000.0              # a traffic car within 10 m of the player bursts into sand; it returns at its lane start
MOOD_CLEAN, MOOD_PERFECT, MOOD_LATE, MOOD_HIT = .34, .5, -.4, -.8   # the streak: +clean, -miss, clamped to [-1, 1]
MUSIC_SWELL = .3                   # music volume multiplier 1 + 0.3 x mood (calm swells, storm dips)


# ---- Free steering on the route (coordinator 11-18 10:4x: the user liked the free-form car, with restrictions) --------
# The car cruises along the rail by itself; A/D, the arrows, the shoulders and the left stick slide it sideways inside a
# corridor around the rail. Soft walls near the edges and a gentle pull to the rail when the stick is let go; no
# collision (never stuck on a facade) and the rail is the only road (never lost). The worst rail point is 5.15 m from a
# wall, so 3.2 m leaves a metre for the car's half width. S or the left trigger brakes (optional).
CORRIDOR, STEER_SPEED, STEER_RESPONSE, CENTER_PULL = 320.0, 600.0, 6.0, .3
WALL_SOFT, WALL_SPRING, STEER_YAW_MAX, BRAKE_FACTOR = .75, 6.0, 22.0, .45
DODGE_HIT, DODGE_SIDE_MIN = 190.0, 20.0   # a dodge strike lands where the car is; more than 2.6 m away at impact clears it;
# it asks for the side with more room (its planned side only when the car is within 0.2 m of the rail)


# ---- Cars and hiring signs (coordinator 11-18 13:1x, the user: "these things must look more AAA") ------------------
LUX_DRIVE = 'P:/FoA-Assets/lux3d/drive_cars_signs'      # six paid G1 generations (docs/lux3d-drive-prompts.md)
CARS_DIR, SIGNS_DIR = ROOT + '/Cars', ROOT + '/Signs'
CAR_LENGTH = {'player_sedan': 460.0, 'traffic_hatchback': 390.0, 'traffic_van': 470.0}   # cm, nose to tail
TRAFFIC_MODELS = ('traffic_hatchback', 'traffic_van', 'player_sedan')  # round robin over the 14 traffic cars
# Each stop's sign stands on the pavement beside the road, 6 to 10 m off the route and clear of the walls (offline
# scan of the surveyed footprints), faces the main approach and turns 20 degrees toward the road:
# (x, y, approach heading, side of the road: 1 right of travel / -1 left, model), one per job_route.DESTINATIONS
SIGN_SPOTS = ((15835.0, 1080.0, 0.0, 1, 'sign_billboard'), (33500.0, 9900.0, 0.0, 1, 'sign_pylon'),
              (44400.0, -7100.0, -90.0, -1, 'sign_billboard'), (49144.0, -510.0, 0.0, -1, 'sign_marquee'))
SIGN_HEIGHT = {'sign_pylon': 650.0, 'sign_billboard': 600.0, 'sign_marquee': 320.0}  # cm, the whole structure
SIGN_TURN = 20.0


def sign_yaw(heading, side):
    """The sign's facing: back toward the approaching car, turned toward the road (the road lies opposite its side)."""
    return heading + 180.0 + SIGN_TURN * side


# ---- City sectors along the rails: rolling preload (coordinator, 11-18 02:10) -------------------------------------
# A sector is pinned loaded while the car is within ROLL_AHEAD before the first rail point that passes within
# SPAN_RADIUS of its cell, until ROLL_BEHIND after the last one (about 150 m behind). SPAN_RADIUS is the sectors' own
# 90 m load radius plus 10 m, so the camera rule never loads a sector the rolling preload has not already asked for.
CELL_CM, CITY_SIDE, CITY_Y0 = 5000.0, 12, -30000.0  # city_streaming.py's grid: cell (x, y) is index x * 12 + y
SPAN_RADIUS, ROLL_AHEAD, ROLL_BEHIND, ROLL_STEP = 10000.0, 25000.0, 5000.0, 2500.0


def _box(x, y, cell):
    cx, cy = (cell // CITY_SIDE + .5) * CELL_CM, CITY_Y0 + (cell % CITY_SIDE + .5) * CELL_CM
    return dist((0, 0), (max(0, abs(x - cx) - CELL_CM / 2), max(0, abs(y - cy) - CELL_CM / 2)))


def sector_spans(rail, radius=SPAN_RADIUS, step=100.0):
    """{cell: [first, last]} distances along the rail (cm) where it passes within `radius` of the cell's box."""
    spans, along, reach = {}, 0.0, int(radius // CELL_CM) + 1
    samples = []
    for p, q in zip(rail, rail[1:]):
        seg = dist(p[:2], q[:2])
        samples += [(p[0] + (q[0] - p[0]) * t / seg, p[1] + (q[1] - p[1]) * t / seg, along + t)
                    for t in [k * step for k in range(int(seg // step) + 1)]]
        along += seg
    samples.append((rail[-1][0], rail[-1][1], along))
    for x, y, s in samples:
        gx, gy = int(x // CELL_CM), int((y - CITY_Y0) // CELL_CM)
        for cx in range(max(0, gx - reach), min(CITY_SIDE, gx + reach + 1)):
            for cy in range(max(0, gy - reach), min(CITY_SIDE, gy + reach + 1)):
                cell = cx * CITY_SIDE + cy
                if _box(x, y, cell) <= radius:
                    span = spans.setdefault(cell, [s, s])
                    span[1] = s
    return spans


_SPANS = [sector_spans(r) for r in RAILS]


def span_table():
    """Every rail's spans as one string for BP_L2Car.SpanTable: 8 characters per (rail, cell) at (rail * 144 + cell)
    * 8, first and last in whole metres (rounded outward), 4 digits each; '99990000' = the rail never passes the cell.
    shortcut: a string, because Hayba batches cannot wire Array_Get's wildcard pins; use a float array once they can."""
    cells = [_SPANS[r].get(c) for r in range(len(RAILS)) for c in range(CITY_SIDE ** 2)]
    return ''.join('99990000' if s is None else f'{floor(s[0] / 100):04d}{-floor(-s[1] / 100):04d}' for s in cells)


SPAN_TABLE = span_table()


def pinned(rail, distance):
    """Cells the rolling preload holds loaded with the car at `distance` cm along `rail`: PreloadCity's rule, read
    from the same table the Blueprint reads."""
    out = []
    for c in range(CITY_SIDE ** 2):
        at = (rail * CITY_SIDE ** 2 + c) * 8
        first, last = float(SPAN_TABLE[at:at + 4]) * 100, float(SPAN_TABLE[at + 4:at + 8]) * 100
        if first - ROLL_AHEAD <= distance <= last + ROLL_BEHIND:
            out.append(c)
    return out


def selftest():
    # Rolling preload: every sector the camera rule would load (90 m around the car) is already pinned, and it was
    # pinned at least (ROLL_AHEAD - SPAN_RADIUS) before the car came within reach of it.
    for r, rail in enumerate(RAILS):
        along = 0.0
        for p, q in zip(rail, rail[1:]):
            seg = dist(p[:2], q[:2])
            for t in range(0, int(seg), 500):
                x, y = p[0] + (q[0] - p[0]) * t / seg, p[1] + (q[1] - p[1]) * t / seg
                now = set(pinned(r, along + t))
                near = {c for c in range(CITY_SIDE ** 2) if _box(x, y, c) < 9000}
                assert near <= now, (r, along + t, near - now)
            along += seg
        assert len(SPAN_TABLE) == len(RAILS) * CITY_SIDE ** 2 * 8 and SPAN_TABLE.isdigit()
        assert pinned(r, -ROLL_AHEAD - 1) == [] and set(pinned(r, 0)) >= {c for c in _SPANS[r] if _SPANS[r][c][0] <= ROLL_AHEAD}
    for r, at in SET_PIECE_AT.items():  # a set-piece sits on a long leg, clear of its start and its stop
        assert ROUTE_LENGTHS[r] > 60000 and SET_PIECE_RISE + 5000 < at < ROUTE_LENGTHS[r] - END_CLEAR - SET_PIECE_GONE
    assert PERFECT < BRACE_WINDOW and PERFECT_DILATION < GOOD_DILATION and TRAFFIC_SAND < 1200
    # the side a dodge asks for always has room, even where the soft wall settles a released car (75% of the corridor)
    assert CORRIDOR + 90 < 515 and DODGE_HIT < CORRIDOR * WALL_SOFT - DODGE_SIDE_MIN
    assert STEER_SPEED * (PROMPT_LEAD - .4) > DODGE_HIT, 'a dodge started late in the prompt still clears'
    assert [impact_cost(*x) for x in [(False, -1), (True, 2.2), (True, 2.55), (True, -1)]] == list(COSTS)
    assert impact_cost(True, 1.899) == 40 and impact_cost(True, 1.9) == 0
    assert impact_cost(True, 2.5) == 15 and impact_cost(True, 2.751) == 40
    composure = 100
    trace = []
    for cost in COSTS:
        composure = max(0, composure - cost)
        trace.append(composure)
    assert trace == [100, 100, 85, 45]
    assert max(0, 100 - 3 * 40) == 0  # three unbraced hits end a leg; one (the teaching leg) never does
    assert ROUTE_STRIKES[ROUTE_KEYS.index(('S', 'J0'))] == 1 and all(1 <= n <= len(KINDS) for n in ROUTE_STRIKES)
    assert KINDS[0] == 0 and all(k in (-1, 0, 1) for k in KINDS)
    for (a, b), rail, length in zip(ROUTE_KEYS, RAILS, ROUTE_LENGTHS):
        assert abs(dist(rail[0][:2], NODES[a]) - LANE) < 1 and abs(dist(rail[-1][:2], NODES[b]) - LANE) < 1, (a, b)
        steps = [dist(p[:2], q[:2]) for p, q in zip(rail, rail[1:])]
        assert min(steps) > 5, (a, b, 'duplicate rail points')
        heads = [atan2(q[1] - p[1], q[0] - p[0]) for p, q in zip(rail, rail[1:])]
        bends = [abs(degrees((h2 - h1 + pi) % (2 * pi) - pi)) for h1, h2 in zip(heads, heads[1:])]
        assert max(bends, default=0) < 8, (a, b, 'sharp rail kink', max(bends))
        assert 5000 < length < 100000, (a, b, length)
    for f in range(len(FROMS)):
        for t in range(len(TOS)):
            assert route_index(f, t) >= 0 or FROMS[f] == TOS[t] or FROMS[f] == 'S', (f, t)
    assert len(TRAFFIC) == len(TRAFFIC_NAMES) and all(dist(*LANES[i]) > 20000 for i, *_ in TRAFFIC)
    assert all(0 <= start < dist(*LANES[i]) for i, _, start in TRAFFIC) and LOW_TRAFFIC <= len(TRAFFIC)
    assert PROP_GAP * 4 > PROP_AHEAD + PROP_GONE, 'a pooled prop is gone before its slot is reused'
    # A strike's prompt, window and grace finish before the next strike is armed.
    assert PROMPT_LEAD > BRACE_WINDOW and TELEGRAPH + LATE_GRACE < STRIKE_GAP and DODGE_SHIFT - STRIKE_SIDE > 240
    print('drive_data selftest passed: costs, clamp,', len(RAILS), 'rails', [round(n / 100) for n in ROUTE_LENGTHS],
          'm, strikes', ROUTE_STRIKES)


if __name__ == '__main__':
    selftest()
