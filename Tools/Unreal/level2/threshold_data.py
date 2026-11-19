"""Shared authored timings and coordinates, centimetres and seconds."""
from math import atan, degrees
import os

OWNER = os.environ.get('FOA_AGENT','dream-transition')
ROOT = '/Game/FoA/Level2/Transition'
BP = ROOT + '/BP_DreamThreshold'
LS = ROOT + '/LS_DreamThreshold'
FALL = ROOT + '/LS_DreamFall'
DREAM_MAP = '/Game/FoA/Level2/Maps/L_L2_DreamTest'
CITY_MAP = '/Game/FoA/Level2/Maps/L_L2_CityStream'
OFFSET = (20000, -80000, 0)
# These marks require an in-editor clearance check against Dream A before placement.
ENTRY = (20000, -80200, 92)  # 60 cm in from -80260: a DreamA_Splats surface sat a few cm ahead of the old spot and walled off the arrival view (coordinator 2026-11-18)
EXIT = (20000, -79660, 92)
THRESHOLD_SECONDS = 9.0
ASSEMBLY_SECONDS = 3.0
PATH_MIN, PATH_MAX = 12.0, 45.0  # MAX strengthens guidance; it never completes the walk.
PATH_SPEED, PATH_HEAVY = 80.0, 30.0  # calm walk; the torment slows him toward HEAVY (wading through dread)
BREATH_HOLD, BREATH_RELEASE = 2.4, .8
BEAT_Y = (-20, 200)
SAFE_Y = (-240, -80, 180)
GUIDE_Y = (-220, -110, 0, 110, 220, 310)

# The torment: his anxieties rise out of black sand beside the path (Lux3D splats, M_SplatMesh static mode), loom,
# and crumble when he breathes. Positions are actor-relative cm (actor at OFFSET, +Y toward EXIT).
DREAM = '/Game/FoA/Level2/Dream'
FEAR_DIR = DREAM + '/Fears'
SPLATS = '/Game/FoA/VFX/Splats'
HAND = FEAR_DIR + '/SM_DreamHand/SM_DreamHand/StaticMeshes/SM_DreamHand'
FEARS = (  # component, mesh, material, location, yaw, scale, detail mode (LOW draws on every scalability tier)
    ('FearClock', SPLATS + '/Meshes/fear_of_adulthood_clock', FEAR_DIR + '/MI_DreamFear_Clock', (-90, 110, 110), 200, 4.5, 'LOW'),
    ('FearCrow', FEAR_DIR + '/SM_DreamCrow/SM_DreamCrow/StaticMeshes/SM_DreamCrow', FEAR_DIR + '/MI_DreamFear_Crow',
     (120, 220, 90), 250, 0.8, 'LOW'),  # side on to him: the crow reads in profile only
    ('FearHand0', HAND, FEAR_DIR + '/MI_DreamFear_Hand', (-45, -60, -6), 180, 2.4, 'LOW'),
    ('FearHand1', HAND, FEAR_DIR + '/MI_DreamFear_Hand', (45, -60, -6), 180, 2.3, 'MEDIUM'),
    ('FearHourglass', FEAR_DIR + '/SM_DreamHourglass/SM_DreamHourglass/StaticMeshes/SM_DreamHourglass',
     FEAR_DIR + '/MI_DreamFear_Hourglass', (-75, 250, 40), 180, 3.4, 'LOW'),
    ('FearBriefcase', FEAR_DIR + '/SM_DreamBriefcase/SM_DreamBriefcase/StaticMeshes/SM_DreamBriefcase', FEAR_DIR + '/MI_DreamFear_Briefcase',
     (115, 250, 120), 146, 3.0, 'LOW'),
    ('FearHand2', HAND, FEAR_DIR + '/MI_DreamFear_Hand', (-40, 185, -6), 180, 2.4, 'LOW'),
    ('FearHand3', HAND, FEAR_DIR + '/MI_DreamFear_Hand', (40, 185, -6), 180, 2.3, 'HIGH'),
)
FEAR_INDEX = {f[0]: i for i, f in enumerate(FEARS)}
SEGMENTS = (FEARS[:4], FEARS[4:])  # each breath crumbles one segment
HAND_AHEAD = {'FearHand0': (-50, 185), 'FearHand1': (50, 170), 'FearHand2': (-45, 125), 'FearHand3': (45, 115)}  # (x, y) from the pawn
# Stage k fires once StageAge >= STAGE_GAP[0] and he has walked to y, or StageAge >= STAGE_GAP[1] if he stands still.
# (y, fears that rise, pressure goal, thought); fears None = the headache (breath beat). Segment two puts the hourglass
# at the foot of the bed beside EXIT and the briefcase across from it, and raises hands in the doorway.
# Facing +Y, +X is on his left: the bed and the bench are on +X, a wall juts in at x -60..-230 near EXIT.
# The clock, the crow, the hourglass and the briefcase hang in the air: black against the bright arches reads as a shape,
# black against the red carpet did not (run_20261118_0043).
STAGE_GAP = (.6, 4.0)
STAGES = ((-260, ('FearClock',), .3, ''), (-160, ('FearCrow',), .55, "Don't stop. Don't stop."),
          (-90, ('FearHand0', 'FearHand1'), .8, ''), (BEAT_Y[0], None, 1., ''),
          (-15, ('FearBriefcase',), .4, ''), (35, ('FearHourglass',), .65, ''),  # rise 2.5 m away: seen whole
          (130, ('FearHand2', 'FearHand3'), .85, ''), (BEAT_Y[1], None, 1., ''))
