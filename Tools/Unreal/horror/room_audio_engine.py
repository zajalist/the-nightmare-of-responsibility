"""atmosphere lane: the Level 2 car's engine, from BP_RoomAudio (no edit to the drive lane's BP_L2Car).
  $env:HAYBA_AGENT_ID='atmosphere'; python Tools/Unreal/horror/room_audio_engine.py      (inside a lease on BP_RoomAudio)
UpdateEngine, the last call of Poll, reads BP_L2Car each poll:
  - it drives while Active and neither Arrived (parked at the stop) nor Failed;
  - on the rising edge (bLastEngine) the 2D `Engine` component gets its sound (set at runtime: the placed FOA_RoomAudio
    keeps stale component values) and fades in over 1 s; on the falling edge it fades out over 1.5 s;
  - while it drives, pitch follows Speed (0.78 at rest to 1.12 at 1200 cm/s) and volume follows it too (0.3 to 0.75),
    both pulled down while the drive's QTE slow motion holds the global time dilation below 1 (volume x0.35, pitch x0.8
    at a dilation of 0.2).
BeginPlay stops the component. Every batch compiles, saves at 0 errors, and rolls back otherwise."""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Audio/BP_RoomAudio'
C = P + '.BP_RoomAudio_C'
CAR = '/Game/FoA/Level2/Drive/BP_L2Car.BP_L2Car_C'
WAVE = '/Game/FoA/Audio/SFX/Drive/SFX_Drive_CarInterior_Loop_01.SFX_Drive_CarInterior_Loop_01'
K = '/Script/Engine.KismetMathLibrary:'
KS = '/Script/Engine.KismetSystemLibrary:'
GS = '/Script/Engine.GameplayStatics:'
AU = '/Script/Engine.AudioComponent:'


def call(cmd, **params):
    r = h.call(cmd, params, timeout=60)
    assert r.get('ok'), (cmd, r.get('error'))
    return r.get('data', {})


def assets():
    info = call('blueprint_get_info', path=P)
    if 'Engine' not in {c['name'] for c in info['components']}:
        call('blueprint_add_component', path=P, component_name='Engine', component_class_path='/Script/Engine.AudioComponent')
    call('object_set_property', path=f'{C}:Engine_GEN_VARIABLE', properties={'Sound': WAVE, 'bAutoActivate': False})
    have = {v['name'] for v in info['variables']}
    for n in ('bWantEngine', 'bLastEngine'):
        if n not in have:
            call('blueprint_add_variable', path=P, variable_name=n, variable_type='bool', default_value='false',
                 instance_editable=False, category='Room audio')
    if 'UpdateEngine' not in info['functions']:
        call('blueprint_add_function', path=P, function_name='UpdateEngine', inputs=[])
    c = call('blueprint_compile', path=P)
    assert not c.get('error_count'), c


