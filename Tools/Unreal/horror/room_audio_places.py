"""atmosphere lane: Level 2's own ambience in BP_RoomAudio, keyed to the place the journey's music names.
  $env:HAYBA_AGENT_ID='atmosphere'; python Tools/Unreal/horror/room_audio_places.py [assets|graph|poll|all]
Inside a lease on /Game/FoA/Audio/BP_RoomAudio. Before this, Level 2 had only its music: Dream A and the street were
otherwise silent (the bedroom beds are positional and drop out 800 m away).
  - three 2D beds (looping SoundWaves without attenuation, SC_Ambience): DreamBed (soft wind) while MusicOverride is
    Dream (Dream A, the interview room, the colour exit); CityBed (dawn birds, far traffic) and CityHum (city traffic
    hum) while it is City (the street and the drive)
  - UpdatePlace, the last call of Poll: on a change of MusicOverride (edge against LastPlace) each bed fades in (3 s)
    when the new place is its own and out (2.5 s) otherwise; None (the bedroom, a Level 2 restart) fades all three out
  - the bedroom falls away: any place other than None fades the bedroom's Rain, Radiator, Hum and Outside over 6 s
    (the threshold opens 9 s before the teleport, so they thin out instead of cutting); None brings Rain and Radiator back
Every batch is compiled, saved only at 0 errors, and rolled back otherwise (held_tool_graphs.Batch.run)."""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Audio/BP_RoomAudio'
C = P + '.BP_RoomAudio_C'
K = '/Script/Engine.KismetMathLibrary:'
AU = '/Script/Engine.AudioComponent:'
W = '/Game/FoA/Audio/SFX/Ambience/'
# component, looping wave, place, volume once faded in
BEDS = [('DreamBed', 'SFX_Ambience_NightWind_Loop_01', 'Dream', 0.45),
        ('CityBed', 'SFX_Ambience_Outside_Loop_01', 'City', 0.5),
        ('CityHum', 'SFX_Ambience_DistantCity_Loop_01', 'City', 0.35)]
ROOM = [('Rain', 0.55), ('Radiator', 0.35)]  # the bedroom's auto-play beds and their build_room_audio volumes
AWAY = [('Hum', 0), ('Outside', 0)]  # T10's door beds: only ever faded out here


def call(cmd, **params):
    r = h.call(cmd, params, timeout=60)
    assert r.get('ok'), (cmd, r.get('error'))
    return r.get('data', {})


def assets():
    for _, wave, _, _ in BEDS:  # a bed must be a 2D loop: no attenuation of its own, looping, an ambience class
        props = call('object_get_property', path=f'{W}{wave}.{wave}',
                     names=['AttenuationSettings', 'bLooping', 'SoundClassObject'])['properties']
        assert props.get('AttenuationSettings') in (None, '', 'None') and str(props.get('bLooping')).lower() == 'true', (wave, props)
        print(wave, props)
    info = call('blueprint_get_info', path=P)
    have = {c['name'] for c in info['components']}
    for comp, wave, _, _ in BEDS:
        if comp not in have:
            call('blueprint_add_component', path=P, component_name=comp, component_class_path='/Script/Engine.AudioComponent')
        call('object_set_property', path=f'{C}:{comp}_GEN_VARIABLE', properties={
            'Sound': f'{W}{wave}.{wave}', 'bAutoActivate': False, 'VolumeMultiplier': 1.0})
    if not any(v['name'] == 'LastPlace' for v in info['variables']):
        call('blueprint_add_variable', path=P, variable_name='LastPlace', variable_type='name', default_value='None',
             instance_editable=False, category='Room audio')
    if 'UpdatePlace' not in info['functions']:
        call('blueprint_add_function', path=P, function_name='UpdatePlace', inputs=[])
    c = call('blueprint_compile', path=P)
    assert not c.get('error_count') and c.get('ok', True), c
    call('asset_save', asset_paths=[P])
    print('assets ok', [b[0] for b in BEDS])


