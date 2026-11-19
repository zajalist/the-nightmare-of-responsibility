"""Story-beat audio cues in BP_BeatDirector (docs/design/horror/audio_wiring.md, "For the story lane"). Hayba only;
idempotent; every batch compiles 0/0 before it saves.
  BeginWardrobeTransition (the 2 s rattle): S_Wardrobe_Rattle at the wardrobe, S_Wardrobe_Creak 1.2 s later.
  WardrobeLanded (+0.25 s): S_Wardrobe_Debris at the fallen wardrobe (StoryAudioForEvent, first in ReportEvent).
  MoveDoor (T7): S_Door_Move and S_Sand_Pour at DoorFrame.
  T0's S_Phone_NightstandBuzz lives in OpenMorningPhone (patch_t0_phone.py).
  OpenTheDoor gets no cue here: BP_Door's own StateSounds play S_Door_FinalOpen on Open (horror lane), and OpenTheDoor
  drives exactly that state, so a director cue would play it twice.
  python Tools/Unreal/flow/wire_story_audio.py"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
C = P + '.BP_BeatDirector_C'
MS = '/Game/FoA/Audio/MetaSounds/'
TOPPLE = '/Game/FoA/Gameplay/BP_Topple.BP_Topple_C'
GS, KS, K = '/Script/Engine.GameplayStatics:', '/Script/Engine.KismetSystemLibrary:', '/Script/Engine.KismetMathLibrary:'
A = '/Script/Engine.Actor:'


def snd(path):
    return MS + path + '.' + path.rsplit('/', 1)[1]


def has_sound(graph, path):
    ns, _ = inspect(P, graph)
    return any(path.rsplit('/', 1)[1] in str(p.get('default_object') or p.get('default_value') or '') for n in ns for p in n['pins'])


def ensure_fn(name, inputs=None):
    if not h.call('blueprint_inspect_graph', {'path': P, 'graph_name': name}).get('ok'):
        r = h.call('blueprint_add_function', {'path': P, 'function_name': name, **({'inputs': inputs} if inputs else {})})
        assert r.get('ok'), r


def at_wardrobe(name, sound, x=0):
    """A function body: the sound at the wardrobe (BP_Topple), if there is one."""
    ns, _ = inspect(P, name)
    entry = find(ns, name)
    b = Batch(P, name)
    old = [n['node_id'] for n in ns if n['node_id'] != entry]
    if old:
        b.ops.append(dict(op='remove', node_ids=old))
    b.fn('wd', GS + 'GetActorOfClass', 250, 0, ActorClass=TOPPLE)
    b.link(entry, 'then', 'wd', 'execute')
    b.fn('ok', KS + 'IsValid', 500, 250)
    b.link('wd', 'ReturnValue', 'ok', 'Object')
    b.node('has', 'branch', 750, 0)
    b.link('ok', 'ReturnValue', 'has', 'Condition')
    b.link('wd', 'then', 'has', 'execute')
    b.fn('where', A + 'K2_GetActorLocation', 750, 300)
    b.link('wd', 'ReturnValue', 'where', 'self')
    b.fn('play', GS + 'PlaySoundAtLocation', 1050, 0, Sound=snd(sound))
    b.link('where', 'ReturnValue', 'play', 'Location')
    b.link('has', 'then', 'play', 'execute')
    return b


def prepend_cue(graph, build, title):
    """Insert a cue chain right after the function entry; the old first node follows it."""
    ns, es = inspect(P, graph)
    entry = find(ns, graph)
    first = next(e for e in es if e['from_node'] == entry and e['from_pin'] == 'then')
    b = Batch(P, graph)
    head, tails = build(b)
    b.cut(entry, 'then', first['to_node'], first['to_pin'])
    b.link(entry, 'then', head, 'execute')
    for ref, out in (tails if isinstance(tails, list) else [(tails, 'then')]):
        b.link(ref, out, first['to_node'], first['to_pin'])
    b.comment(title, [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()


def main():
    os.environ['HAYBA_AGENT_ID'] = 'story'
    assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    token = h.lease_acquire('story', ['asset:' + P], ttl_s=240, wait_s=180)
    done = []
    try:
        for name in ('WardrobeCreakCue', 'WardrobeDebrisCue'):
            ensure_fn(name)
        ensure_fn('StoryAudioForEvent', [{'name': 'Event', 'type': 'name'}])
        if not has_sound('WardrobeCreakCue', 'Wardrobe/S_Wardrobe_Creak'):
            b = at_wardrobe('WardrobeCreakCue', 'Wardrobe/S_Wardrobe_Creak')
            b.comment('The wardrobe creaks', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
            b.run()
            done.append('WardrobeCreakCue')
        if not has_sound('WardrobeDebrisCue', 'Wardrobe/S_Wardrobe_Debris'):
            b = at_wardrobe('WardrobeDebrisCue', 'Wardrobe/S_Wardrobe_Debris')
            b.comment('Debris after the landing', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
            b.run()
            done.append('WardrobeDebrisCue')
        if not has_sound('BeginWardrobeTransition', 'Wardrobe/S_Wardrobe_Rattle'):
            def rattle(b):
                b.fn('wd', GS + 'GetActorOfClass', -900, -400, ActorClass=TOPPLE)
                b.fn('ok', KS + 'IsValid', -650, -200)
                b.link('wd', 'ReturnValue', 'ok', 'Object')
                b.node('has', 'branch', -400, -400)
                b.link('ok', 'ReturnValue', 'has', 'Condition')
                b.link('wd', 'then', 'has', 'execute')
                b.fn('where', A + 'K2_GetActorLocation', -400, -150)
                b.link('wd', 'ReturnValue', 'where', 'self')
                b.fn('play', GS + 'PlaySoundAtLocation', -150, -450, Sound=snd('Wardrobe/S_Wardrobe_Rattle'))
                b.link('where', 'ReturnValue', 'play', 'Location')
                b.link('has', 'then', 'play', 'execute')
                b.fn('creak', KS + 'K2_SetTimer', 150, -400, FunctionName='WardrobeCreakCue', Time=1.2, bLooping='false')
                b.link('play', 'then', 'creak', 'execute')
                b.link('has', 'else', 'creak', 'execute')
                return 'wd', 'creak'
            prepend_cue('BeginWardrobeTransition', rattle, 'The wardrobe rattles')
            done.append('BeginWardrobeTransition')
        ns, _ = inspect(P, 'StoryAudioForEvent')
        if not any(n['title'] == 'Set Timer by Function Name' for n in ns):
            entry = find(ns, 'StoryAudioForEvent')
            b = Batch(P, 'StoryAudioForEvent')
            b.fn('landed', K + 'EqualEqual_NameName', 250, 250, B='WardrobeLanded')
            b.link(entry, 'Event', 'landed', 'A')
            b.node('is', 'branch', 500, 0)
            b.link('landed', 'ReturnValue', 'is', 'Condition')
            b.link(entry, 'then', 'is', 'execute')
            b.fn('debris', KS + 'K2_SetTimer', 750, 0, FunctionName='WardrobeDebrisCue', Time=0.25, bLooping='false')
            b.link('is', 'then', 'debris', 'execute')
            b.comment('Event cues', ['landed', 'is', 'debris'])
            b.run()
            done.append('StoryAudioForEvent')
        ns, _ = inspect(P, 'ReportEvent')
        if not any(n['title'] == 'StoryAudioForEvent' for n in ns):
            def call(b):
                b.fn('cue', C + ':StoryAudioForEvent', -900, -300)
                b.link(find(ns, 'ReportEvent'), 'Event', 'cue', 'Event')
                return 'cue', 'cue'
            prepend_cue('ReportEvent', call, 'Story audio')
            done.append('ReportEvent')
        if not has_sound('MoveDoor', 'Door/S_Door_Move'):
            def door(b):
                b.get('frame', 'DoorFrame', -900, -150)
                b.fn('ok', KS + 'IsValid', -650, -150)
                b.link('frame', 'DoorFrame', 'ok', 'Object')
                b.node('has', 'branch', -650, -400)
                b.link('ok', 'ReturnValue', 'has', 'Condition')
                b.fn('where', A + 'K2_GetActorLocation', -400, -150)
                b.link('frame', 'DoorFrame', 'where', 'self')
                b.fn('drag', GS + 'PlaySoundAtLocation', -400, -450, Sound=snd('Door/S_Door_Move'))
                b.link('where', 'ReturnValue', 'drag', 'Location')
                b.fn('pour', GS + 'PlaySoundAtLocation', -100, -450, Sound=snd('Sand/S_Sand_Pour'))
                b.link('where', 'ReturnValue', 'pour', 'Location')
                b.link('has', 'then', 'drag', 'execute')
                b.link('drag', 'then', 'pour', 'execute')
                return 'has', [('pour', 'then'), ('has', 'else')]
            prepend_cue('MoveDoor', door, 'The door moves')
            done.append('MoveDoor')
        print('story audio wired', done)
    finally:
        h.release('story', token)


if __name__ == '__main__':
    main()