RISE_SECONDS, CRUMBLE_SECONDS = 1.4, 1.9
CALM_PRESSURE = .3  # pressure while he breathes out
MAX_STEP = .35  # longest frame a tick may count: a hitch never grants a whole breath, and 3 fps QA bursts still pace in real time
GLITCH = (.45, .9)  # BP_DreamDirector.TriggerGlitchBurst at a headache: strength, seconds (the glyph must stay readable)
PULSE_RADIUS = 300  # the room gives way this far around him at a headache; the walls and the fears stay in view
SHAKE_EVERY, SHAKE_FROM = .6, .45  # tremor retrigger period and the pressure it starts at
EXIT_FRAME = (('ExitDoor', (-52, 352, 108), (.06, .06, 2.16)), ('ExitDoorR', (52, 352, 108), (.06, .06, 2.16)),
              ('ExitLintel', (0, 352, 216), (1.1, .06, .06)))  # a glowing white door frame at the end of the marks (cube scale)
EXIT_TEXT = ((0, 345, 238), 44)  # the EXIT word above it (location, world size)
FALL_SECONDS = 8.0
CITY_LAND_TIMEOUT = 60.0

def proof_budget(case,realtime=False):
    # Current earned city arrival takes43s; leave each downstream stage its own bounded window.
    return {'cv':116,'stops':84,'drive':70,'job':145,'job_campaign':370,'job_gamepad':650,'job_shift_visual':320,'job_ending':110,'phone':70,'paper':70,'reset':70,'ending':90,
            'cleanup':60,'debug':60,'shockwave':70,'streaming':95}.get(case,57 if realtime else 51)

def dolly_keys():
    """Keep doorway size stable as focal length and distance change together."""
    return [(t, focal, focal * 6) for t, focal in ((3, 24), (4, 35), (5.4, 70), (6.1, 18), (6.7, 24))]

def fall_due(age, remaining, outside=False, completed=0, breathing=False):
    return not outside and not breathing and completed==2 and age>=PATH_MIN and remaining<=100

def selftest():
    assert not fall_due(1000,0) and not fall_due(1000,10000,completed=2)
    assert not fall_due(11.99,0,completed=2) and fall_due(12,0,completed=2)
    assert not fall_due(1000,0,True,completed=2) and not fall_due(1000,0,completed=2,breathing=True)
    ratios=[f/d for _,f,d in dolly_keys()]
    assert max(ratios)-min(ratios)<1e-12
    fovs=[degrees(2*atan(36/(2*f))) for _,f,_ in dolly_keys()]
    assert max(fovs)-min(fovs)>60
    assert BREATH_HOLD>1 and BREATH_RELEASE>0
    print('threshold timing/exit and dolly projection checks passed')

if __name__ == '__main__':
    selftest()