def graph():
    ns, _ = inspect(P, 'UpdatePlace')
    entry = next(n['node_id'] for n in ns if n['title'] == 'Update Place' or n['title'] == 'UpdatePlace')
    b = Batch(P, 'UpdatePlace')
    old = [n['node_id'] for n in ns if n['node_id'] != entry]
    if old:  # idempotent: the function is ours alone, so a rerun rebuilds its body
        b.ops.append(dict(op='remove', node_ids=old))
    b.get('want', 'MusicOverride', 0, 300)
    b.get('last', 'LastPlace', 0, 450)
    b.fn('ne', K + 'NotEqual_NameName', 250, 300)
    b.link('want', 'MusicOverride', 'ne', 'A')
    b.link('last', 'LastPlace', 'ne', 'B')
    b.node('chg', 'branch', 250, 0)
    b.link('ne', 'ReturnValue', 'chg', 'Condition')
    b.set('keep', 'LastPlace', 500, 0)
    b.link('want', 'MusicOverride', 'keep', 'LastPlace')
    b.chain(entry, 'chg')
    b.link('chg', 'then', 'keep', 'execute')
    prev, x = 'keep', 800
    for i, (comp, wave, place, vol) in enumerate(BEDS):
        r = comp.lower()
        b.fn(r + 'Is', K + 'EqualEqual_NameName', x, 350, B=place)
        b.link('want', 'MusicOverride', r + 'Is', 'A')
        b.node(r + 'Br', 'branch', x, 0)
        b.link(r + 'Is', 'ReturnValue', r + 'Br', 'Condition')
        b.get(r + 'C', comp, x + 250, 500)
        b.fn(r + 'In', AU + 'FadeIn', x + 250, -150, FadeInDuration=3.0, FadeVolumeLevel=vol, StartTime=0)
        b.fn(r + 'Out', AU + 'FadeOut', x + 250, 200, FadeOutDuration=2.5, FadeVolumeLevel=0)
        b.link(r + 'C', comp, r + 'In', 'self')
        b.link(r + 'C', comp, r + 'Out', 'self')
        if prev == 'keep':
            b.link('keep', 'then', r + 'Br', 'execute')
        else:  # both arms of the previous bed lead on to this one
            b.link(prev + 'In', 'then', r + 'Br', 'execute')
            b.link(prev + 'Out', 'then', r + 'Br', 'execute')
        # the sound is set here, not only on the component: the placed FOA_RoomAudio keeps its own component values
        b.fn(r + 'Snd', AU + 'SetSound', x + 250, -300, NewSound=f'{W}{wave}.{wave}')
        b.link(r + 'C', comp, r + 'Snd', 'self')
        b.link(r + 'Br', 'then', r + 'Snd', 'execute')
        b.link(r + 'Snd', 'then', r + 'In', 'execute')
        b.link(r + 'Br', 'else', r + 'Out', 'execute')
        prev, x = r, x + 600
    beds = [o['ref'] for o in b.ops if o.get('op') == 'add_node']
    # The bedroom falls away: leaving it (any place), its beds fade over 6 s, so the rain and the radiator thin out
    # while the threshold opens instead of cutting at the 800 m teleport; back in it (None), rain and radiator return.
    b.fn('home', K + 'EqualEqual_NameName', x, 350, B='None')
    b.link('want', 'MusicOverride', 'home', 'A')
    b.node('homeBr', 'branch', x, 0)
    b.link('home', 'ReturnValue', 'homeBr', 'Condition')
    b.link(prev + 'In', 'then', 'homeBr', 'execute')
    b.link(prev + 'Out', 'then', 'homeBr', 'execute')
    back, away = 'homeBr', 'homeBr'
    for i, (comp, vol) in enumerate(ROOM):
        r = 'room' + comp
        b.get(r + 'C', comp, x + 250 + i * 300, 500)
        b.fn(r + 'In', AU + 'FadeIn', x + 250 + i * 300, -150, FadeInDuration=2.0, FadeVolumeLevel=vol, StartTime=0)
        b.link(r + 'C', comp, r + 'In', 'self')
        b.link(back, 'then', r + 'In', 'execute')
        back = r + 'In'
    for i, (comp, _) in enumerate(ROOM + AWAY):
        r = 'gone' + comp
        b.get(r + 'C', comp, x + 250 + i * 300, 700)
        b.fn(r + 'Out', AU + 'FadeOut', x + 250 + i * 300, 200, FadeOutDuration=6.0, FadeVolumeLevel=0)
        b.link(r + 'C', comp, r + 'Out', 'self')
        b.link(away, 'else' if away == 'homeBr' else 'then', r + 'Out', 'execute')
        away = r + 'Out'
    b.comment('Level 2 beds by place', beds)
    b.comment('The bedroom falls away', [o['ref'] for o in b.ops if o.get('op') == 'add_node' and o['ref'] not in beds])
    b.run()


