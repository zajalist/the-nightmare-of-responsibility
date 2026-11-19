"""atmosphere lane: sound for the intro story's panels, from BP_RoomAudio (the intro widget plays none).
  $env:HAYBA_AGENT_ID='atmosphere'; python Tools/Unreal/horror/room_audio_intro.py      (inside a lease on BP_RoomAudio)
WBP_IntroStory steps its Index through five panels (5.0, 4.5, 4.5, 5.5, 1.6 s). Until now the only sound under them was
the wake bed and the room: the cut to the phone, the shirt, the thing at the foot of the bed and the hook (it is right
over him, the frame crumbles to black sand) passed in silence. UpdateIntro, the last call of Poll, watches the front
end's Story widget and on each new panel (edge against LastIntroPanel) plays:
  panels 1-3   SFX_FE_PanelTransition (the front end's own sand-dissolve whoosh, made for these panels, never wired)
  panel 1      a soft phone buzz under the whoosh (the phone lights up; the same buzz wakes him at T0)
  panel 4      the hook: SFX_Horror_Stinger_01 and SFX_FE_SandScatter (the frame crumbling to sand)
Off screen (skipped, finished, gameplay) LastIntroPanel goes back to -1, so a new game hears it again."""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Audio/BP_RoomAudio'
C = P + '.BP_RoomAudio_C'
FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
STORY = '/Game/FoA/UI/Intro/WBP_IntroStory.WBP_IntroStory_C'
K = '/Script/Engine.KismetMathLibrary:'
KS = '/Script/Engine.KismetSystemLibrary:'
GS = '/Script/Engine.GameplayStatics:'
A = '/Game/FoA/Audio/'
WHOOSH = A + 'SFX/UI_FrontEnd/SFX_FE_PanelTransition.SFX_FE_PanelTransition'
BUZZ = A + 'MetaSounds/Phone/S_Phone_Buzz.S_Phone_Buzz'
STING = A + 'SFX/Horror/SFX_Horror_Stinger_01.SFX_Horror_Stinger_01'
SCATTER = A + 'SFX/UI_FrontEnd/SFX_FE_SandScatter.SFX_FE_SandScatter'


def call(cmd, **params):
    r = h.call(cmd, params, timeout=60)
    assert r.get('ok'), (cmd, r.get('error'))
    return r.get('data', {})


def assets():
    info = call('blueprint_get_info', path=P)
    if not any(v['name'] == 'LastIntroPanel' for v in info['variables']):
        call('blueprint_add_variable', path=P, variable_name='LastIntroPanel', variable_type='int', default_value='-1',
             instance_editable=False, category='Room audio')
    if 'UpdateIntro' not in info['functions']:
        call('blueprint_add_function', path=P, function_name='UpdateIntro', inputs=[])
    c = call('blueprint_compile', path=P)
    assert not c.get('error_count'), c


