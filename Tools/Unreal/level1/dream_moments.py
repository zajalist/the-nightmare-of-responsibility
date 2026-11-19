"""level1 lane, round 3: two small dream moments for the T2-T5 search, in one lean actor (no new art, no text).
  The school backpack wants him to leave: while he searches (T2 to T5), each time both its spot and its next spot are
  out of his view (more than about 70 deg off his look) and he is not standing on the next spot, it is somewhere else,
  one step closer to the door: by the commode, by the wardrobe, then under the coat rail at the door. At most one step
  every 6 s, three steps a morning, a faint floor creak where it lands. It stays by the door (T7 moves the door away,
  so it waits at the wrong wall). A new morning puts it back by the desk.
  The wardrobe stirs: the first time he comes within 2 m of the standing wardrobe (T2 to T5), it rattles and creaks
  once, quietly (foreshadowing the fall at T6; its Look line is already "Has it always leaned like that?").
BP_L1DreamMoments (/Game/FoA/Gameplay/Ambient): BeginPlay finds the director, makes the backpack movable, keeps its
home, and starts a 0.25 s timer on Step. Readable for QA: Moves (int), bRattled (bool).
  $env:HAYBA_AGENT_ID='level1'; python Tools/Unreal/level1/dream_moments.py create|graph   (inside an asset lease)
  FOA_ACTORS_NEW=L1_DreamMoments FOA_ACTORS=Dress_Lux3D_Backpack python Tools/Unreal/ue_remote.py Tools/Unreal/level1/dream_moments_place.py"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
os.environ.setdefault('HAYBA_AGENT_ID', 'level1')
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

BP = '/Game/FoA/Gameplay/Ambient/BP_L1DreamMoments'
DIR_C = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
GS, KS, K = '/Script/Engine.GameplayStatics:', '/Script/Engine.KismetSystemLibrary:', '/Script/Engine.KismetMathLibrary:'
A, PCM = '/Script/Engine.Actor:', '/Script/Engine.PlayerCameraManager:'
SND = '/Game/FoA/Audio/MetaSounds/'
WAYPOINTS = ('-30,268,18', '95,262,18', '338,165,18')  # floor spots clear of the commode, the wardrobe and the door swing
UNSEEN_DOT = 0.35   # cos of about 70 deg from his look
COOLDOWN = 6.0
NEAR_WARDROBE = 200.0


def call(cmd, **a):
    r = h.call(cmd, a, owner='level1', timeout=120)
    assert r.get('ok'), (cmd, str(r)[:400])
    return r.get('data', {})


def create():
    if not h.call('blueprint_get_info', dict(path=BP), owner='level1').get('ok'):
        call('blueprint_create', name='BP_L1DreamMoments', package_path=BP, parent_class_path='/Script/Engine.Actor')
    for name, kind, default, edit in (
            ('Director', 'object:' + DIR_C, '', False), ('Backpack', 'object:/Script/Engine.Actor', '', True),
            ('Wardrobe', 'object:/Script/Engine.Actor', '', True), ('Home', 'transform', '', False),
            ('Moves', 'int', '0', False), ('LastMove', 'float', '-100', False), ('bRattled', 'bool', 'false', False)):
        call('blueprint_add_variable', path=BP, variable_name=name, variable_type=kind, container='none',
             **({'default_value': default} if default else {}), category='Dream moments', instance_editable=edit,
             update_existing=True)
    print('CREATE', call('blueprint_compile', path=BP, save=True).get('saved'))


def graph():
    ns, _ = inspect(BP, 'EventGraph')
    begin = find(ns, 'Event BeginPlay')
    old = [n['node_id'] for n in ns if n['title'] not in ('Event BeginPlay', 'Event Tick', 'Event ActorBeginOverlap')]
    b = Batch(BP, 'EventGraph')
    if old:
        b.ops.append(dict(op='remove', node_ids=old))
    # BeginPlay
    b.fn('dir', GS + 'GetActorOfClass', 200, 200, ActorClass=DIR_C)
    b.set('setdir', 'Director', 400, 0); b.link('dir', 'ReturnValue', 'setdir', 'Director')
    b.get('bp0', 'Backpack', 400, 300)
    b.fn('root', A + 'K2_GetRootComponent', 600, 300); b.link('bp0', 'Backpack', 'root', 'self')
    b.fn('movable', '/Script/Engine.SceneComponent:SetMobility', 700, 0, NewMobility='Movable'); b.link('root', 'ReturnValue', 'movable', 'self')
    b.fn('homexf', A + 'GetTransform', 900, 300); b.link('bp0', 'Backpack', 'homexf', 'self')
    b.set('sethome', 'Home', 1000, 0); b.link('homexf', 'ReturnValue', 'sethome', 'Home')
    b.fn('timer', KS + 'K2_SetTimer', 1300, 0, FunctionName='Step', Time=0.25, bLooping='true')
    b.chain(begin, 'dir', 'setdir', 'movable', 'sethome', 'timer')
    b.comment('Find the director, free the backpack, start', ['dir', 'setdir', 'bp0', 'root', 'movable', 'homexf', 'sethome', 'timer'])
    # Step: guards
    Y = 900
    b.node('step', 'custom_event', 0, Y, event_name='Step')
    b.get('d', 'Director', 0, Y + 250); b.get('bp', 'Backpack', 0, Y + 400)
    b.fn('dv', KS + 'IsValid', 200, Y + 250); b.link('d', 'Director', 'dv', 'Object')
    b.fn('bv', KS + 'IsValid', 200, Y + 400); b.link('bp', 'Backpack', 'bv', 'Object')
    b.fn('valid', K + 'BooleanAND', 400, Y + 300); b.link('dv', 'ReturnValue', 'valid', 'A'); b.link('bv', 'ReturnValue', 'valid', 'B')
    b.node('brvalid', 'branch', 300, Y); b.link('valid', 'ReturnValue', 'brvalid', 'Condition'); b.chain('step', 'brvalid')
    b.get('beat', 'BeatIndex', 500, Y + 500, DIR_C); b.link('d', 'Director', 'beat', 'self')
    b.fn('morning', K + 'Less_IntInt', 700, Y + 500, B=2); b.link('beat', 'BeatIndex', 'morning', 'A')
    b.node('brmorning', 'branch', 600, Y); b.link('morning', 'ReturnValue', 'brmorning', 'Condition'); b.chain('brvalid', 'brmorning')
    # Reset on a new morning (only if something happened)
    b.get('m0', 'Moves', 800, Y - 300); b.get('r0', 'bRattled', 800, Y - 200)
    b.fn('moved', K + 'Greater_IntInt', 1000, Y - 300, B=0); b.link('m0', 'Moves', 'moved', 'A')
    b.fn('dirty', K + 'BooleanOR', 1200, Y - 250); b.link('moved', 'ReturnValue', 'dirty', 'A'); b.link('r0', 'bRattled', 'dirty', 'B')
    b.node('brdirty', 'branch', 900, Y - 500); b.link('dirty', 'ReturnValue', 'brdirty', 'Condition'); b.link('brmorning', 'then', 'brdirty', 'execute')
    b.get('home', 'Home', 1200, Y - 400)
    b.fn('back', A + 'K2_SetActorTransform', 1200, Y - 500, bSweep='false', bTeleport='true')
    b.link('bp', 'Backpack', 'back', 'self'); b.link('home', 'Home', 'back', 'NewTransform')
    b.set('m0set', 'Moves', 1500, Y - 500); b.pin('m0set', 'Moves', 0)
    b.set('r0set', 'bRattled', 1750, Y - 500); b.pin('r0set', 'bRattled', 'false')
    b.chain('brdirty', 'back', 'm0set', 'r0set')
    b.comment('A new morning: backpack home', ['m0', 'r0', 'moved', 'dirty', 'brdirty', 'home', 'back', 'm0set', 'r0set'])
    # Searching: T2 to T5
    b.fn('search', K + 'LessEqual_IntInt', 800, Y + 600, B=5); b.link('beat', 'BeatIndex', 'search', 'A')
    b.node('brsearch', 'branch', 900, Y); b.link('search', 'ReturnValue', 'brsearch', 'Condition'); b.link('brmorning', 'else', 'brsearch', 'execute')
    b.fn('pawn', GS + 'GetPlayerPawn', 900, Y + 750, PlayerIndex=0)
    b.fn('pawnat', A + 'K2_GetActorLocation', 1100, Y + 750); b.link('pawn', 'ReturnValue', 'pawnat', 'self')
    # The wardrobe stirs once
    b.get('w', 'Wardrobe', 1200, Y + 300)
    b.fn('wv', KS + 'IsValid', 1400, Y + 300); b.link('w', 'Wardrobe', 'wv', 'Object')
    b.fn('wat', A + 'K2_GetActorLocation', 1400, Y + 450); b.link('w', 'Wardrobe', 'wat', 'self')
    b.fn('wdist', K + 'Vector_Distance', 1600, Y + 450); b.link('wat', 'ReturnValue', 'wdist', 'V1'); b.link('pawnat', 'ReturnValue', 'wdist', 'V2')
    b.fn('wnear', K + 'Less_DoubleDouble', 1800, Y + 450, B=NEAR_WARDROBE); b.link('wdist', 'ReturnValue', 'wnear', 'A')
    b.get('r1', 'bRattled', 1600, Y + 300)
    b.fn('notyet', K + 'Not_PreBool', 1800, Y + 300); b.link('r1', 'bRattled', 'notyet', 'A')
    b.fn('w1', K + 'BooleanAND', 2000, Y + 300); b.link('wv', 'ReturnValue', 'w1', 'A'); b.link('notyet', 'ReturnValue', 'w1', 'B')
    b.fn('w2', K + 'BooleanAND', 2200, Y + 350); b.link('w1', 'ReturnValue', 'w2', 'A'); b.link('wnear', 'ReturnValue', 'w2', 'B')
    b.node('brstir', 'branch', 1200, Y); b.link('w2', 'ReturnValue', 'brstir', 'Condition'); b.chain('brsearch', 'brstir')
    b.fn('rattle', GS + 'PlaySoundAtLocation', 1500, Y - 100, Sound=SND + 'Wardrobe/S_Wardrobe_Rattle.S_Wardrobe_Rattle', VolumeMultiplier=0.55)
    b.link('wat', 'ReturnValue', 'rattle', 'Location')
    b.fn('creak', GS + 'PlaySoundAtLocation', 1800, Y - 100, Sound=SND + 'Wardrobe/S_Wardrobe_Creak.S_Wardrobe_Creak', VolumeMultiplier=0.7)
    b.link('wat', 'ReturnValue', 'creak', 'Location')
    b.set('r1set', 'bRattled', 2100, Y - 100); b.pin('r1set', 'bRattled', 'true')
    b.chain('brstir', 'rattle', 'creak', 'r1set')
    b.comment('The wardrobe stirs once', ['w', 'wv', 'wat', 'wdist', 'wnear', 'r1', 'notyet', 'w1', 'w2', 'brstir', 'rattle', 'creak', 'r1set'])
    # The backpack moves when he is not looking
    X = 2500
    b.get('m1', 'Moves', X, Y + 300)
    b.fn('is1', K + 'EqualEqual_IntInt', X + 200, Y + 300, B=1); b.link('m1', 'Moves', 'is1', 'A')
    b.fn('is2', K + 'EqualEqual_IntInt', X + 200, Y + 400, B=2); b.link('m1', 'Moves', 'is2', 'A')
    b.fn('wp01', K + 'SelectVector', X + 400, Y + 300, A=WAYPOINTS[1], B=WAYPOINTS[0]); b.link('is1', 'ReturnValue', 'wp01', 'bPickA')
    b.fn('wp', K + 'SelectVector', X + 600, Y + 350, A=WAYPOINTS[2]); b.link('wp01', 'ReturnValue', 'wp', 'B'); b.link('is2', 'ReturnValue', 'wp', 'bPickA')
    b.fn('left', K + 'Less_IntInt', X + 200, Y + 550, B=len(WAYPOINTS)); b.link('m1', 'Moves', 'left', 'A')
    b.fn('now', GS + 'GetTimeSeconds', X, Y + 700)
    b.get('lm', 'LastMove', X, Y + 850)
    b.fn('since', K + 'Subtract_DoubleDouble', X + 200, Y + 700); b.link('now', 'ReturnValue', 'since', 'A'); b.link('lm', 'LastMove', 'since', 'B')
    b.fn('rested', K + 'Greater_DoubleDouble', X + 400, Y + 700, B=COOLDOWN); b.link('since', 'ReturnValue', 'rested', 'A')
    b.fn('pcm', GS + 'GetPlayerCameraManager', X, Y + 1000, PlayerIndex=0)
    b.fn('eye', PCM + 'GetCameraLocation', X + 200, Y + 1000); b.link('pcm', 'ReturnValue', 'eye', 'self')
    b.fn('look', PCM + 'GetCameraRotation', X + 200, Y + 1150); b.link('pcm', 'ReturnValue', 'look', 'self')
    b.fn('fwd', K + 'GetForwardVector', X + 400, Y + 1150); b.link('look', 'ReturnValue', 'fwd', 'InRot')
    b.fn('bpat', A + 'K2_GetActorLocation', X + 200, Y + 1300); b.link('bp', 'Backpack', 'bpat', 'self')
    for ref, src, src_pin, y in (('cur', 'bpat', 'ReturnValue', 1300), ('nxt', 'wp', 'ReturnValue', 1450)):
        b.fn(ref + 'to', K + 'Subtract_VectorVector', X + 400, Y + y); b.link(src, src_pin, ref + 'to', 'A'); b.link('eye', 'ReturnValue', ref + 'to', 'B')
        b.fn(ref + 'dir', K + 'Normal', X + 600, Y + y); b.link(ref + 'to', 'ReturnValue', ref + 'dir', 'A')
        b.fn(ref + 'dot', K + 'Dot_VectorVector', X + 800, Y + y); b.link('fwd', 'ReturnValue', ref + 'dot', 'A'); b.link(ref + 'dir', 'ReturnValue', ref + 'dot', 'B')
        b.fn(ref + 'off', K + 'Less_DoubleDouble', X + 1000, Y + y, B=UNSEEN_DOT); b.link(ref + 'dot', 'ReturnValue', ref + 'off', 'A')
    b.fn('room', K + 'Vector_Distance', X + 800, Y + 1600); b.link('wp', 'ReturnValue', 'room', 'V1'); b.link('pawnat', 'ReturnValue', 'room', 'V2')
    b.fn('clear', K + 'Greater_DoubleDouble', X + 1000, Y + 1600, B=120); b.link('room', 'ReturnValue', 'clear', 'A')
    b.fn('c1', K + 'BooleanAND', X + 1200, Y + 600); b.link('left', 'ReturnValue', 'c1', 'A'); b.link('rested', 'ReturnValue', 'c1', 'B')
    b.fn('c2', K + 'BooleanAND', X + 1200, Y + 1350); b.link('curoff', 'ReturnValue', 'c2', 'A'); b.link('nxtoff', 'ReturnValue', 'c2', 'B')
    b.fn('c3', K + 'BooleanAND', X + 1400, Y + 900); b.link('c1', 'ReturnValue', 'c3', 'A'); b.link('c2', 'ReturnValue', 'c3', 'B')
    b.fn('c4', K + 'BooleanAND', X + 1600, Y + 1000); b.link('c3', 'ReturnValue', 'c4', 'A'); b.link('clear', 'ReturnValue', 'c4', 'B')
    b.node('brmove', 'branch', X + 1300, Y); b.link('c4', 'ReturnValue', 'brmove', 'Condition')
    b.link('brstir', 'else', 'brmove', 'execute'); b.link('r1set', 'then', 'brmove', 'execute')
    b.fn('hop', A + 'K2_SetActorLocation', X + 1600, Y, bSweep='false', bTeleport='true')
    b.link('bp', 'Backpack', 'hop', 'self'); b.link('wp', 'ReturnValue', 'hop', 'NewLocation')
    b.fn('thud', GS + 'PlaySoundAtLocation', X + 1900, Y, Sound=SND + 'Creaks/S_Creaks_Floor.S_Creaks_Floor', VolumeMultiplier=0.45)
    b.link('wp', 'ReturnValue', 'thud', 'Location')
    b.fn('inc', K + 'Add_IntInt', X + 2100, Y + 200, B=1); b.link('m1', 'Moves', 'inc', 'A')
    b.set('m1set', 'Moves', X + 2200, Y); b.link('inc', 'ReturnValue', 'm1set', 'Moves')
    b.set('lmset', 'LastMove', X + 2500, Y); b.link('now', 'ReturnValue', 'lmset', 'LastMove')
    b.chain('brmove', 'hop', 'thud', 'm1set', 'lmset')
    b.comment('The backpack moves when unseen', ['m1', 'is1', 'is2', 'wp01', 'wp', 'left', 'now', 'lm', 'since', 'rested', 'pcm', 'eye',
                                              'look', 'fwd', 'bpat', 'curto', 'curdir', 'curdot', 'curoff', 'nxtto', 'nxtdir', 'nxtdot',
                                              'nxtoff', 'room', 'clear', 'c1', 'c2', 'c3', 'c4', 'brmove', 'hop', 'thud', 'inc', 'm1set', 'lmset'])
    b.comment('Step: who, when', ['step', 'd', 'bp', 'dv', 'bv', 'valid', 'brvalid', 'beat', 'morning', 'brmorning', 'search', 'brsearch', 'pawn', 'pawnat'])
    b.run()


{'create': create, 'graph': graph}[sys.argv[1]]()