def poll():
    ns, es = inspect(P, 'Poll')
    if any(n['title'] in ('UpdatePlace', 'Update Place') for n in ns):
        print('Poll already calls UpdatePlace')
        return
    comp = next(n['node_id'] for n in ns if n['title'] in ('UpdateComposure', 'Update Composure'))
    assert not any(e['from_node'] == comp and e['from_pin'] == 'then' for e in es), 'UpdateComposure.then is taken'
    b = Batch(P, 'Poll')
    b.fn('place', C + ':UpdatePlace', 3150, 0)
    b.link(comp, 'then', 'place', 'execute')
    b.run()


def begin():
    """BeginPlay stops the three beds: the placed FOA_RoomAudio keeps auto-activate on for them whatever the template
    says (its component values revert on every recompile), and the Dream bed then played wind in the bedroom from boot."""
    ns, es = inspect(P, 'EventGraph')
    if any(n['title'] == 'Stop' for n in ns):
        print('BeginPlay already stops the beds')
        return
    timers = [n['node_id'] for n in ns if n['title'] == 'Set Timer by Function Name']
    last = next(t for t in timers if not any(e['from_node'] == t and e['from_pin'] == 'then' for e in es))
    b = Batch(P, 'EventGraph')
    prev = last
    for i, (comp, _, _, _) in enumerate(BEDS):
        r = 'stop' + comp
        b.get(r + 'C', comp, 900 + i * 260, 250)
        b.fn(r, AU + 'Stop', 900 + i * 260, 0)
        b.link(r + 'C', comp, r, 'self')
        b.link(prev, 'then', r, 'execute')
        prev = r
    b.comment('Level 2 beds start silent', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()


def composure():
    """UpdateComposure's fade-in also sets the bed's sound: the placed instance had lost it, so it never played."""
    ns, es = inspect(P, 'UpdateComposure')
    if any(n['title'] in ('Set Sound', 'SetSound') for n in ns):
        print('UpdateComposure already sets its sound')
        return
    fade_in = next(n['node_id'] for n in ns if n['title'] in ('Fade In', 'FadeIn'))
    feed = next(e for e in es if e['to_node'] == fade_in and e['to_pin'] == 'execute')
    target = next(e for e in es if e['to_node'] == fade_in and e['to_pin'] == 'self')
    b = Batch(P, 'UpdateComposure')
    b.fn('snd', AU + 'SetSound', 2300, -500, NewSound='/Game/FoA/Audio/MetaSounds/Battle/S_Battle_ComposureLow_Loop_01.S_Battle_ComposureLow_Loop_01')
    b.link(target['from_node'], target['from_pin'], 'snd', 'self')
    b.cut(feed['from_node'], feed['from_pin'], fade_in, 'execute')
    b.link(feed['from_node'], feed['from_pin'], 'snd', 'execute')
    b.link('snd', 'then', fade_in, 'execute')
    b.run()


if __name__ == '__main__':
    step = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for s in (['assets', 'graph', 'poll', 'composure', 'begin'] if step == 'all' else [step]):
        globals()[s]()