def graph():
    ns, _ = inspect(P, 'UpdateIntro')
    entry = next(n['node_id'] for n in ns if n['title'] in ('UpdateIntro', 'Update Intro'))
    b = Batch(P, 'UpdateIntro')
    old = [n['node_id'] for n in ns if n['node_id'] != entry]
    if old:  # the function is ours alone: a rerun rebuilds its body
        b.ops.append(dict(op='remove', node_ids=old))
    # Find the story widget (impure finds stay on the exec path)
    b.fn('fe', GS + 'GetActorOfClass', 250, 0, ActorClass=FE)
    b.fn('feOk', KS + 'IsValid', 500, 250)
    b.link('fe', 'ReturnValue', 'feOk', 'Object')
    b.node('feB', 'branch', 500, 0)
    b.link('feOk', 'ReturnValue', 'feB', 'Condition')
    b.get('story', 'Story', 750, 250, FE)
    b.link('fe', 'ReturnValue', 'story', 'self')
    b.node('as', 'cast', 750, 0, class_path=STORY)
    b.link('story', 'Story', 'as', 'Object')
    # On screen and still running
    b.fn('vis', '/Script/UMG.UserWidget:IsInViewport', 1050, 250)
    b.link('as', 'AsWBP Intro Story', 'vis', 'self')
    b.get('done', 'bDone', 1050, 400, STORY)
    b.link('as', 'AsWBP Intro Story', 'done', 'self')
    b.fn('notDone', K + 'Not_PreBool', 1300, 400)
    b.link('done', 'bDone', 'notDone', 'A')
    b.fn('live', K + 'BooleanAND', 1300, 250)
    b.link('vis', 'ReturnValue', 'live', 'A')
    b.link('notDone', 'ReturnValue', 'live', 'B')
    b.node('liveB', 'branch', 1300, 0)
    b.link('live', 'ReturnValue', 'liveB', 'Condition')
    # A new panel: remember it, then its sound
    b.get('idx', 'Index', 1550, 250, STORY)
    b.link('as', 'AsWBP Intro Story', 'idx', 'self')
    b.get('last', 'LastIntroPanel', 1550, 400)
    b.fn('ne', K + 'NotEqual_IntInt', 1800, 300)
    b.link('idx', 'Index', 'ne', 'A')
    b.link('last', 'LastIntroPanel', 'ne', 'B')
    b.node('newB', 'branch', 1800, 0)
    b.link('ne', 'ReturnValue', 'newB', 'Condition')
    b.set('keep', 'LastIntroPanel', 2050, 0)
    b.link('idx', 'Index', 'keep', 'LastIntroPanel')
    for ref, lo, hi, x in (('mid', 1, 3, 2300), ('phone', 1, 1, 2850), ('hook', 4, 4, 3400)):
        b.fn(ref + 'In', K + 'InRange_IntInt', x, 300, Min=lo, Max=hi, InclusiveMin='true', InclusiveMax='true')
        b.link('idx', 'Index', ref + 'In', 'Value')
        b.node(ref + 'B', 'branch', x, 0)
        b.link(ref + 'In', 'ReturnValue', ref + 'B', 'Condition')
    b.fn('whoosh', GS + 'PlaySound2D', 2550, -150, Sound=WHOOSH, VolumeMultiplier=0.6)
    b.fn('buzz', GS + 'PlaySound2D', 3100, -150, Sound=BUZZ, VolumeMultiplier=0.3)
    b.fn('sting', GS + 'PlaySound2D', 3650, -150, Sound=STING, VolumeMultiplier=0.55)
    b.fn('scatter', GS + 'PlaySound2D', 3900, -150, Sound=SCATTER, VolumeMultiplier=0.8)
    # Off screen: forget the panel so a new game plays the intro's sounds again
    b.set('reset', 'LastIntroPanel', 1550, -200)
    b.pin('reset', 'LastIntroPanel', '-1')
    b.chain(entry, 'fe', 'feB')
    b.link('feB', 'then', 'as', 'execute')
    b.link('as', 'then', 'liveB', 'execute')
    b.link('liveB', 'then', 'newB', 'execute')
    b.link('liveB', 'else', 'reset', 'execute')
    b.link('newB', 'then', 'keep', 'execute')
    b.link('keep', 'then', 'midB', 'execute')
    b.link('midB', 'then', 'whoosh', 'execute')
    b.link('midB', 'else', 'phoneB', 'execute')
    b.link('whoosh', 'then', 'phoneB', 'execute')
    b.link('phoneB', 'then', 'buzz', 'execute')
    b.link('phoneB', 'else', 'hookB', 'execute')
    b.link('buzz', 'then', 'hookB', 'execute')
    b.chain('hookB', 'sting', 'scatter')
    b.comment('Intro panel sounds', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()


def poll():
    ns, es = inspect(P, 'Poll')
    if any(n['title'] in ('UpdateIntro', 'Update Intro') for n in ns):
        print('Poll already calls UpdateIntro')
        return
    place = next(n['node_id'] for n in ns if n['title'] in ('UpdatePlace', 'Update Place'))
    assert not any(e['from_node'] == place and e['from_pin'] == 'then' for e in es), 'UpdatePlace.then is taken'
    b = Batch(P, 'Poll')
    b.fn('intro', C + ':UpdateIntro', 3400, 0)
    b.link(place, 'then', 'intro', 'execute')
    b.run()


if __name__ == '__main__':
    step = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for s in (['assets', 'graph', 'poll'] if step == 'all' else [step]):
        globals()[s]()
    print('done', step)