def graph():
    ns, _ = inspect(P, 'UpdateEngine')
    entry = next(n['node_id'] for n in ns if n['title'] in ('UpdateEngine', 'Update Engine'))
    b = Batch(P, 'UpdateEngine')
    old = [n['node_id'] for n in ns if n['node_id'] != entry]
    if old:  # ours alone: a rerun rebuilds the body
        b.ops.append(dict(op='remove', node_ids=old))
    # Is the car driving? (its properties are read only on the path where it exists)
    b.fn('car', GS + 'GetActorOfClass', 250, 0, ActorClass=CAR)
    b.fn('carOk', KS + 'IsValid', 500, 250)
    b.link('car', 'ReturnValue', 'carOk', 'Object')
    b.node('carB', 'branch', 500, 0)
    b.link('carOk', 'ReturnValue', 'carB', 'Condition')
    for i, var in enumerate(('Active', 'Arrived', 'Failed', 'Speed')):
        b.get(var, var, 750, 250 + i * 130, CAR)
        b.link('car', 'ReturnValue', var, 'self')
    b.fn('notArr', K + 'Not_PreBool', 1000, 380)
    b.link('Arrived', 'Arrived', 'notArr', 'A')
    b.fn('notFail', K + 'Not_PreBool', 1000, 510)
    b.link('Failed', 'Failed', 'notFail', 'A')
    b.fn('and1', K + 'BooleanAND', 1250, 300)
    b.link('Active', 'Active', 'and1', 'A')
    b.link('notArr', 'ReturnValue', 'and1', 'B')
    b.fn('and2', K + 'BooleanAND', 1450, 300)
    b.link('and1', 'ReturnValue', 'and2', 'A')
    b.link('notFail', 'ReturnValue', 'and2', 'B')
    b.set('wantYes', 'bWantEngine', 1450, -50)
    b.link('and2', 'ReturnValue', 'wantYes', 'bWantEngine')
    b.set('wantNo', 'bWantEngine', 750, -250)
    b.pin('wantNo', 'bWantEngine', 'false')
    # Speed and slow motion -> volume and pitch
    b.fn('s01', K + 'MapRangeClamped', 1000, 700, InRangeA=0, InRangeB=1200, OutRangeA=0, OutRangeB=1)
    b.link('Speed', 'Speed', 's01', 'Value')
    b.fn('dil', GS + 'GetGlobalTimeDilation', 1000, 900)
    b.fn('duckV', K + 'MapRangeClamped', 1250, 900, InRangeA=0.2, InRangeB=1.0, OutRangeA=0.35, OutRangeB=1.0)
    b.link('dil', 'ReturnValue', 'duckV', 'Value')
    b.fn('duckP', K + 'MapRangeClamped', 1250, 1050, InRangeA=0.2, InRangeB=1.0, OutRangeA=0.8, OutRangeB=1.0)
    b.link('dil', 'ReturnValue', 'duckP', 'Value')
    b.fn('volS', K + 'Lerp', 1250, 700, A=0.3, B=0.75)
    b.link('s01', 'ReturnValue', 'volS', 'Alpha')
    b.fn('vol', K + 'Multiply_DoubleDouble', 1500, 750)
    b.link('volS', 'ReturnValue', 'vol', 'A')
    b.link('duckV', 'ReturnValue', 'vol', 'B')
    b.fn('pitS', K + 'Lerp', 1250, 1200, A=0.78, B=1.12)
    b.link('s01', 'ReturnValue', 'pitS', 'Alpha')
    b.fn('pit', K + 'Multiply_DoubleDouble', 1500, 1100)
    b.link('pitS', 'ReturnValue', 'pit', 'A')
    b.link('duckP', 'ReturnValue', 'pit', 'B')
    # Edge: start or stop; otherwise follow the speed
    b.get('want', 'bWantEngine', 1750, 250)
    b.get('last', 'bLastEngine', 1750, 380)
    b.fn('chg', K + 'NotEqual_BoolBool', 2000, 300)
    b.link('want', 'bWantEngine', 'chg', 'A')
    b.link('last', 'bLastEngine', 'chg', 'B')
    b.node('chgB', 'branch', 2000, 0)
    b.link('chg', 'ReturnValue', 'chgB', 'Condition')
    b.set('keep', 'bLastEngine', 2250, -150)
    b.link('want', 'bWantEngine', 'keep', 'bLastEngine')
    b.node('onB', 'branch', 2500, -150)
    b.link('want', 'bWantEngine', 'onB', 'Condition')
    b.get('eng', 'Engine', 2750, 500)
    b.fn('snd', AU + 'SetSound', 2750, -350, NewSound=WAVE)
    b.fn('pitch0', AU + 'SetPitchMultiplier', 3000, -350)
    b.fn('fadeIn', AU + 'FadeIn', 3250, -350, FadeInDuration=1.0, StartTime=0)
    b.fn('fadeOut', AU + 'FadeOut', 2750, 0, FadeOutDuration=1.5, FadeVolumeLevel=0)
    b.node('runB', 'branch', 2250, 250)
    b.link('want', 'bWantEngine', 'runB', 'Condition')
    b.fn('adj', AU + 'AdjustVolume', 2500, 250, AdjustVolumeDuration=0.5)
    b.fn('pitch1', AU + 'SetPitchMultiplier', 2750, 250)
    for n in ('snd', 'pitch0', 'fadeIn', 'fadeOut', 'adj', 'pitch1'):
        b.link('eng', 'Engine', n, 'self')
    b.link('pit', 'ReturnValue', 'pitch0', 'NewPitchMultiplier')
    b.link('pit', 'ReturnValue', 'pitch1', 'NewPitchMultiplier')
    b.link('vol', 'ReturnValue', 'fadeIn', 'FadeVolumeLevel')
    b.link('vol', 'ReturnValue', 'adj', 'AdjustVolumeLevel')
    # exec
    b.chain(entry, 'car', 'carB')
    b.link('carB', 'then', 'wantYes', 'execute')
    b.link('carB', 'else', 'wantNo', 'execute')
    b.link('wantYes', 'then', 'chgB', 'execute')
    b.link('wantNo', 'then', 'chgB', 'execute')
    b.link('chgB', 'then', 'keep', 'execute')
    b.link('keep', 'then', 'onB', 'execute')
    b.chain('snd', 'pitch0', 'fadeIn')
    b.link('onB', 'then', 'snd', 'execute')
    b.link('onB', 'else', 'fadeOut', 'execute')
    b.link('chgB', 'else', 'runB', 'execute')
    b.link('runB', 'then', 'adj', 'execute')
    b.link('adj', 'then', 'pitch1', 'execute')
    b.comment('Car engine', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()


def poll():
    ns, es = inspect(P, 'Poll')
    if any(n['title'] in ('UpdateEngine', 'Update Engine') for n in ns):
        print('Poll already calls UpdateEngine')
        return
    last = next(n['node_id'] for n in ns if n['title'] in ('UpdateIntro', 'Update Intro'))
    assert not any(e['from_node'] == last and e['from_pin'] == 'then' for e in es), 'UpdateIntro.then is taken'
    b = Batch(P, 'Poll')
    b.fn('engine', C + ':UpdateEngine', 3650, 0)
    b.link(last, 'then', 'engine', 'execute')
    b.run()


def begin():
    """BeginPlay stops the engine too (after the Level 2 beds' stops)."""
    ns, es = inspect(P, 'EventGraph')
    if any(n['title'] == 'Stop' and any(e['to_node'] == n['node_id'] and e['from_pin'] == 'Engine' for e in es) for n in ns):
        print('BeginPlay already stops the engine')
        return
    stops = [n['node_id'] for n in ns if n['title'] == 'Stop']
    tail = next(s for s in stops if not any(e['from_node'] == s and e['from_pin'] == 'then' for e in es))
    b = Batch(P, 'EventGraph')
    b.get('engC', 'Engine', 1680, 250)
    b.fn('stopEng', AU + 'Stop', 1680, 0)
    b.link('engC', 'Engine', 'stopEng', 'self')
    b.link(tail, 'then', 'stopEng', 'execute')
    b.run()


if __name__ == '__main__':
    step = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for s in (['assets', 'graph', 'poll', 'begin'] if step == 'all' else [step]):
        globals()[s]()
    print('done', step)
