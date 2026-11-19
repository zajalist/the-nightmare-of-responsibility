"""Rails + QTE drive (2026-11-17, drive lane). The car follows the road by itself; the player answers a few strikes:
Space to brace, A or D to dodge. Native Blueprint graphs through Hayba; one lease per step.

  python -B Tools/Unreal/level2/drive_rails.py setup|roads|widget|input|graphs|<BP>.<Function>
Composure costs, the road restart hand-off and EMPLOYABILITY are unchanged (design.md sections 4 and 6).
"""
from math import atan2, degrees, dist
import os
from pathlib import Path
import sys

sys.path[:0] = [str(Path(__file__).parent), 'P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import build_drive as b
import drive_data as D
from job_route import BOARDS, NAMES
from job_hunt_data import BOSS_MINIMUM

CAR, MET, HUD, ROAD, G, K, A, SC, GS, SL, cls = b.CAR, b.MET, b.HUD, b.ROAD, b.G, b.K, b.A, b.SC, b.GS, b.SL, b.cls
SP = '/Script/Engine.SplineComponent:'
W = '/Script/UMG.Widget:'
JOURNEY = b.JOURNEY
DREAM_MPC = '/Game/FoA/PostProcess/MPC_Dream.MPC_Dream'
SFX = '/Game/FoA/Audio/SFX/'
SOUNDS = dict(clash=SFX + 'Battle/SFX_Battle_SwordClash_01.SFX_Battle_SwordClash_01',
              whoosh=SFX + 'Battle/SFX_Battle_FabricWhoosh_01.SFX_Battle_FabricWhoosh_01',
              hit=SFX + 'Battle/SFX_Battle_PlayerHit_01.SFX_Battle_PlayerHit_01',
              sand=SFX + 'Sand/SFX_Sand_Burst_01.SFX_Sand_Burst_01')
# A dodge strike asks for a direction to steer, not a key: the arrow (A/D, the arrows, the stick and the shoulders all steer)
KEYS = {0: 'Space', 1: '\u2192', -1: '\u2190'}
PAD_GLYPHS = {0: 'A', 1: '\u2192', -1: '\u2190'}  # IMC_L2Drive: FaceButton_Bottom braces
PAD_KEYS = {0: 'Gamepad_FaceButton_Bottom', 1: 'Gamepad_RightShoulder', -1: 'Gamepad_LeftShoulder'}

CAR_VARS = [('RouteReady', 'bool', 'false'), ('RouteLength', 'float', '0'), ('Target', 'int', '0'),
            ('ArriveAt', 'float', '-1'), ('MeteorIndex', 'int', '0'), ('Teaching', 'bool', 'false'),
            ('TaughtBrace', 'bool', 'false'), ('TaughtDodge', 'bool', 'false'),
            ('DodgeOffset', 'float', '0'), ('DodgeSide', 'float', '0'), ('DodgeUntil', 'float', '-10'),
            ('SlowUntil', 'float', '-10'), ('SlowScale', 'float', '1'), ('Shake', 'float', '0'), ('FovPunch', 'float', '0'),
            ('UsingPad', 'bool', 'false'), ('CityHold', 'bool', 'false'), ('CityReady', 'bool', 'false'),
            ('HoldUntil', 'float', '0'), ('NextRoll', 'float', '0'), ('PinChanged', 'bool', 'false'),
            ('HintAlpha', 'float', '0'), ('CutCamera', 'bool', 'false'),
            ('SetPieceAt', 'float', '-1'), ('SetPieceState', 'int', '0'), ('Mood', 'float', '0'),
            ('MoodShown', 'float', '0'), ('EngineSpeed', 'float', '0'),
            ('RoomAudio', 'object:' + '/Game/FoA/Audio/BP_RoomAudio.BP_RoomAudio_C', ''),
            ('Steer', 'float', '0'), ('Lateral', 'float', '0'), ('LatRate', 'float', '0'), ('StrikeLateral', 'float', '0'),
            ('Director', 'object:/Game/FoA/PostProcess/BP_DreamDirector.BP_DreamDirector_C', '')]
MET_VARS = [('Kind', 'int', '0'), ('Committed', 'bool', 'false'), ('Dodged', 'bool', 'false'),
            ('Result', 'int', '0'), ('ResultTime', 'float', '-10'), ('BraceAge', 'float', '-1')]
CAR_VARS += [('NextProp', 'int', '0'), ('PropAt', 'float', '0'), ('PropSide', 'float', '0'), ('PropSlot', 'int', '0'),
             ('PropSlots', 'int', '4')] + [(f'PropDist{i}', 'float', '0') for i in range(4)] + \
            [(f'PropState{i}', 'int', '0') for i in range(4)]
ROAD_VARS = [('TrafficLimit', 'int', str(len(D.TRAFFIC))), ('Wrapped', 'bool', 'false')] + [(f'TrafficPos{i}', 'float', str(start))
                                                              for i, (_, _, start) in enumerate(D.TRAFFIC)]
CAR_FUNCS = {'ChooseTarget': [], 'PickRoute': [], 'TrackStrike': [], 'UpdateFeel': [], 'AutoPark': [],
             'Feedback': [('Cost', 'int')], 'SpawnProp': [], 'FadeProp': [('Index', 'int')], 'ResetProps': [],
             'PreloadCity': [], 'CheckCity': [], 'RollCity': [], 'SetPiece': [], 'UpdateMood': [], 'FindRoomAudio': [],
             'ResetMood': [], 'Reward': [], 'ReadSteer': [], 'FindDirector': [], 'WarmImpact': [], 'DirLetterbox': [('Enabled', 'bool'), ('Seconds', 'float')],
             'DirGlitch': [('Strength', 'float'), ('Seconds', 'float')], 'DirStreak': [('Intensity', 'float'), ('Seconds', 'float')]}
ROAD_FUNCS = {'ApplyTrafficLimit': [], 'SignFlicker': [], 'TrafficSand': [('Car', 'object:/Script/Engine.SceneComponent'), ('Near', 'bool'),
                                                       ('Wrapped', 'bool'), ('Allowed', 'bool')]}
ROAD_COMPONENTS = [f'SandProp{i}' for i in range(4)] + [n for n in D.TRAFFIC_NAMES if not n.endswith('Collision')] + ['SetPiece']
PRIM = '/Script/Engine.PrimitiveComponent:'
PCM = '/Script/Engine.PlayerCameraManager:'
DIRECTOR = '/Game/FoA/PostProcess/BP_DreamDirector'   # the post lane's contract API: callers skip quietly if absent
ROOM_AUDIO = '/Game/FoA/Audio/BP_RoomAudio'
SANDFX = '/Game/FoA/VFX/Sand/BPL_SandFX'
HUD_FUNCS = {'SetQTE': [('Key', 'text'), ('Shown', 'bool'), ('Close', 'float'), ('Live', 'bool'),
                        ('Result', 'int'), ('ResultAge', 'float')]}


# ---- small graph helpers (house G batches; pure nodes re-evaluate per consumer, so read state back with getv) ------
GROUP_BOXES = False


class G(b.G):
    """The house batch plus title-only comment boxes per functional group: g.group('Speed') starts a box that holds
    every node made until the next group. Without groups the function gets the house's single box."""
    def group(self, title):
        groups = self.__dict__.setdefault('groups', [])
        if groups:
            groups[-1][2] = self.i
        groups.append([title, self.i, None])

    def comment(self, title, refs):
        # shortcut: bp_layout places nodes by exec flow, not by group, so per-group boxes overlapped (01:06 capture of
        # Move); one titled box per function until the layout tool can pack groups. Set GROUP_BOXES to try again.
        groups = self.__dict__.get('groups') if GROUP_BOXES else None
        if not groups or not title.endswith(' flow'):  # the house finish() asks for one box: give one per group
            return super().comment(title, refs)
        groups[-1][2] = groups[-1][2] or self.i
        for name, first, last in groups:
            mine = [r for r in refs if r.startswith('d') and r[1:].isdigit() and first < int(r[1:]) <= last]
            if mine:
                super().comment(name, mine)


def vec(g, p):
    return g.math('MakeVector', X=p[0], Y=p[1], Z=p[2] if len(p) > 2 else 0)


def set_on(g, target, path, name, value):
    r = g.ref(); g.set(r, name, g.i * 220, 0, cls(path)); g.put(r, 'self', target); g.put(r, name, value)
    g.chain(g.tail, r); g.tail = r


def pick(g, kind, values, index):
    """values[index] through a Select chain; kind is Int, Float, String or Vector."""
    out = values[0]
    for i, value in enumerate(values[1:], 1):
        out = g.math('Select' + kind, A=value, B=out, bPickA=g.math('EqualEqual_IntInt', A=index, B=i))
    return out


def both(g, *conds):
    out = conds[0]
    for c in conds[1:]:
        out = g.math('BooleanAND', A=out, B=c)
    return out


def either(g, *conds):
    out = conds[0]
    for c in conds[1:]:
        out = g.math('BooleanOR', A=out, B=c)
    return out


def NOT(g, c): return g.math('Not_PreBool', A=c)
def add(g, a, c): return g.math('Add_DoubleDouble', A=a, B=c)
def sub(g, a, c): return g.math('Subtract_DoubleDouble', A=a, B=c)
def mul(g, a, c): return g.math('Multiply_DoubleDouble', A=a, B=c)
def ge(g, a, c): return g.math('GreaterEqual_DoubleDouble', A=a, B=c)
def lt(g, a, c): return g.math('Less_DoubleDouble', A=a, B=c)
def ieq(g, a, c): return g.math('EqualEqual_IntInt', A=a, B=c)
def clamp01(g, v): return g.math('FClamp', Value=v, Min=0, Max=1)
def gate(g, cond): br = g.branch(cond); g.side(br); return br


def rail_at(g, what, distance):
    """Location, Rotation, RightVector or Direction of the active rail at a distance, world space."""
    return g.f(SP + f'Get{what}AtDistanceAlongSpline', self=g.getv('Rail'), Distance=distance, CoordinateSpace='World')


def met(g, name):
    return g.getv(name, g.getv('Meteor'), MET)


def sound(g, key, volume):
    g.do(GS + 'PlaySound2D', Sound=SOUNDS[key], VolumeMultiplier=volume)


# ---- BP_L2Car ---------------------------------------------------------------------------------------------------
def place_at_checkpoint():
    """A leg starts at its canonical start; a road retry starts where the failed leg started."""
    g = G(CAR, 'PlaceAtCheckpoint')
    retry = g.branch(both(g, g.getv('Failed'), g.f(SL + 'IsValid', Object=g.getv('Rail')))); g.side(retry)
    g.do(A + 'K2_SetActorLocationAndRotation', NewLocation=rail_at(g, 'Location', 0),
         NewRotation=rail_at(g, 'Rotation', 0), bSweep=False, bTeleport=True)
    g.side(retry, False)
    starts, yaws = [], []
    for frm, to in zip(D.CANON_FROM, D.TOS):
        rail = D.RAILS[D.ROUTE_KEYS.index((frm, to))]
        starts.append(vec(g, rail[0]))
        yaws.append(round(degrees(atan2(rail[1][1] - rail[0][1], rail[1][0] - rail[0][0])), 2))
    leg = g.getv('Leg')
    g.do(A + 'K2_SetActorLocationAndRotation', NewLocation=pick(g, 'Vector', starts, leg),
         NewRotation=g.math('MakeRotator', Yaw=pick(g, 'Float', yaws, leg)), bSweep=False, bTeleport=True)
    g.finish()


def choose_target():
    """Target = the journey's Stop; parked at that very stop (a job left without the hire), drive on to the next
    unedited job instead, or to the interview once EMPLOYABILITY allows it."""
    g = G(CAR, 'ChooseTarget')
    g.setv('Target', g.getv('Leg'))
    here = g.f(A + 'K2_GetActorLocation')
    near = [g.math('Less_DoubleDouble', A=g.math('Vector_Distance2D', V1=here, V2=vec(g, D.NODES[n])), B=1500)
            for n in ('J0', 'J1', 'J2')]
    leg = g.getv('Leg')
    same = either(g, *[both(g, near[i], ieq(g, leg, i)) for i in range(3)])
    gate(g, both(g, same, g.f(SL + 'IsValid', Object=g.getv('Journey'))))
    journey = g.cast(g.getv('Journey'), cls(JOURNEY), 'BP L2Journey')
    edited = [g.getv(f'Edited{i}', journey, JOURNEY) for i in range(3)]

    def is_edited(index):
        return either(g, *[both(g, ieq(g, index, i), edited[i]) for i in range(3)])
    first = g.math('Percent_IntInt', A=g.math('Add_IntInt', A=leg, B=1), B=3)
    second = g.math('Percent_IntInt', A=g.math('Add_IntInt', A=leg, B=2), B=3)
    boss = g.math('GreaterEqual_IntInt', A=g.getv('Employability'), B=BOSS_MINIMUM)
    fallback = g.math('SelectInt', A=3, B=first, bPickA=boss)
    target = g.math('SelectInt', A=second, B=fallback, bPickA=NOT(g, is_edited(second)))
    target = g.math('SelectInt', A=first, B=target, bPickA=NOT(g, is_edited(first)))
    g.setv('Target', target)
    g.finish()


def pick_route():
    """Once per leg, on the first drive tick: the nearest start node and the target choose the rail."""
    g = G(CAR, 'PickRoute')
    g.group('Choose the target')
    gate(g, NOT(g, g.getv('RouteReady')))
    g.own('ChooseTarget')
    here = g.f(A + 'K2_GetActorLocation')
    g.group('Nearest start')
    best = g.math('Vector_Distance2D', V1=here, V2=vec(g, D.NODES[D.FROMS[0]]))
    frm = 0
    for i, name in enumerate(D.FROMS[1:], 1):
        candidate = g.math('Vector_Distance2D', V1=here, V2=vec(g, D.NODES[name]))
        better = lt(g, candidate, best)
        best = g.math('SelectFloat', A=candidate, B=best, bPickA=better)
        frm = g.math('SelectInt', A=i, B=frm, bPickA=better)
    g.group('Choose the rail')
    key = g.math('Add_IntInt', A=g.math('Multiply_IntInt', A=frm, B=len(D.TOS)), B=g.getv('Target'))
    table = []
    for f in range(len(D.FROMS)):
        for t in range(len(D.TOS)):
            index = D.route_index(f, t)
            table.append(index if index >= 0 else D.ROUTE_KEYS.index((D.CANON_FROM[t], D.TOS[t])))
    index = pick(g, 'Int', table, key)
    g.own('SetRail', Index=index)
    g.setv('ArrivalJob', g.getv('Target'))
    # The card's title names where the rail goes: the route crosses several streets, not only Queen.
    g.setv('Place', g.f('/Script/Engine.KismetTextLibrary:Conv_StringToText', InString=pick(g, 'String', list(NAMES), g.getv('Target'))))
    g.setv('RouteLength', g.f(SP + 'GetSplineLength', self=g.getv('Rail')))
    g.setv('Destination', rail_at(g, 'Location', g.getv('RouteLength')))
    g.do(A + 'K2_SetActorLocationAndRotation', NewLocation=rail_at(g, 'Location', 0),
         NewRotation=rail_at(g, 'Rotation', 0), bSweep=False, bTeleport=True)
    g.group('Strikes for the leg')
    g.setv('MeteorsLeft', pick(g, 'Int', D.ROUTE_STRIKES, g.getv('RailIndex')))
    g.setv('MeteorIndex', 0)
    g.setv('NextMeteor', add(g, g.getv('Clock'), D.FIRST_STRIKE))
    g.setv('NearDestination', False)
    g.group('Stream the opening')
    g.own('PreloadCity')
    g.setv('CityHold', True)
    g.setv('HoldUntil', add(g, g.getv('Clock'), CITY_HOLD))
    g.own('WarmImpact')  # while the car waits for the city: nothing the impact needs is made at the impact
    road = g.getv('Road')
    g.group('Signs and boards')
    from free_drive import hide_sign
    hide_sign(g)
    eligible = g.math('GreaterEqual_IntInt', A=g.getv('Employability'), B=BOSS_MINIMUM)
    for component in BOARDS[-1]:
        g.do(SC + 'SetVisibility', self=g.getv(component, road, ROAD), bNewVisibility=eligible, bPropagateToChildren=False)
    g.setv('RouteReady', True)
    g.finish()


def start_leg():
    g = G(CAR, 'StartLeg')
    g.setv('Leg', g.arg('Index'))
    g.own('ResetShockwave')
    g.own('PlaceAtCheckpoint')  # before Failed clears: a road retry restarts the failed leg's own rail
    for name, value in [('Composure', 100), ('Failed', False), ('Arrived', False), ('Clock', 0), ('Speed', 0),
                        ('Distance', 0), ('Throttle', False), ('BrakeHeld', False), ('TurnQueued', False),
                        ('HitsResolved', 0), ('Cue', ''), ('CameraReady', False), ('RouteReady', False),
                        ('NearDestination', False), ('ArriveAt', -1), ('MeteorIndex', 0), ('MeteorsLeft', 0),
                        ('NextMeteor', 0), ('DodgeOffset', 0), ('DodgeUntil', -10), ('SlowUntil', -10),
                        ('Shake', 0), ('FovPunch', 0), ('Teaching', False)]:
        g.setv(name, value)
    g.setv('Place', 'Queen Street')
    g.do(cls(MET) + ':Hide', self=g.getv('Meteor'))
    g.do(cls(MET) + ':ResetImpact', self=g.getv('Meteor'))
    b.reset_storm(g)
    g.do(GS + 'SetGlobalTimeDilation', TimeDilation=1)
    g.own('ResetProps')
    g.setv('SetPieceState', 0)
    for name in ('Steer', 'Lateral', 'LatRate', 'StrikeLateral'):
        g.setv(name, 0)
    g.do(SC + 'SetVisibility', self=g.getv('SetPiece', g.getv('Road'), ROAD), bNewVisibility=False, bPropagateToChildren=False)
    g.own('DirLetterbox', Enabled=False, Seconds=.3)
    # A leg starts with a view jump (Activate's instant view switch, a restart's teleport): flag the cut, or motion
    # vectors span the jump and the time-shift echo ghosts the old view (level2 L2S1 01654: the board read twice).
    g.do(PCM + 'SetGameCameraCutThisFrame', self=g.f(GS + 'GetPlayerCameraManager', PlayerIndex=0))
    g.finish()


def move():
    """Follow the rail: cruise, ease into corners, brake to a stop at the destination; dodges slide sideways."""
    g = G(CAR, 'Move')
    g.group('Speed for the road')
    gate(g, g.getv('RouteReady'))
    dt = g.math('FClamp', Value=g.arg('Delta'), Min=0, Max=D.MAX_STEP)
    length = g.getv('RouteLength')
    ahead = g.math('FMin', A=add(g, g.getv('Distance'), D.LOOKAHEAD), B=length)
    turn = g.math('Dot_VectorVector', A=rail_at(g, 'Direction', g.getv('Distance')), B=rail_at(g, 'Direction', ahead))
    corner = g.math('Lerp', A=D.CORNER_SPEED, B=D.CRUISE, Alpha=clamp01(g, g.math('Divide_DoubleDouble', A=sub(g, turn, .3), B=.7)))
    left = g.math('FMax', A=sub(g, g.getv('RouteLength'), g.getv('Distance')), B=0)
    stop = add(g, g.math('Sqrt', A=mul(g, 2 * D.BRAKE, left)), 40)
    cruise = mul(g, g.math('FMin', A=corner, B=stop), g.math('SelectFloat', A=D.BRAKE_FACTOR, B=1, bPickA=g.getv('BrakeHeld')))
    target = g.math('SelectFloat', A=0, B=cruise, bPickA=g.getv('CityHold'))
    g.setv('Speed', g.math('FInterpTo_Constant', Current=g.getv('Speed'), Target=target, DeltaTime=dt, InterpSpeed=D.ACCEL))
    g.group('Advance on rail')
    g.setv('Distance', g.math('FMin', A=add(g, g.getv('Distance'), mul(g, g.getv('Speed'), dt)), B=g.getv('RouteLength')))
    g.group('Steer inside the corridor')
    g.setv('LatRate', g.math('FInterpTo', Current=g.getv('LatRate'), Target=mul(g, g.getv('Steer'), D.STEER_SPEED),
                             DeltaTime=dt, InterpSpeed=D.STEER_RESPONSE))
    raw = add(g, g.getv('Lateral'), mul(g, g.getv('LatRate'), dt))
    # the pull back to the rail waits while a dodge strike is up: a car steered clear stays clear when the stick is let go
    dodging = both(g, met(g, 'Active'), g.math('NotEqual_IntInt', A=met(g, 'Kind'), B=0))
    idle = both(g, lt(g, g.math('Abs', A=g.getv('Steer')), .1), NOT(g, dodging))
    pulled = g.math('SelectFloat', A=g.math('FInterpTo', Current=raw, Target=0, DeltaTime=dt, InterpSpeed=D.CENTER_PULL), B=raw, bPickA=idle)
    g.setv('Lateral', pulled)
    # soft wall: past 70% of the corridor a spring pushes back; the corridor's edge is a hard limit
    over = g.math('FMax', A=0, B=sub(g, g.math('Abs', A=g.getv('Lateral')), D.CORRIDOR * D.WALL_SOFT))
    spring = mul(g, mul(g, g.math('SignOfFloat', A=g.getv('Lateral')), over), g.math('FMin', A=1, B=mul(g, D.WALL_SPRING, dt)))
    g.setv('Lateral', g.math('FClamp', Value=sub(g, g.getv('Lateral'), spring), Min=-D.CORRIDOR, Max=D.CORRIDOR))
    g.group('Place the car')
    at = g.getv('Distance')
    where = g.math('Add_VectorVector', A=rail_at(g, 'Location', at),
                   B=g.math('Multiply_VectorFloat', A=rail_at(g, 'RightVector', at), B=g.getv('Lateral')))
    road = g.f(K + 'BreakRotator', InRot=rail_at(g, 'Rotation', g.math('FMin', A=add(g, g.getv('Distance'), 150), B=g.getv('RouteLength'))))
    # the car points where it is going: its slide against its speed, a few degrees off the road
    slip = g.math('FClamp', Value=g.math('DegAtan2', Y=g.getv('LatRate'), X=g.math('FMax', A=g.getv('Speed'), B=200)),
                  Min=-D.STEER_YAW_MAX, Max=D.STEER_YAW_MAX)
    facing = g.math('MakeRotator', Yaw=add(g, (road[0], 'Yaw'), slip))
    smooth = g.math('RInterpTo', Current=g.f(A + 'K2_GetActorRotation'), Target=facing, DeltaTime=dt, InterpSpeed=7)
    g.do(A + 'K2_SetActorLocationAndRotation', NewLocation=where, NewRotation=smooth, bSweep=False, bTeleport=False)
    g.group('Arrive')
    gate(g, both(g, ge(g, g.getv('Distance'), sub(g, g.getv('RouteLength'), 5)), NOT(g, g.getv('NearDestination'))))
    g.setv('NearDestination', True); g.setv('Speed', 0)
    g.setv('ArriveAt', add(g, g.getv('Clock'), .45))
    g.finish()


def track_strike():
    """Keep a falling strike over the point the car will reach at impact (speed changes in corners)."""
    g = G(CAR, 'TrackStrike')
    meteor = g.getv('Meteor')
    gate(g, both(g, met(g, 'Active'), NOT(g, met(g, 'Impacted'))))
    left = g.math('FMax', A=sub(g, D.TELEGRAPH, met(g, 'Age')), B=0)
    ahead = g.math('FMin', A=add(g, g.getv('Distance'), mul(g, g.getv('Speed'), left)), B=g.getv('RouteLength'))
    shift = g.math('SelectFloat', A=g.getv('Lateral'), B=g.getv('StrikeLateral'), bPickA=ieq(g, met(g, 'Kind'), 0))
    where = g.math('Add_VectorVector', A=rail_at(g, 'Location', ahead),
                   B=g.math('Multiply_VectorFloat', A=rail_at(g, 'RightVector', ahead), B=shift))
    g.do(A + 'K2_SetActorLocation', self=meteor, NewLocation=g.math('Add_VectorVector', A=where, B='0,0,-65'),
         bSweep=False, bTeleport=True)
    g.finish()


def schedule():
    """A finite set of strikes per leg, spaced, never inside the stop."""
    g = G(CAR, 'Schedule')
    g.group('Strike due')
    room = g.math('Greater_DoubleDouble', A=sub(g, g.getv('RouteLength'), g.getv('Distance')),
                  B=D.CRUISE * D.TELEGRAPH + D.END_CLEAR)
    # Never while the car waits for the city, and never over the last result's flash (a strike must not chain).
    settled = ge(g, sub(g, g.f(GS + 'GetTimeSeconds'), met(g, 'ResultTime')), D.RESULT_CLEAR)
    piece = pick(g, 'Float', [D.SET_PIECE_AT.get(r, -1.0) for r in range(len(D.RAILS))], g.getv('RailIndex'))
    clear = NOT(g, both(g, ge(g, piece, 0), ge(g, g.getv('Distance'), sub(g, piece, D.SET_PIECE_CLEAR[0])),
                        lt(g, g.getv('Distance'), add(g, piece, D.SET_PIECE_CLEAR[1]))))
    gate(g, both(g, g.getv('RouteReady'), g.math('Greater_IntInt', A=g.getv('MeteorsLeft'), B=0), NOT(g, g.getv('CityHold')),
                 ge(g, g.getv('Clock'), g.getv('NextMeteor')), NOT(g, met(g, 'Active')), settled, room, clear))
    g.group('Strike kind')
    planned = pick(g, 'Int', list(D.KINDS), g.math('Clamp', Value=g.getv('MeteorIndex'), Min=0, Max=len(D.KINDS) - 1))
    lat = g.getv('Lateral')
    toward = g.math('SelectInt', A=-1, B=g.math('SelectInt', A=1, B=planned, bPickA=lt(g, lat, -D.DODGE_SIDE_MIN)),
                    bPickA=g.math('Greater_DoubleDouble', A=lat, B=D.DODGE_SIDE_MIN))
    kind = g.math('SelectInt', A=planned, B=toward, bPickA=ieq(g, planned, 0))
    set_on(g, g.getv('Meteor'), MET, 'Kind', kind)
    g.setv('StrikeLateral', g.getv('Lateral'))
    brace = ieq(g, met(g, 'Kind'), 0)
    g.setv('Teaching', either(g, both(g, brace, NOT(g, g.getv('TaughtBrace'))),
                              both(g, NOT(g, brace), NOT(g, g.getv('TaughtDodge')))))
    g.setv('TaughtBrace', either(g, g.getv('TaughtBrace'), brace))
    g.setv('TaughtDodge', either(g, g.getv('TaughtDodge'), NOT(g, brace)))
    g.group('Arm the strike')
    me = g.ref(); g.node(me, 'self', 0, 500)
    g.do(cls(MET) + ':Arm', self=g.getv('Meteor'), Driver=(me, 'self'),
         Position=g.math('Add_VectorVector', A=g.f(A + 'K2_GetActorLocation'), B='0,0,-65'))
    g.own('TrackStrike')
    g.group('Next strike')
    g.setv('MeteorsLeft', g.math('Subtract_IntInt', A=g.getv('MeteorsLeft'), B=1))
    g.setv('MeteorIndex', g.math('Add_IntInt', A=g.getv('MeteorIndex'), B=1))
    g.setv('NextMeteor', add(g, g.getv('Clock'), D.STRIKE_GAP))
    g.finish()


def read_steer():
    """Steer -1..1 from what is held now: D, Right or RB right; A, Left or LB left; the left stick on top (dead zone 0.15)."""
    g = G(CAR, 'ReadSteer')
    pc = g.f(GS + 'GetPlayerController', PlayerIndex=0)
    down = lambda key: g.math('SelectFloat', A=1, B=0, bPickA=g.f('/Script/Engine.PlayerController:IsInputKeyDown', self=pc, Key=key))  # noqa: E731
    keys = sub(g, add(g, add(g, down('D'), down('Right')), down('Gamepad_RightShoulder')),
               add(g, add(g, down('A'), down('Left')), down('Gamepad_LeftShoulder')))
    stick = g.f('/Script/Engine.PlayerController:GetInputAnalogKeyState', self=pc, Key='Gamepad_LeftX')
    live = g.math('SelectFloat', A=stick, B=0, bPickA=g.math('Greater_DoubleDouble', A=g.math('Abs', A=stick), B=.15))
    g.setv('Steer', g.math('FClamp', Value=add(g, keys, live), Min=-1, Max=1))
    g.finish()


def change_lane():
    """The A/D input events: steering is continuous now (ReadSteer, Move); a press only kicks the slide on its first frame."""
    g = G(CAR, 'ChangeLane')
    g.setv('LatRate', add(g, g.getv('LatRate'), mul(g, g.arg('Side'), 150)))
    g.finish()


def resolve_hit():
    g = G(CAR, 'ResolveHit')
    g.setv('Composure', g.math('Max', A=0, B=g.math('Subtract_IntInt', A=g.getv('Composure'), B=g.arg('Cost'))))
    g.setv('LastOutcome', g.arg('Outcome')); g.setv('HitsResolved', g.math('Add_IntInt', A=g.getv('HitsResolved'), B=1))
    g.own('Feedback', Cost=g.arg('Cost'))
    value = g.f('/Script/Engine.KismetStringLibrary:Conv_IntToString', InInt=g.getv('Composure'))
    line = g.f('/Script/Engine.KismetStringLibrary:Concat_StrStr', A='L2 impact Composure ', B=value)
    g.do(SL + 'PrintString', InString=line, bPrintToScreen=False, bPrintToLog=True)
    gate(g, g.math('LessEqual_IntInt', A=g.getv('Composure'), B=0)); g.own('Restart')
    g.finish()


def feedback():
    """Unmistakable result: slow-motion beat, camera kick, sound. ReduceMotion keeps the beat, drops the kick."""
    g = G(CAR, 'Feedback')
    g.group('Beat and kick')
    cost = g.arg('Cost')
    good = ieq(g, cost, 0); late = both(g, g.math('Greater_IntInt', A=cost, B=0), g.math('Less_IntInt', A=cost, B=40))
    perfect = ieq(g, met(g, 'Result'), 4)
    now = g.f(GS + 'GetRealTimeSeconds')
    pf = lambda a, b_: g.math('SelectFloat', A=a, B=b_, bPickA=perfect)  # noqa: E731
    g.setv('SlowUntil', add(g, now, pf(D.PERFECT_SLOW, g.math('SelectFloat', A=D.GOOD_SLOW, B=D.HIT_SLOW, bPickA=good))))
    g.setv('SlowScale', pf(D.PERFECT_DILATION, g.math('SelectFloat', A=D.GOOD_DILATION, B=D.HIT_DILATION, bPickA=good)))
    g.setv('Shake', pf(5, g.math('SelectFloat', A=9, B=g.math('SelectFloat', A=22, B=40, bPickA=late), bPickA=good)))
    g.setv('FovPunch', pf(-12, g.math('SelectFloat', A=-7, B=9, bPickA=good)))
    g.group('The streak')
    delta = pf(D.MOOD_PERFECT, g.math('SelectFloat', A=D.MOOD_CLEAN, B=g.math('SelectFloat', A=D.MOOD_LATE, B=D.MOOD_HIT,
                                                                                bPickA=late), bPickA=good))
    g.setv('Mood', g.math('FClamp', Value=add(g, g.getv('Mood'), delta), Min=-1, Max=1))
    g.group('Result sound')
    hit = g.branch(NOT(g, good)); g.side(hit)
    sound(g, 'hit', g.math('SelectFloat', A=.45, B=.8, bPickA=late))
    # stormier with every miss: a glitch burst that grows as the streak's mood sinks
    g.own('DirGlitch', Strength=add(g, .25, mul(g, .35, g.math('FMax', A=0, B=mul(g, -1, g.getv('Mood'))))), Seconds=.9)
    g.side(hit, False)
    sound(g, 'sand', .35)
    g.own('Reward')
    braced = gate(g, ieq(g, met(g, 'Kind'), 0))
    sound(g, 'clash', .55)
    g.finish()


def update_feel():
    """Global time dilation: the slow-motion beat after a result, a slower world while a first prompt teaches."""
    g = G(CAR, 'UpdateFeel')
    g.group('Time dilation')
    age = met(g, 'Age')
    prompt = both(g, met(g, 'Active'), NOT(g, met(g, 'Impacted')), ge(g, age, D.TELEGRAPH - D.PROMPT_LEAD))
    teach = both(g, prompt, g.getv('Teaching'))
    beat = lt(g, g.f(GS + 'GetRealTimeSeconds'), g.getv('SlowUntil'))
    scale = g.math('SelectFloat', A=g.getv('SlowScale'),
                   B=g.math('SelectFloat', A=D.TEACH_DILATION, B=1, bPickA=teach), bPickA=beat)
    g.do(GS + 'SetGlobalTimeDilation', TimeDilation=scale)
    # EngineSpeed for the engine loop's pitch (atmosphere lane): 0 standing, 1 at cruise, up to 1.2.
    g.setv('EngineSpeed', g.math('FClamp', Value=g.math('Divide_DoubleDouble', A=g.getv('Speed'), B=D.CRUISE), Min=0, Max=1.2))
    # The prompt names the device in hand: the last one touched.
    g.group('Device in hand')
    pc = g.f(GS + 'GetPlayerController', PlayerIndex=0)
    down = lambda key: g.f('/Script/Engine.PlayerController:IsInputKeyDown', self=pc, Key=key)
    stick = lambda key: g.math('Greater_DoubleDouble', A=g.math('Abs', A=g.f(
        '/Script/Engine.PlayerController:GetInputAnalogKeyState', self=pc, Key=key)), B=.4)
    pad = either(g, *[down(k) for k in PAD_KEYS.values()], down('Gamepad_FaceButton_Top'), stick('Gamepad_LeftX'), stick('Gamepad_LeftY'))
    keys = either(g, *[down(k) for k in ('SpaceBar', 'A', 'D', 'Left', 'Right', 'Enter', 'C')])
    # Keyboard until a pad button or stick is used: an assigned pad alone is not proof (the QA editor reports one).
    g.setv('UsingPad', either(g, pad, both(g, NOT(g, keys), g.getv('UsingPad'))))
    g.finish()


def auto_park():
    g = G(CAR, 'AutoPark')
    gate(g, both(g, g.getv('NearDestination'), NOT(g, g.getv('Arrived')), NOT(g, g.getv('Failed')),
                 ge(g, g.getv('Clock'), g.getv('ArriveAt'))))
    g.own('Continue')
    # While the stop plays, stream the opening of the usual next leg (a different next leg re-points the sectors).
    nxt = [D.ROUTE_KEYS.index(k) for k in (('J0', 'J1'), ('J1', 'B'), ('J2', 'B'))]
    gate(g, g.math('Less_IntInt', A=g.getv('ArrivalJob'), B=3))
    g.own('SetRail', Index=pick(g, 'Int', nxt, g.getv('ArrivalJob')))
    g.own('PreloadCity')
    g.finish()


def drive_step():
    g = G(CAR, 'DriveStep'); dt = g.arg('Delta')
    g.group('Clock and feel')
    gate(g, g.getv('Active'))
    g.setv('Clock', add(g, g.getv('Clock'), dt))
    g.own('UpdateFeel'); g.own('UpdateMood')
    g.group('Road restart')
    failed = g.branch(g.getv('Failed')); g.side(failed)
    gate(g, ge(g, g.getv('Clock'), g.getv('RestartAt')))
    integrated = g.branch(g.f(SL + 'IsValid', Object=g.getv('Journey'))); g.side(integrated)
    journey = g.cast(g.getv('Journey'), cls(JOURNEY), 'BP L2Journey')
    g.do(cls(JOURNEY) + ':RestartRun', self=journey)
    g.side(integrated, False); g.own('StartLeg', Index=0)
    g.side(failed, False)
    g.group('Drive the rail')
    driving = g.branch(NOT(g, g.getv('Arrived'))); g.side(driving)
    for name in ('PickRoute', 'CheckCity', 'ReadSteer', 'Move', 'RollCity', 'TrackStrike', 'SetPiece', 'Schedule', 'SpawnProp', 'AutoPark'):
        g.own(name, **({'Delta': dt} if name == 'Move' else {}))
    for i in range(4):
        g.own('FadeProp', Index=i)
    g.do(cls(ROAD) + ':StepTraffic', self=g.getv('Road'), Delta=dt, Driver=g.f(A + 'K2_GetActorLocation'))
    g.own('RefreshHUD')
    g.side(driving, False); g.own('RefreshHUD')
    g.finish()


def refresh_hud():
    g = G(CAR, 'RefreshHUD')
    hud = g.getv('HUD')
    gate(g, g.f(SL + 'IsValid', Object=hud))
    g.group('Status card')
    g.do(cls(HUD) + ':RefreshProgress', self=g.getv('HUD'), Value=g.getv('Employability'))
    metres = g.f('/Script/Engine.KismetStringLibrary:Conv_IntToString', InInt=g.math('Round', A=g.math(
        'Divide_DoubleDouble', A=sub(g, g.getv('RouteLength'), g.getv('Distance')), B=100)))
    line = g.f('/Script/Engine.KismetStringLibrary:Concat_StrStr', A=metres, B=' m to go')
    show_route = both(g, g.getv('RouteReady'), NOT(g, g.getv('Arrived')), NOT(g, g.getv('Failed')),
                      NOT(g, g.getv('NearDestination')))
    cue = g.f('/Script/Engine.KismetTextLibrary:Conv_StringToText', InString=g.math(
        'SelectString', A=line, B=g.f('/Script/Engine.KismetTextLibrary:Conv_TextToString', InText=g.getv('Cue')),
        bPickA=show_route))
    g.do(cls(HUD) + ':Refresh', self=g.getv('HUD'), Value=g.getv('Composure'), Location=g.getv('Place'), Prompt=cue)
    g.group('C.V. hint while stopped')
    stopped = lt(g, g.math('Abs', A=g.getv('Speed')), 30)
    g.setv('HintAlpha', g.math('FInterpTo', Current=g.getv('HintAlpha'), Target=g.math('SelectFloat', A=1, B=0, bPickA=stopped),
                               DeltaTime=g.f(GS + 'GetWorldDeltaSeconds'), InterpSpeed=5))
    for name in ('Txt_Controls', 'Brd_DriveControls'):
        g.do(W + 'SetRenderOpacity', self=g.getv(name, g.getv('HUD'), HUD), InOpacity=g.getv('HintAlpha'))
    g.group('Strike prompt')
    age = met(g, 'Age'); kind = met(g, 'Kind')
    up = both(g, met(g, 'Active'), ge(g, age, D.TELEGRAPH - D.PROMPT_LEAD))
    close = clamp01(g, g.math('Divide_DoubleDouble', A=sub(g, age, D.TELEGRAPH - D.PROMPT_LEAD),
                              B=D.PROMPT_LEAD - D.BRACE_WINDOW))
    since = sub(g, g.f(GS + 'GetTimeSeconds'), met(g, 'ResultTime'))
    flash = both(g, g.math('Greater_IntInt', A=met(g, 'Result'), B=0), lt(g, since, .7))
    glyph = lambda table: g.math('SelectString', A=table[0], B=g.math('SelectString', A=table[1], B=table[-1],
                                 bPickA=g.math('Greater_IntInt', A=kind, B=0)), bPickA=ieq(g, kind, 0))
    key = g.math('SelectString', A=glyph(PAD_GLYPHS), B=glyph(KEYS), bPickA=g.getv('UsingPad'))
    g.do(cls(HUD) + ':SetQTE', self=g.getv('HUD'), Key=g.f('/Script/Engine.KismetTextLibrary:Conv_StringToText', InString=key),
         Shown=either(g, up, flash), Close=close, Live=both(g, up, either(g, g.math('NotEqual_IntInt', A=kind, B=0), ge(g, met(g, 'Age'), D.TELEGRAPH - D.BRACE_WINDOW))),
         Result=g.math('SelectInt', A=met(g, 'Result'), B=0, bPickA=flash), ResultAge=since)
    g.finish()


def director_call(name, fn, **pins):
    """A post-lane contract call on BP_DreamDirector (found once per leg by FindDirector), skipped when there is none."""
    def build():
        g = G(CAR, name)
        gate(g, g.f(SL + 'IsValid', Object=g.getv('Director')))
        g.do(cls(DIRECTOR) + ':' + fn, self=g.getv('Director'), **{k: g.arg(v) for k, v in pins.items()})
        g.finish()
    return build


def find_director():
    g = G(CAR, 'FindDirector')
    found = g.do(GS + 'GetActorOfClass', ActorClass=cls(DIRECTOR))
    g.setv('Director', g.cast(found, cls(DIRECTOR), 'BP Dream Director'))
    g.finish()


IMPACT_SOUNDS = ['/Game/FoA/Audio/SFX/Dream/SFX_Dream_LowImpact_01.SFX_Dream_LowImpact_01'] + list(SOUNDS.values())


def warm_impact():
    """Everything a strike's impact uses is made ready while the car waits at the start of a leg, so an impact only
    toggles and sets parameters (perf lane, Shipping: 40-179 ms frames on impacts with game thread and GPU low): the
    level's pooled sand manager is found or made now, a small burst and bloom 25 m ahead create their pooled pieces and
    draw their materials once, the impact sounds are primed, and the post director is found once."""
    g = G(CAR, 'WarmImpact')
    g.own('FindDirector')
    for sound in IMPACT_SOUNDS:
        g.do(GS + 'PrimeSound', InSound=sound)
    g.do(cls(SANDFX) + ':GetSandFX')
    ahead = g.math('Add_VectorVector', A=g.f(A + 'K2_GetActorLocation'),
                   B=g.math('Multiply_VectorFloat', A=g.f(A + 'GetActorForwardVector'), B=2500))
    g.do(cls(SANDFX) + ':SpawnSandBurst', Location=ahead, Scale=.6)
    g.do(cls(SANDFX) + ':SpawnSandBloom', Location=ahead, Size=.6, Seconds=.4, Crumble=True)
    g.finish()


def find_room_audio():
    g = G(CAR, 'FindRoomAudio')
    found = g.do(GS + 'GetActorOfClass', ActorClass=cls(ROOM_AUDIO))
    g.setv('RoomAudio', g.cast(found, cls(ROOM_AUDIO), 'BP Room Audio'))
    g.finish()


def update_mood():
    """The streak: clean braces calm the city and swell the music, misses make it stormier (Feedback moves Mood)."""
    g = G(CAR, 'UpdateMood')
    g.setv('MoodShown', g.math('FInterpTo', Current=g.getv('MoodShown'), Target=g.getv('Mood'),
                               DeltaTime=g.f(GS + 'GetWorldDeltaSeconds'), InterpSpeed=1.5))
    have = g.branch(g.f(SL + 'IsValid', Object=g.getv('RoomAudio'))); g.side(have, False); g.own('FindRoomAudio'); g.side(have)
    for name in ('Music', 'Music2'):  # the room audio crossfades through FadeIn/FadeOut; the multiplier is ours
        g.do('/Script/Engine.AudioComponent:SetVolumeMultiplier', self=g.getv(name, g.getv('RoomAudio'), ROOM_AUDIO),
             NewVolumeMultiplier=add(g, 1, mul(g, g.getv('MoodShown'), D.MUSIC_SWELL)))
    g.finish()


def reset_mood():
    g = G(CAR, 'ResetMood')
    g.setv('Mood', 0); g.setv('MoodShown', 0)
    gate(g, g.f(SL + 'IsValid', Object=g.getv('RoomAudio')))
    for name in ('Music', 'Music2'):
        g.do('/Script/Engine.AudioComponent:SetVolumeMultiplier', self=g.getv(name, g.getv('RoomAudio'), ROOM_AUDIO),
             NewVolumeMultiplier=1)
    g.finish()


def reward():
    """A perfect brace: the post lane's highlight streak across the screen and a whoosh over the deep slow motion."""
    g = G(CAR, 'Reward')
    gate(g, ieq(g, met(g, 'Result'), 4))
    g.own('DirStreak', Intensity=.9, Seconds=.8)
    sound(g, 'whoosh', .6)
    g.finish()


def set_piece():
    """One per long leg: the Nightmare rises out of the road 90 m ahead and rears over it; 12 m before it the car
    drives through as it bursts back into sand (slow motion, bars, kick). Strikes keep clear of it (Schedule)."""
    g = G(CAR, 'SetPiece')
    g.setv('SetPieceAt', pick(g, 'Float', [D.SET_PIECE_AT.get(r, -1.0) for r in range(len(D.RAILS))], g.getv('RailIndex')))
    gate(g, both(g, g.getv('RouteReady'), ge(g, g.getv('SetPieceAt'), 0), g.math('Less_IntInt', A=g.getv('SetPieceState'), B=3)))
    piece = lambda: g.getv('SetPiece', g.getv('Road'), ROAD)  # noqa: E731
    where = lambda: g.math('Add_VectorVector', A=rail_at(g, 'Location', g.getv('SetPieceAt')), B='0,0,-65')  # noqa: E731
    g.group('Rise out of the road')
    rise = g.branch(both(g, ieq(g, g.getv('SetPieceState'), 0),
                         ge(g, add(g, g.getv('Distance'), D.SET_PIECE_RISE), g.getv('SetPieceAt')))); g.side(rise)
    facing = g.f(K + 'BreakRotator', InRot=rail_at(g, 'Rotation', g.getv('SetPieceAt')))
    g.do(SC + 'K2_SetWorldLocationAndRotation', self=piece(), NewLocation=where(),
         NewRotation=g.math('MakeRotator', Yaw=add(g, (facing[0], 'Yaw'), 180)), bSweep=False, bTeleport=True)
    g.do(SC + 'SetVisibility', self=piece(), bNewVisibility=True, bPropagateToChildren=False)
    sand_event(g, piece(), 1, D.SET_PIECE_FORM, 0)
    g.do(cls(SANDFX) + ':SpawnSandBurst', Location=where(), Scale=5)
    sound(g, 'sand', .55)
    g.own('DirLetterbox', Enabled=True, Seconds=.8)
    g.setv('SetPieceState', 1)
    g.side(rise, False)
    g.group('Drive through it')
    through = g.branch(both(g, ieq(g, g.getv('SetPieceState'), 1),
                            ge(g, add(g, g.getv('Distance'), D.SET_PIECE_BURST), g.getv('SetPieceAt')))); g.side(through)
    sand_event(g, piece(), 0, D.SET_PIECE_CRUMBLE, 1)
    g.do(cls(SANDFX) + ':SpawnSandBurst', Location=g.math('Add_VectorVector', A=where(), B='0,0,300'), Scale=7)
    g.setv('SlowUntil', add(g, g.f(GS + 'GetRealTimeSeconds'), .8)); g.setv('SlowScale', .35)
    g.setv('Shake', 28); g.setv('FovPunch', 12)
    sound(g, 'sand', .8); sound(g, 'whoosh', .7)
    g.setv('SetPieceState', 2)
    g.side(through, False)
    g.group('Gone')
    gate(g, both(g, ieq(g, g.getv('SetPieceState'), 2), ge(g, g.getv('Distance'), add(g, g.getv('SetPieceAt'), D.SET_PIECE_GONE))))
    g.do(SC + 'SetVisibility', self=piece(), bNewVisibility=False, bPropagateToChildren=False)
    g.own('DirLetterbox', Enabled=False, Seconds=1)
    g.setv('SetPieceState', 3)
    g.finish()


def update_camera():
    """Smooth chase: the boom eases behind the car's own (already smoothed) heading; kick and FOV punch decay."""
    g = G(CAR, 'UpdateCamera'); dt = g.arg('Delta'); boom = g.getv('CameraBoom')
    gate(g, g.getv('Active'))
    g.group('Follow the car')
    car = g.f(K + 'BreakRotator', InRot=g.f(A + 'K2_GetActorRotation'))
    pitch = g.math('FClamp', Value=g.getv('CameraPitch'), Min=5, Max=30)
    target = g.math('MakeRotator', Pitch=mul(g, -1, pitch), Yaw=add(g, (car[0], 'Yaw'), g.getv('CameraYawOffset')), Roll=0)
    smooth = g.math('RInterpTo', Current=g.f(SC + 'K2_GetComponentRotation', self=boom), Target=target, DeltaTime=dt, InterpSpeed=5)
    g.do(SC + 'K2_SetWorldRotation', self=boom, NewRotation=g.math('SelectRotator', A=smooth, B=target, bPickA=g.getv('CameraReady')),
         bSweep=False, bTeleport=True)
    g.setv('CutCamera', NOT(g, g.getv('CameraReady')))
    g.setv('CameraReady', True)
    g.group('Kick and FOV punch')
    reduce = g.do('/Script/Engine.KismetMaterialLibrary:GetScalarParameterValue', Collection=DREAM_MPC,
                  ParameterName='ReduceMotion')  # impure in 5.9: it must sit on the exec path
    motion = sub(g, 1, clamp01(g, reduce))
    t = g.f(GS + 'GetRealTimeSeconds')
    kick = mul(g, g.getv('Shake'), motion)
    offset = g.math('MakeVector', X=0, Y=mul(g, g.math('Sin', A=mul(g, t, 61)), kick),
                    Z=mul(g, g.math('Sin', A=add(g, mul(g, t, 47), 1.7)), mul(g, kick, .6)))
    camera = g.getv('FollowCamera')
    g.do(SC + 'K2_SetRelativeLocation', self=camera, NewLocation=offset, bSweep=False, bTeleport=True)
    g.do('/Script/Engine.CameraComponent:SetFieldOfView', self=g.getv('FollowCamera'),
         InFieldOfView=add(g, 80, mul(g, g.getv('FovPunch'), motion)))
    g.setv('Shake', g.math('FInterpTo', Current=g.getv('Shake'), Target=0, DeltaTime=dt, InterpSpeed=5))
    g.setv('FovPunch', g.math('FInterpTo', Current=g.getv('FovPunch'), Target=0, DeltaTime=dt, InterpSpeed=4))
    g.group('Camera cut on a snap')
    gate(g, g.getv('CutCamera'))
    g.do(PCM + 'SetGameCameraCutThisFrame', self=g.f(GS + 'GetPlayerCameraManager', PlayerIndex=0))
    g.finish()


def sand_event(g, component, frm, seconds, to):
    """M_SplatMesh's SandEvent (custom primitive data 0-3): dissolve from -> to over seconds, starting now."""
    g.do(PRIM + 'SetVectorParameterForCustomPrimitiveData', self=component, ParameterName='SandEvent',
         Value=g.math('MakeVector4', X=frm, Y=g.f(GS + 'GetTimeSeconds'), Z=seconds, W=to))


def spawn_prop():
    """The next pooled sand prop forms ahead, alternating the right kerb and the oncoming lane."""
    g = G(CAR, 'SpawnProp')
    g.group('Next prop due')
    at = add(g, mul(g, g.math('Conv_IntToDouble', InInt=g.getv('NextProp')), D.PROP_GAP), D.PROP_FIRST)
    gate(g, both(g, g.getv('RouteReady'), g.math('Greater_IntInt', A=g.getv('PropSlots'), B=0),
                 ge(g, add(g, g.getv('Distance'), D.PROP_AHEAD), at), lt(g, at, sub(g, g.getv('RouteLength'), 2500))))
    g.setv('PropAt', at)
    even = ieq(g, g.math('Percent_IntInt', A=g.getv('NextProp'), B=2), 0)
    g.setv('PropSide', g.math('SelectFloat', A=D.PROP_RIGHT, B=D.PROP_LEFT, bPickA=even))
    g.setv('PropSlot', g.math('Percent_IntInt', A=g.getv('NextProp'), B=g.getv('PropSlots')))
    g.setv('NextProp', g.math('Add_IntInt', A=g.getv('NextProp'), B=1))
    road = g.getv('Road')
    g.group('Where it stands')
    where = g.math('Add_VectorVector', A=g.math('Add_VectorVector', A=rail_at(g, 'Location', g.getv('PropAt')),
                   B=g.math('Multiply_VectorFloat', A=rail_at(g, 'RightVector', g.getv('PropAt')), B=g.getv('PropSide'))),
                   B='0,0,-65')
    facing = g.f(K + 'BreakRotator', InRot=rail_at(g, 'Rotation', g.getv('PropAt')))
    yaw = add(g, (facing[0], 'Yaw'), g.math('SelectFloat', A=152, B=208, bPickA=g.math(
        'Greater_DoubleDouble', A=g.getv('PropSide'), B=0)))
    g.group('Form from sand')
    for i in range(4):
        br = g.branch(ieq(g, g.getv('PropSlot'), i)); g.side(br)
        prop = g.getv(f'SandProp{i}', road, ROAD)
        g.do(SC + 'K2_SetWorldLocationAndRotation', self=prop, NewLocation=where, NewRotation=g.math('MakeRotator', Yaw=yaw),
             bSweep=False, bTeleport=True)
        g.do(SC + 'SetVisibility', self=g.getv(f'SandProp{i}', road, ROAD), bNewVisibility=True, bPropagateToChildren=False)
        sand_event(g, g.getv(f'SandProp{i}', road, ROAD), 1, D.PROP_FORM, 0)
        g.setv(f'PropDist{i}', g.getv('PropAt')); g.setv(f'PropState{i}', 1)
        g.do(cls('/Game/FoA/VFX/Sand/BPL_SandFX') + ':SpawnSandBurst', Location=where, Scale=2.4)
        g.side(br, False)
    g.finish()


def fade_prop():
    """Crumble a formed prop as the car draws level; hide it once it is well behind."""
    g = G(CAR, 'FadeProp')
    road = g.getv('Road')
    for i in range(4):
        br = g.branch(ieq(g, g.arg('Index'), i)); g.side(br)
        dist_i, state = g.getv(f'PropDist{i}'), g.getv(f'PropState{i}')
        crumble = g.branch(both(g, ieq(g, state, 1), ge(g, g.getv('Distance'), sub(g, dist_i, D.PROP_PASS)))); g.side(crumble)
        sand_event(g, g.getv(f'SandProp{i}', road, ROAD), 0, D.PROP_CRUMBLE, 1)
        g.setv(f'PropState{i}', 2)
        g.side(crumble, False)
        gate(g, both(g, ieq(g, g.getv(f'PropState{i}'), 2), ge(g, g.getv('Distance'), add(g, g.getv(f'PropDist{i}'), D.PROP_GONE))))
        g.do(SC + 'SetVisibility', self=g.getv(f'SandProp{i}', road, ROAD), bNewVisibility=False, bPropagateToChildren=False)
        g.setv(f'PropState{i}', 0)
        g.side(br, False)
    g.finish()


def reset_props():
    """Every leg: props hidden, and the prop and traffic counts follow the view-distance scalability tier."""
    g = G(CAR, 'ResetProps')
    gate(g, g.f(SL + 'IsValid', Object=g.getv('Road')))
    g.setv('NextProp', 0)
    for i in range(4):
        g.setv(f'PropState{i}', 0)
        g.do(SC + 'SetVisibility', self=g.getv(f'SandProp{i}', g.getv('Road'), ROAD), bNewVisibility=False, bPropagateToChildren=False)
    settings = g.do('/Script/Engine.GameUserSettings:GetGameUserSettings')
    low = g.math('LessEqual_IntInt', A=g.f('/Script/Engine.GameUserSettings:GetViewDistanceQuality', self=settings), B=1)
    g.setv('PropSlots', g.math('SelectInt', A=D.LOW_PROPS, B=4, bPickA=low))
    set_on(g, g.getv('Road'), ROAD, 'TrafficLimit', g.math('SelectInt', A=D.LOW_TRAFFIC, B=len(D.TRAFFIC), bPickA=low))
    g.do(cls(ROAD) + ':ApplyTrafficLimit', self=g.getv('Road'))
    g.finish()


def deactivate():
    """build_drive.deactivate plus the rails' own cleanup: normal time and no props left standing."""
    g = G(CAR, 'Deactivate')
    gate(g, g.getv('Active'))
    for name, value in [('Active', False), ('Throttle', False), ('BrakeHeld', False), ('TurnQueued', False), ('Speed', 0)]:
        g.setv(name, value)
    g.do(GS + 'SetGlobalTimeDilation', TimeDilation=1)
    g.own('ResetShockwave'); g.own('ResetProps'); g.own('ResetMood')
    g.do(SC + 'SetVisibility', self=g.getv('SetPiece', g.getv('Road'), ROAD), bNewVisibility=False, bPropagateToChildren=False)
    g.own('DirLetterbox', Enabled=False, Seconds=.5)
    g.do(cls(MET) + ':Hide', self=g.getv('Meteor'))
    g.do(cls(MET) + ':ResetImpact', self=g.getv('Meteor'))
    b.reset_storm(g)
    from free_drive import hide_sign
    hide_sign(g)
    pc = g.f(GS + 'GetPlayerController', PlayerIndex=0)
    sub_ = g.f('/Script/Engine.SubsystemBlueprintLibrary:GetLocalPlayerSubSystemFromPlayerController',
               PlayerController=pc, Class='/Script/EnhancedInput.EnhancedInputLocalPlayerSubsystem')
    sub_ = g.cast(sub_, '/Script/EnhancedInput.EnhancedInputLocalPlayerSubsystem', 'Enhanced Input Local Player Subsystem')
    g.do('/Script/EnhancedInput.EnhancedInputSubsystemInterface:RemoveMappingContext', self=sub_,
         MappingContext=D.ROOT + '/Input/IMC_L2Drive.IMC_L2Drive')
    g.do('/Script/UMG.Widget:RemoveFromParent', self=g.getv('HUD'))
    gate(g, g.f(SL + 'IsValid', Object=g.getv('ReturnPawn')))
    g.do('/Script/Engine.Controller:Possess', self=pc, InPawn=g.getv('ReturnPawn'))
    g.do('/Script/Engine.PlayerController:SetViewTargetWithBlend', self=pc, NewViewTarget=g.getv('ReturnPawn'), BlendTime=.2)
    g.finish()


# ---- BP_L2RoadNetwork: traffic ------------------------------------------------------------------------------------
def step_traffic():
    """Fourteen pooled cars on the outer lanes; each waits while the player's car is close, sinks into the sand at
    its lane ends and rises again at the start."""
    g = G(ROAD, 'StepTraffic')
    dt = g.math('FClamp', Value=g.arg('Delta'), Min=0, Max=D.MAX_STEP)
    for i, ((lane, speed, _), name) in enumerate(zip(D.TRAFFIC, D.TRAFFIC_NAMES)):
        (ax, ay), (bx, by) = D.LANES[lane]
        length = dist((ax, ay), (bx, by)); dx, dy = (bx - ax) / length, (by - ay) / length
        base = D.CAR_Z if name.endswith('Collision') else 0.0  # the car models stand on their pivot: wheels on the road
        here = g.f(SC + 'K2_GetComponentLocation', self=g.getv(name))
        wait = either(g, lt(g, g.math('Vector_Distance2D', V1=here, V2=g.arg('Driver')), 1200),
                      g.math('LessEqual_IntInt', A=g.getv('TrafficLimit'), B=i))
        ahead = add(g, g.getv(f'TrafficPos{i}'), g.math('SelectFloat', A=0, B=mul(g, speed, dt), bPickA=wait))
        g.setv('Wrapped', g.math('Greater_DoubleDouble', A=ahead, B=length))  # read before TrafficPos moves on
        g.setv(f'TrafficPos{i}', g.math('SelectFloat', A=sub(g, ahead, length), B=ahead, bPickA=g.getv('Wrapped')))
        at = g.getv(f'TrafficPos{i}')
        edge = g.math('FMin', A=at, B=sub(g, length, g.getv(f'TrafficPos{i}')))
        z = g.math('Lerp', A=base - 320, B=base, Alpha=clamp01(g, g.math('Divide_DoubleDouble', A=edge, B=700)))
        where = g.math('MakeVector', X=add(g, ax, mul(g, dx, at)), Y=add(g, ay, mul(g, dy, g.getv(f'TrafficPos{i}'))), Z=z)
        g.do(SC + 'K2_SetWorldLocationAndRotation', self=g.getv(name), NewLocation=where,
             NewRotation=g.math('MakeRotator', Yaw=round(degrees(atan2(dy, dx)), 2)), bSweep=False, bTeleport=True)
        near = lt(g, g.math('Vector_Distance2D', V1=g.f(SC + 'K2_GetComponentLocation', self=g.getv(name)), V2=g.arg('Driver')),
                  D.TRAFFIC_SAND)
        g.own('TrafficSand', Car=g.getv(name), Wrapped=g.getv('Wrapped'), Near=near,
              Allowed=g.math('Greater_IntInt', A=g.getv('TrafficLimit'), B=i))
    g.own('SignFlicker')
    g.finish()


def sign_flicker():
    """Neon lettering on the hiring signs: a steady hum and, a few times a minute, a short dip (each sign on its own
    beat, in twelfths of a second); the unlit text material multiplies its glow by the text colour."""
    g = G(ROAD, 'SignFlicker')
    t = g.f(GS + 'GetTimeSeconds')
    for i in range(4):
        step = g.math('FFloor', A=mul(g, t, 12))
        n = g.math('Fraction', A=mul(g, g.math('Sin', A=add(g, mul(g, g.math('Conv_IntToDouble', InInt=step), 12.9898), i * 78.233)),
                                        43758.5453))
        dip = g.math('SelectFloat', A=.5, B=1, bPickA=g.math('Greater_DoubleDouble', A=n, B=.94))
        hum = add(g, .93, mul(g, .07, g.math('Sin', A=add(g, mul(g, t, 23 + 4 * i), i))))
        b = mul(g, dip, hum)
        color = g.math('Conv_LinearColorToColor', InLinearColor=g.math('MakeColor', R=b, G=b, B=b, A=1), InUseSRGB=True)
        g.do('/Script/Engine.TextRenderComponent:SetTextRenderColor', self=g.getv(f'JobBoardText{i}'), Value=color)
    g.finish()


def traffic_sand():
    """A car the player passes bursts into sand and is gone; it comes back when it wraps to its lane start."""
    g = G(ROAD, 'TrafficSand')
    back = g.branch(both(g, g.arg('Wrapped'), g.arg('Allowed'))); g.side(back)
    g.do(SC + 'SetVisibility', self=g.arg('Car'), bNewVisibility=True, bPropagateToChildren=True); g.side(back, False)
    gate(g, both(g, g.arg('Near'), g.f(SC + 'IsVisible', self=g.arg('Car'))))
    g.do(cls(SANDFX) + ':SpawnSandBurst', Location=g.f(SC + 'K2_GetComponentLocation', self=g.arg('Car')), Scale=2.6)
    g.do(SC + 'SetVisibility', self=g.arg('Car'), bNewVisibility=False, bPropagateToChildren=True)
    g.do(GS + 'PlaySound2D', Sound=SOUNDS['sand'], VolumeMultiplier=.22)
    g.finish()


def apply_traffic_limit():
    g = G(ROAD, 'ApplyTrafficLimit')
    for i, name in enumerate(D.TRAFFIC_NAMES):
        g.do(SC + 'SetVisibility', self=g.getv(name), bPropagateToChildren=True,
             bNewVisibility=g.math('Greater_IntInt', A=g.getv('TrafficLimit'), B=i))
    g.finish()


# ---- City sectors: rolling preload along the rail (perf lane 11-18 00:5x; coordinator 11-18 02:10) -----------------
SECTOR = '/Game/FoA/Level2/City/Expanded/BP_City2Sector'
STR = '/Script/Engine.KismetStringLibrary:'
CITY_HOLD = 2.5


def for_each_sector(g):
    """ForEachLoop over every BP_City2Sector; returns (loop, typed sector) with the tail inside the body."""
    actors = g.do(GS + 'GetAllActorsOfClass', ActorClass=cls(SECTOR))
    loop = g.ref(); g.node(loop, 'macro', 0, 0, macro_name='ForEachLoop'); g.put(loop, 'Array', (actors[0], 'OutActors'))
    g.link(g.tail, 'then', loop, 'Exec'); g.tail = loop; g._side = 'LoopBody'
    return loop, g.cast((loop, 'Array Element'), cls(SECTOR), 'BP City 2Sector')


def preload_city():
    """Pin every sector the next ROLL_AHEAD (250 m) of the rail passes, keep it until the car is ROLL_BEHIND past the
    last point that passes it (about 150 m behind), and let the rest follow the camera. The spans are computed offline
    per rail and cell (drive_data.SPAN_TABLE in SpanTable). A pinned sector points its own BootstrapPoint at itself, so
    its 4 Hz tick keeps it loaded; one whose pin changed is updated now. Runs when a leg starts, when the stop points at
    the next leg, and every ROLL_STEP of travel (RollCity)."""
    g = G(CAR, 'PreloadCity')
    g.group('Pin the sectors along the rail')
    loop, sector = for_each_sector(g)
    centre = g.f(A + 'K2_GetActorLocation', self=sector)
    c = g.math('BreakVector', InVec=centre)[0]
    cx = g.math('FFloor', A=g.math('Divide_DoubleDouble', A=(c, 'X'), B=D.CELL_CM))
    cy = g.math('FFloor', A=g.math('Divide_DoubleDouble', A=sub(g, (c, 'Y'), D.CITY_Y0), B=D.CELL_CM))
    cell = g.math('Add_IntInt', A=g.math('Multiply_IntInt', A=cx, B=D.CITY_SIDE), B=cy)
    at = g.math('Multiply_IntInt', A=g.math('Add_IntInt', A=g.math('Multiply_IntInt', A=g.getv('RailIndex'), B=D.CITY_SIDE ** 2),
                                             B=cell), B=8)
    metres = lambda start: g.f(STR + 'Conv_StringToDouble', InString=g.f(
        STR + 'GetSubstring', SourceString=g.getv('SpanTable'), StartIndex=start, Length=4))
    first, last = mul(g, metres(at), 100), mul(g, metres(g.math('Add_IntInt', A=at, B=4)), 100)
    wanted = both(g, ge(g, g.getv('Distance'), sub(g, first, D.ROLL_AHEAD)),
                  g.math('LessEqual_DoubleDouble', A=g.getv('Distance'), B=add(g, last, D.ROLL_BEHIND)))
    changed = g.math('NotEqual_BoolBool', A=g.getv('BootstrapPending', sector, SECTOR), B=wanted)
    g.setv('PinChanged', changed)
    set_on(g, sector, SECTOR, 'BootstrapPoint', centre)
    set_on(g, sector, SECTOR, 'BootstrapPending', wanted)
    gate(g, g.getv('PinChanged'))
    g.do(cls(SECTOR) + ':UpdateSector', self=sector)
    g.tail, g._side = loop, 'Completed'
    g.group('Next roll')
    g.setv('NextRoll', add(g, g.getv('Distance'), D.ROLL_STEP))
    g.finish()


def roll_city():
    """While driving, re-pin the sectors every ROLL_STEP (25 m) of travel."""
    g = G(CAR, 'RollCity')
    gate(g, both(g, g.getv('RouteReady'), NOT(g, g.getv('CityHold')), ge(g, g.getv('Distance'), g.getv('NextRoll'))))
    g.own('PreloadCity')
    g.finish()


def check_city():
    """Hold the car (at most 2.5 s) until every sector that wants to be loaded is visible; then the strikes start."""
    g = G(CAR, 'CheckCity')
    g.group('All sectors in')
    gate(g, g.getv('CityHold'))
    g.setv('CityReady', True)
    loop, sector = for_each_sector(g)
    g.setv('CityReady', both(g, g.getv('CityReady'), g.getv('Ready', sector, SECTOR)))
    g.tail, g._side = loop, 'Completed'
    g.group('Release the car')
    gate(g, either(g, g.getv('CityReady'), ge(g, g.getv('Clock'), g.getv('HoldUntil'))))
    g.setv('CityHold', False)
    g.setv('NextMeteor', add(g, g.getv('Clock'), D.FIRST_STRIKE))
    g.finish()


def check_destination():
    """Kept for the journey's ExitJob call; on rails the stop is reached by the rail itself."""
    g = G(CAR, 'CheckDestination'); g.setv('NearDestination', False); g.finish()


# ---- BP_Meteor --------------------------------------------------------------------------------------------------
def meteor_arm():
    g = G(MET, 'Arm')
    for n, v in [('Age', 0), ('Active', True), ('Impacted', False), ('Inside', False), ('Braced', False), ('Late', False),
                 ('NearStrike', False), ('Committed', False), ('Dodged', False), ('Result', 0), ('ResultTime', -10),
                 ('BraceAge', -1)]:
        g.setv(n, v)
    g.do(A + 'K2_SetActorLocation', NewLocation=g.arg('Position'), bSweep=False, bTeleport=True)
    g.do(SC + 'K2_SetRelativeLocation', self=g.getv('Shadow'), NewLocation=f'0,0,{D.FALL_HEIGHT}', bSweep=False, bTeleport=True)
    for name in ('Shadow', 'Ring', 'Trail'):
        g.do(SC + 'SetVisibility', self=g.getv(name), bNewVisibility=True, bPropagateToChildren=False)
    g.do(A + 'SetActorHiddenInGame', bNewHidden=False)
    g.do(GS + 'PlaySound2D', Sound='/Game/FoA/Audio/SFX/Dream/SFX_Dream_ReverseSwell_01.SFX_Dream_ReverseSwell_01', VolumeMultiplier=.3)
    g.finish()


def meteor_impact():
    """Brace strikes land on the car; a dodge strike hits unless the right side was committed."""
    g = G(MET, 'Impact'); g.setv('Impacted', True)
    car = g.getv('Car'); pos = g.f(A + 'K2_GetActorLocation'); at = g.f(A + 'K2_GetActorLocation', self=car)
    near = g.math('LessEqual_DoubleDouble', A=g.math('Vector_Distance2D', V1=pos, V2=at), B=240)
    brace = ieq(g, g.getv('Kind'), 0)
    clear = g.math('Greater_DoubleDouble', A=g.math('Vector_Distance2D', V1=pos, V2=at), B=D.DODGE_HIT)
    g.setv('Dodged', both(g, NOT(g, brace), clear)); g.setv('Committed', g.getv('Dodged'))
    g.setv('Inside', either(g, both(g, brace, near), both(g, NOT(g, brace), NOT(g, g.getv('Dodged')))))
    split = g.f(K + 'BreakVector', InVec=pos)
    clock = g.f(GS + 'GetTimeSeconds')
    color = g.math('MakeColor', R=(split[0], 'X'), G=(split[0], 'Y'), B=clock, A=1)
    g.do('/Script/Engine.KismetMaterialLibrary:SetVectorParameterValue', Collection=b.CITY_MPC, ParameterName='Impact0', ParameterValue=color)
    g.setv('ImpactStarted', clock)
    for name in ('Shadow', 'Ring', 'Trail'):
        g.do(SC + 'SetVisibility', self=g.getv(name), bNewVisibility=False, bPropagateToChildren=False)
    sand = cls('/Game/FoA/VFX/Sand/BPL_SandFX')
    g.do(sand + ':SpawnSandBurst', Location=pos, Scale=3.2)
    g.do(sand + ':SpawnSandBloom', Location=pos, Size=5.5, Seconds=2.6, Crumble=True)
    g.do(GS + 'PlaySound2D', Sound='/Game/FoA/Audio/SFX/Dream/SFX_Dream_LowImpact_01.SFX_Dream_LowImpact_01', VolumeMultiplier=.4)
    g.finish()


def meteor_resolve():
    g = G(MET, 'Resolve')
    clear = either(g, g.getv('Braced'), NOT(g, g.getv('Inside')))
    gate(g, both(g, g.getv('Active'), g.getv('Impacted'),
                 either(g, clear, g.getv('Late'), ge(g, g.getv('Age'), D.TELEGRAPH + D.LATE_GRACE))))
    cost = g.math('SelectInt', A=0, B=g.math('SelectInt', A=15, B=40, bPickA=g.getv('Late')), bPickA=clear)
    # 4 = perfect: braced in the last PERFECT seconds before impact (the near miss), 1 clean, 2 late, 3 hit
    perfect = both(g, g.getv('Braced'), ge(g, g.getv('BraceAge'), D.TELEGRAPH - D.PERFECT))
    g.setv('Result', g.math('SelectInt', A=g.math('SelectInt', A=4, B=1, bPickA=perfect),
                            B=g.math('SelectInt', A=2, B=3, bPickA=g.getv('Late')), bPickA=clear))
    g.setv('ResultTime', g.f(GS + 'GetTimeSeconds'))
    outcome = g.f('/Script/Engine.KismetStringLibrary:Conv_StringToName',
                  InString=g.f('/Script/Engine.KismetStringLibrary:Conv_IntToString', InInt=cost))
    g.do(cls(CAR) + ':ResolveHit', self=g.getv('Car'), Cost=cost, Outcome=outcome)
    g.own('Hide')
    g.finish()


def meteor_brace():
    """Space: inside the window is a clean brace; inside the grace after impact is late; early presses do nothing."""
    g = G(MET, 'AcceptBrace')
    gate(g, both(g, g.getv('Active'), ieq(g, g.getv('Kind'), 0), NOT(g, g.getv('Braced'))))
    age = g.getv('Age')
    window = both(g, ge(g, age, D.TELEGRAPH - D.BRACE_WINDOW), NOT(g, g.getv('Impacted')))
    br = g.branch(window); g.side(br); g.setv('Braced', True); g.setv('BraceAge', g.getv('Age')); g.side(br, False)
    gate(g, both(g, g.getv('Impacted'), g.math('LessEqual_DoubleDouble', A=g.getv('Age'), B=D.TELEGRAPH + D.LATE_GRACE)))
    g.setv('Late', True)
    g.finish()


# ---- WBP_L2Drive ------------------------------------------------------------------------------------------------
def set_qte():
    """One big key with a ring closing onto it; white fill on success, dark and shaken on a hit."""
    g = G(HUD, 'SetQTE')
    g.group('Show or hide')
    root = g.getv('QTE')
    hidden = g.branch(NOT(g, g.arg('Shown'))); g.side(hidden)
    g.do(W + 'SetVisibility', self=root, InVisibility='Collapsed')
    for name in STATUS:
        g.do(W + 'SetRenderOpacity', self=g.getv(name), InOpacity=1)
    g.side(hidden, False)
    g.do(W + 'SetVisibility', self=g.getv('QTE'), InVisibility='HitTestInvisible')
    g.do('/Script/UMG.TextBlock:SetText', self=g.getv('Txt_QTEKey'), InText=g.arg('Key'))
    # Steer keys draw the arrow image (T_UI_KeyArrow, the stops' key caps), not the font's fallback arrows (level2
    # lane, 2026-11-18). The glyph stays in the text, invisible, so the key data and comparisons are unchanged.
    key = g.f('/Script/Engine.KismetTextLibrary:Conv_TextToString', InText=g.arg('Key'))
    left = g.f(STR + 'EqualEqual_StrStr', A=key, B=KEYS[-1])
    arrow = either(g, g.f(STR + 'EqualEqual_StrStr', A=key, B=KEYS[1]), left)
    g.do(W + 'SetRenderOpacity', self=g.getv('Txt_QTEKey'), InOpacity=g.math('SelectFloat', A=0, B=1, bPickA=arrow))
    g.do(W + 'SetRenderOpacity', self=g.getv('Img_QTEArrow'), InOpacity=g.math('SelectFloat', A=1, B=0, bPickA=arrow))
    g.do(W + 'SetRenderTransformAngle', self=g.getv('Img_QTEArrow'), Angle=g.math('SelectFloat', A=180, B=0, bPickA=left))
    result = g.arg('Result')
    good, hit, perfect = either(g, ieq(g, result, 1), ieq(g, result, 4)), ieq(g, result, 3), ieq(g, result, 4)
    done = g.math('Greater_IntInt', A=result, B=0)
    t = clamp01(g, g.math('Divide_DoubleDouble', A=g.arg('ResultAge'), B=.5))
    closing = g.math('Lerp', A=2.6, B=1, Alpha=g.arg('Close'))
    burst = g.math('SelectFloat', A=2.6, B=1.9, bPickA=perfect)  # the near miss bursts wider
    settle = g.math('SelectFloat', A=g.math('Lerp', A=1, B=burst, Alpha=t), B=g.math('Lerp', A=1, B=.82, Alpha=t), bPickA=good)
    g.group('Closing ring')
    s = g.math('SelectFloat', A=settle, B=closing, bPickA=done)
    opacity = g.math('SelectFloat', A=sub(g, 1, t), B=g.math('Lerp', A=.45, B=1, Alpha=g.arg('Close')), bPickA=done)
    # A light ring over a wide dark one: the prompt reads on the bright road and on the black sky alike.
    for name in ('Img_QTEHalo', 'Img_QTERing'):
        g.do(W + 'SetRenderScale', self=g.getv(name), Scale=g.math('MakeVector2D', X=s, Y=s))
        g.do(W + 'SetRenderOpacity', self=g.getv(name), InOpacity=opacity)
    g.group('Key cap')
    fill = g.math('SelectColor', A='(R=1,G=1,B=1,A=0.96)', B=g.math('SelectColor', A='(R=0.02,G=0.02,B=0.02,A=0.94)',
                  B=g.math('SelectColor', A='(R=0.18,G=0.18,B=0.18,A=0.9)', B='(R=0,G=0,B=0,A=0.55)', bPickA=g.arg('Live')),
                  bPickA=hit), bPickA=good)
    g.do('/Script/UMG.Border:SetBrushColor', self=g.getv('Brd_QTEKey'), InBrushColor=fill)
    ink = g.math('SelectColor', A='(R=0,G=0,B=0,A=1)', B=g.math('SelectColor', A='(R=0.38,G=0.38,B=0.38,A=1)',
                 B='(R=1,G=1,B=1,A=1)', bPickA=hit), bPickA=good)
    g.do('/Script/UMG.Border:SetContentColorAndOpacity', self=g.getv('Brd_QTEKey'), InContentColorAndOpacity=ink)
    k = g.math('SelectFloat', A=g.math('Lerp', A=1.18, B=1, Alpha=t), B=g.math('SelectFloat', A=1.08, B=1, bPickA=g.arg('Live')), bPickA=good)
    g.do(W + 'SetRenderScale', self=g.getv('Brd_QTEKey'), Scale=g.math('MakeVector2D', X=k, Y=k))
    shake = mul(g, g.math('Sin', A=mul(g, g.arg('ResultAge'), 80)), mul(g, 14, sub(g, 1, t)))
    g.do(W + 'SetRenderTranslation', self=g.getv('Brd_QTEKey'),
         Translation=g.math('MakeVector2D', X=g.math('SelectFloat', A=shake, B=0, bPickA=hit), Y=0))
    g.group('Fade')
    fade = g.math('SelectFloat', A=clamp01(g, g.math('Divide_DoubleDouble', A=sub(g, .7, g.arg('ResultAge')), B=.2)),
                  B=clamp01(g, add(g, mul(g, g.arg('Close'), 5), .2)), bPickA=done)
    g.do(W + 'SetRenderOpacity', self=g.getv('QTE'), InOpacity=fade)
    g.group('Only the ring and key during a strike')
    for name in STATUS:
        g.do(W + 'SetRenderOpacity', self=g.getv(name), InOpacity=sub(g, 1, fade))
    g.finish()


GRAPHS = {'WBP_L2Drive.SetQTE': set_qte,
          'BP_L2RoadNetwork.ApplyTrafficLimit': apply_traffic_limit, 'BP_L2RoadNetwork.StepTraffic': step_traffic,
          'BP_Meteor.Arm': meteor_arm, 'BP_Meteor.Impact': meteor_impact, 'BP_Meteor.Resolve': meteor_resolve,
          'BP_Meteor.AcceptBrace': meteor_brace,
          'BP_L2Car.SetRail': b.set_rail, 'BP_L2Car.PlaceAtCheckpoint': place_at_checkpoint,
          'BP_L2Car.ChooseTarget': choose_target, 'BP_L2Car.PickRoute': pick_route, 'BP_L2Car.StartLeg': start_leg,
          'BP_L2Car.Move': move, 'BP_L2Car.TrackStrike': track_strike, 'BP_L2Car.Schedule': schedule,
          'BP_L2Car.ChangeLane': change_lane, 'BP_L2Car.Feedback': feedback, 'BP_L2Car.ResolveHit': resolve_hit,
          'BP_L2Car.UpdateFeel': update_feel, 'BP_L2Car.AutoPark': auto_park, 'BP_L2Car.RefreshHUD': refresh_hud,
          'BP_L2Car.CheckDestination': check_destination, 'BP_L2Car.UpdateCamera': update_camera,
          'BP_L2Car.SpawnProp': spawn_prop, 'BP_L2Car.FadeProp': fade_prop, 'BP_L2Car.ResetProps': reset_props,
          'BP_L2Car.Deactivate': deactivate, 'BP_L2Car.PreloadCity': preload_city, 'BP_L2Car.CheckCity': check_city,
          'BP_L2Car.RollCity': roll_city,
          'BP_L2RoadNetwork.TrafficSand': traffic_sand, 'BP_L2RoadNetwork.SignFlicker': sign_flicker,
          'BP_L2Car.DirLetterbox': director_call('DirLetterbox', 'SetLetterbox', Enabled='Enabled', Seconds='Seconds'),
          'BP_L2Car.DirGlitch': director_call('DirGlitch', 'TriggerGlitchBurst', Strength='Strength', Seconds='Seconds'),
          'BP_L2Car.DirStreak': director_call('DirStreak', 'PulseShiftStreak', Intensity='Intensity', Seconds='Seconds'),
          'BP_L2Car.FindRoomAudio': find_room_audio, 'BP_L2Car.UpdateMood': update_mood, 'BP_L2Car.ResetMood': reset_mood,
          'BP_L2Car.Reward': reward, 'BP_L2Car.SetPiece': set_piece, 'BP_L2Car.ReadSteer': read_steer,
          'BP_L2Car.FindDirector': find_director, 'BP_L2Car.WarmImpact': warm_impact,
          'BP_L2Car.DriveStep': drive_step}


# ---- structure: variables, functions, rails, widget, input ----------------------------------------------------------
def setup():
    for path, rows in ((CAR, CAR_VARS), (MET, MET_VARS), (ROAD, ROAD_VARS)):
        for name, typ, default in rows:  # blueprint_get_info can truncate its list: always the idempotent form
            b.call('blueprint_add_variable', path=path, variable_name=name, variable_type=typ, default_value=default,
                   category='Drive', update_existing=True)
    for path, funcs in ((CAR, CAR_FUNCS), (HUD, HUD_FUNCS), (ROAD, ROAD_FUNCS)):
        for name, inputs in funcs.items():  # the graph itself is the existence check (get_info can truncate)
            if not b.h.call('blueprint_inspect_graph', {'path': path, 'graph_name': name, 'limit': 1}).get('ok'):
                b.call('blueprint_add_function', path=path, function_name=name,
                       inputs=[dict(name=n, type=t) for n, t in inputs])
    adds = [(ROAD, f'Rail{i}', 'SplineComponent') for i in range(len(D.RAILS))]
    adds += [(ROAD, n, 'StaticMeshComponent') for n in ROAD_COMPONENTS] + [(MET, 'Trail', 'StaticMeshComponent')]
    have = {p: {c['name'] for c in b.call('blueprint_get_info', path=p).get('components', [])} for p in (ROAD, MET)}
    for path, name, kind in adds:
        if name in have[path]:
            continue
        r = b.h.call('blueprint_add_component', {'path': path, 'component_name': name,
                                                 'component_class_path': '/Script/Engine.' + kind})
        assert r.get('ok') or 'exist' in str(r.get('error', '')).lower(), (name, r)
    b.call('python_exec_file', path=Path(__file__).with_name('drive_rails_templates.py').as_posix(),
           resources=['asset:' + D.ROOT])


def spans():
    """The rolling preload's per-rail sector spans (drive_data.SPAN_TABLE) as BP_L2Car's SpanTable default."""
    b.call('blueprint_add_variable', path=CAR, variable_name='SpanTable', variable_type='string', category='Drive',
           update_existing=True)
    print('spans', b.call('blueprint_set_defaults', path=CAR, properties={'SpanTable': D.SPAN_TABLE}))
    b.call('blueprint_compile', path=CAR); b.call('asset_save', asset_paths=[CAR])


def roads():
    b.call('python_exec_file', path='P:/FoA/Tools/Unreal/level2/drive_setup.py', env={'FOA_DRIVE_SETUP': 'roads'},
           resources=['asset:' + D.ROOT])


def widget():
    """The QTE prompt, edited in place: a ring image and a key cap, centred above the car."""
    found = str(b.call('ui_query', path=HUD))
    if 'Img_QTERing' not in found:
        key = {'class': 'Border', 'name': 'Brd_QTEKey', 'slot_props': dict(horizontal_alignment='Center', vertical_alignment='Center'),
               'properties': {'Background': '(DrawAs=RoundedBox,TintColor=(SpecifiedColor=(R=1,G=1,B=1,A=1)),'
                              'OutlineSettings=(CornerRadii=(X=12,Y=12,Z=12,W=12),Color=(SpecifiedColor=(R=0.92,G=0.92,B=0.92,A=1)),'
                              'Width=3,RoundingType=FixedRadius))', 'BrushColor': [0, 0, 0, .55],
                              'Padding': '(Left=34,Top=8,Right=34,Bottom=12)', 'HorizontalAlignment': 'HAlign_Center',
                              'VerticalAlignment': 'VAlign_Center'},
               'children': [{'class': 'TextBlock', 'name': 'Txt_QTEKey', 'properties': {
                   'Text': 'Space', 'Justification': 'Center',
                   'Font': {'FontObject': '/Game/FoA/UI/Fonts/F_FoA_Display.F_FoA_Display', 'TypefaceFontName': 'ExtraBold', 'Size': 46},
                   'ColorAndOpacity': {'SpecifiedColor': [1, 1, 1, 1]}}}]}
        b.call('ui_build_tree', widget_blueprint_path=HUD, parent_widget_name='RootCanvas', tree=[{
            'class': 'Overlay', 'name': 'QTE', 'properties': {'Visibility': 'Collapsed', 'RenderTransformPivot': '(X=0.5,Y=0.5)'},
            'slot_props': dict(anchors_min=[.5, .5], anchors_max=[.5, .5], alignment=[.5, .5], position=[0, 30],
                               size=[360, 360], z_order=5, auto_size=False),
            'children': [{'class': 'Image', 'name': 'Img_QTERing',
                          'slot_props': dict(horizontal_alignment='Center', vertical_alignment='Center')}, key]}])
    if 'Img_QTEHalo' not in found:
        b.call('ui_build_tree', widget_blueprint_path=HUD, parent_widget_name='QTE', tree=[{
            'class': 'Image', 'name': 'Img_QTEHalo', 'slot_props': dict(horizontal_alignment='Center', vertical_alignment='Center')}])
        b.call('ui_move_element', widget_blueprint_path=HUD, widget_name='Img_QTEHalo', index=0)
    # Plain Slate circles (rounded box outlines): a wide dark halo under a thin light ring. The UI Lib's
    # material ring drew nothing in this widget (design-time render 23:50), and an outline needs no shader.
    for name, color, width in (('Img_QTEHalo', '(R=0.01,G=0.01,B=0.01,A=0.85)', 13), ('Img_QTERing', '(R=1,G=1,B=1,A=1)', 4)):
        b.call('ui_set_widget_properties', widget_blueprint_path=HUD, widget_name=name, properties={'Brush': (
            '(ImageSize=(X=300,Y=300),DrawAs=RoundedBox,ResourceObject=None,TintColor=(SpecifiedColor=(R=1,G=1,B=1,A=0)),'
            f'OutlineSettings=(CornerRadii=(X=150,Y=150,Z=150,W=150),Color=(SpecifiedColor={color}),Width={width},'
            'RoundingType=HalfHeightRadius))')})
    qte_arrow()
    for name in ('QTE', 'Img_QTEHalo', 'Img_QTERing', 'Brd_QTEKey', 'Txt_QTEKey', 'Img_QTEArrow'):
        b.call('ui_set_variable', widget_blueprint_path=HUD, widget_name=name, is_variable=True)
    # Rails take the driving keys away: the bar only names what is still yours.
    b.call('ui_set_widget_properties', widget_blueprint_path=HUD, widget_name='Txt_Controls',
           properties={'Text': 'C  Read the C.V.'}, slot_props=dict(size=[420, 38]))
    b.call('ui_set_widget_properties', widget_blueprint_path=HUD, widget_name='Brd_DriveControls',
           slot_props=dict(size=[470, 72]))
    b.call('ui_compile_widget', widget_blueprint_path=HUD)
    b.call('ui_save_widget', widget_blueprint_path=HUD)


def qte_arrow():
    """The key cap holds an overlay: the key's text, and over it the stops' arrow image for the steer keys."""
    if 'Img_QTEArrow' in str(b.call('ui_query', path=HUD)):
        return
    b.call('ui_reparent_element', widget_blueprint_path=HUD, widget_name='Txt_QTEKey', new_parent_name='QTE')
    b.call('ui_build_tree', widget_blueprint_path=HUD, parent_widget_name='Brd_QTEKey', tree=[{
        'class': 'Overlay', 'name': 'Ovl_QTEKey', 'children': [{
            'class': 'Image', 'name': 'Img_QTEArrow', 'slot_props': dict(horizontal_alignment='Center', vertical_alignment='Center'),
            'properties': {'Brush': '(ImageSize=(X=46,Y=46),DrawAs=Image,ResourceObject="/Game/FoA/UI/Textures/T_UI_KeyArrow.T_UI_KeyArrow")',
                           'RenderOpacity': 0, 'RenderTransformPivot': '(X=0.5,Y=0.5)', 'Visibility': 'HitTestInvisible'}}]}])
    b.call('ui_reparent_element', widget_blueprint_path=HUD, widget_name='Txt_QTEKey', new_parent_name='Ovl_QTEKey',
           slot_props=dict(horizontal_alignment='Center', vertical_alignment='Center'))
    b.call('ui_move_element', widget_blueprint_path=HUD, widget_name='Txt_QTEKey', index=0)
    b.call('ui_set_variable', widget_blueprint_path=HUD, widget_name='Img_QTEArrow', is_variable=True)


DOT = '/Game/FoA/UI/Textures/T_UI_SoftDot.T_UI_SoftDot'
UI_FONT = '/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
INK, SUB = 0.87, 0.43  # #F0F0F0 and #B0B0B0 in linear, as l2_look.py
STATUS = ('Brd_DriveStatus', 'Txt_Place', 'Txt_Composure', 'Txt_Cue', 'Txt_Employability')
FLAT = {'Translation': {'X': 0, 'Y': 0}, 'Scale': {'X': 1, 'Y': 1}, 'Shear': {'X': 0, 'Y': 0}, 'Angle': 0.0}  # the ink tilt off


def hud_look():
    """No ink plates: small type over one soft dark falloff (T_UI_SoftDot), the destination as a quiet title,
    Composure and the distance as small plain numbers, the C.V. hint (only while stopped) over its own small halo."""
    def setp(name, props=None, slot=None):
        r = b.h.call('ui_set_widget_properties', {'widget_blueprint_path': HUD, 'widget_name': name,
                                                   'properties': props or {}, 'slot_props': slot or {}})
        assert r.get('ok') and not (r.get('data') or {}).get('failed_properties'), (name, r)

    def text(typeface, size, v):
        return {'Font': {'FontObject': UI_FONT, 'TypefaceFontName': typeface, 'Size': size},
                'ColorAndOpacity': {'SpecifiedColor': [v, v, v, 1]}, 'ShadowOffset': {'X': 0, 'Y': 2},
                'ShadowColorAndOpacity': [0, 0, 0, 0.55], 'RenderTransform': FLAT}

    def halo(alpha):
        return {'Background': {'ResourceObject': DOT, 'DrawAs': 'Image', 'TintColor': {'SpecifiedColor': [0, 0, 0, 1]}},
                'BrushColor': [0, 0, 0, alpha], 'RenderTransform': FLAT, 'Visibility': 'HitTestInvisible'}

    for name in ('DriveFrame', 'DrivePlaceBack', 'DrivePlaceTag', 'Icon_Composure', 'Icon_Employability'):
        setp(name, {'Visibility': 'Collapsed'})
    setp('Bar_L2Employability', {'RenderOpacity': 0.0})  # RefreshL2Progress still toggles it; the number says enough
    setp('Brd_DriveStatus', halo(0.9), dict(position=[240, 80], size=[1150, 760], alignment=[.5, .5], z_order=0))
    setp('Txt_Place', text('SemiBold', 30, INK), dict(position=[52, 34], size=[600, 44], alignment=[0, 0], z_order=2))
    setp('Txt_Composure', text('Medium', 20, SUB), dict(position=[52, 82], size=[190, 30], alignment=[0, 0], z_order=2))
    setp('Txt_Cue', text('Medium', 20, SUB), dict(position=[236, 82], size=[360, 30], alignment=[0, 0], z_order=2))
    setp('Txt_Employability', text('Medium', 18, SUB), dict(position=[52, 112], size=[460, 28], alignment=[0, 0], z_order=2))
    setp('Brd_DriveControls', dict(halo(0.7), RenderOpacity=0.0), dict(position=[0, -60], size=[1300, 280], alignment=[.5, .5], z_order=0))
    setp('Txt_Controls', dict(text('Medium', 21, SUB), Text='Steer with A and D or the stick. C or D-pad left to read the C.V.',
                              Justification='Center', RenderOpacity=0.0),
         dict(position=[0, -60], size=[900, 32], alignment=[.5, .5], z_order=2))
    for name in STATUS + ('Txt_Controls', 'Brd_DriveControls'):
        b.call('ui_set_variable', widget_blueprint_path=HUD, widget_name=name, is_variable=True)
    b.call('ui_compile_widget', widget_blueprint_path=HUD)
    b.call('ui_save_widget', widget_blueprint_path=HUD)


def inputs():
    b.call('python_exec_file', path=str(Path(__file__).with_name('drive_rails_input.py')).replace('\\', '/'),
           resources=['asset:' + D.ROOT])


def graphs():
    for name, fn in GRAPHS.items():
        b.h.renew_all(D.OWNER, 240)
        print('==', name, flush=True)
        fn()


STEPS = dict(setup=setup, spans=spans, roads=roads, widget=widget, look=hud_look, input=inputs, graphs=graphs, **GRAPHS)
STEPS['all'] = lambda: [STEPS[s]() for s in ('setup', 'spans', 'roads', 'widget', 'look', 'input', 'graphs')]


def layout():
    """The house layout pass (bp_layout: rows, spacing, title-only bubbles) over this builder's graphs only."""
    import bp_layout
    for path in (MET, ROAD, HUD, CAR):
        prefix = path.rsplit('/', 1)[1] + '.'
        names = [k[len(prefix):] for k in GRAPHS if k.startswith(prefix)]
        b.h.renew_all(D.OWNER, 300)
        result = bp_layout.drive(path, graph_names=names)
        print('layout', prefix, len(names), 'graphs', {k: result.get(k) for k in ('applied', 'error', 'failed')}, flush=True)


STEPS['layout'] = layout
STEPS['qte_arrow'] = lambda: (qte_arrow(), b.call('blueprint_compile', path=HUD, save=True), set_qte())


def shots():
    """Whole-graph PNGs of the key rails graphs (FoAGraphTools), for review and the devlog."""
    import time
    out = Path('P:/FoA/Saved/GraphShots')
    out.mkdir(parents=True, exist_ok=True)
    wanted = os.environ.get('DRIVE_SHOTS', 'DriveStep,Move,Schedule,SpawnProp,Feedback,Resolve,SetQTE,StepTraffic').split(',')
    owner = {'Resolve': MET, 'SetQTE': HUD, 'StepTraffic': ROAD}
    for path, graph in ((owner.get(g, CAR), g) for g in wanted):
        png = out / f'drive_{graph}.png'
        for attempt in range(3):  # the async capture sometimes paints only the grid: look, and retake
            stamp = time.time()
            b.call('python_exec_file', path='P:/FoA/Tools/Unreal/ui/capture_graph.py',
                   env={'FOA_ASSET': path, 'FOA_GRAPH': graph, 'FOA_PNG': png.as_posix()}, resources=['asset:' + path])
            while not (png.exists() and png.stat().st_mtime >= stamp) and time.time() - stamp < 20:
                time.sleep(.2)
            time.sleep(2)  # let the renderer finish before the next graph opens
            from PIL import Image, ImageStat
            if png.exists() and ImageStat.Stat(Image.open(png).convert('L')).stddev[0] > 8:
                break
        print('shot', png, png.exists(), attempt)
    for path in (CAR, MET, ROAD):  # a capture can dirty its Blueprint: leave each one clean
        b.call('blueprint_compile', path=path); b.call('asset_save', asset_paths=[path])
    b.call('ui_compile_widget', widget_blueprint_path=HUD); b.call('ui_save_widget', widget_blueprint_path=HUD)


STEPS['shots'] = shots


def run(step):
    import editor_lock
    owner = os.environ.get('HAYBA_AGENT_ID', 'drive')
    os.environ.update(FOA_AGENT=owner, HAYBA_AGENT_ID=owner); D.OWNER = owner
    token = editor_lock.acquire(owner, wait_s=900, ttl=300, areas=[D.ROOT])
    if token:
        os.environ['FOA_LEASE'] = token
    try:
        assert not b.call('editor_get_state')['pie_running'], 'Stop PIE first'
        names = [n for n in STEPS if n == step or n.startswith(step + '.')] if step not in STEPS else [step]
        for name in names:
            STEPS[name]()
    finally:
        # Never leave a drive Blueprint failing to compile between leases.
        for path in (ROAD, CAR, MET, HUD):
            r = b.h.call('blueprint_compile', {'path': path})
            print('compile', path.rsplit('/', 1)[1], (r.get('data') or {}).get('error_count'), flush=True)
        editor_lock.release(owner)


if __name__ == '__main__':
    run(sys.argv[1])
