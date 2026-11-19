"""level1 lane: the wardrobe fall's get-up (pairs with wardrobe_fall_smooth.py, which leaves him lying after the
sequence stops: its clip sections are KEEP_STATE, so the mesh stays in the sequencer's custom anim mode).
  WardrobeVanish (4.15 s, he is hidden in the sand): Mesh.SetAnimationMode(AnimationBlueprint), then
      PlayAnimMontage(AM_FoA_WakeUp, 1.5). The montage's 0.3 s blend-in finishes while he is hidden, so at the re-form
      (5.05 s) he is lying, its held first frame runs to 5.48 s, then the get-up, standing at 7.18 s (control 7.2 s).
  FinishWardrobeTransition, inside its bWardrobeTransition branch (so also the reset path): StopAnimMontage(WakeUp)
      and SetAnimationMode(AnimationBlueprint) without re-init, so an interrupted fall never leaves him lying.
Idempotent: skips a function that already has its node. wardrobe_fall_reform.py then retimes the fall and swaps
the vanish's PlayAnimMontage for Montage_Play from 0.275 s (a shorter lying hold).
  $env:HAYBA_AGENT_ID='level1'; python Tools/Unreal/level1/wardrobe_fall_getup.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
from held_tool_graphs import Batch, inspect  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
GS, CH, SK = '/Script/Engine.GameplayStatics:', '/Script/Engine.Character:', '/Script/Engine.SkeletalMeshComponent:'
WAKE = '/Game/FoA/Characters/Player/Montages/AM_FoA_WakeUp.AM_FoA_WakeUp'
RATE = 1.5


def tail(fn, title):
    ns, es = inspect(P, fn)
    titles = {n['node_id']: n['title'].split('\n')[0] for n in ns}
    hits = [i for i, t in titles.items() if t == title and not any(e['from_node'] == i and e['from_pin'] == 'then' for e in es)]
    assert len(hits) == 1, (fn, title, hits)
    return hits[0], titles


def add(fn, last_title, montage_op):
    last, titles = tail(fn, last_title)
    if any(t in ('PlayAnimMontage', 'StopAnimMontage', 'Montage Play', 'Montage_Play') for t in titles.values()):
        return 'kept'
    b = Batch(P, fn)
    b.fn('pawn', GS + 'GetPlayerCharacter', 3000, 300, PlayerIndex=0)
    b.get('mesh', 'Mesh', 3300, 300, cls='/Script/Engine.Character')
    b.link('pawn', 'ReturnValue', 'mesh', 'self')
    b.fn('mode', SK + 'SetAnimationMode', 3600, 0, InAnimationMode='AnimationBlueprint', bForceInitAnimScriptInstance='false')
    b.link('mesh', 'Mesh', 'mode', 'self')
    if montage_op == 'play':
        b.fn('mont', CH + 'PlayAnimMontage', 3900, 0, AnimMontage=WAKE, InPlayRate=RATE)
        b.link('pawn', 'ReturnValue', 'mont', 'self')
        b.link(last, 'then', 'mode', 'execute')
        b.chain('mode', 'mont')
        b.comment('He re-forms lying, then gets up', ['pawn', 'mesh', 'mode', 'mont'])
    else:
        b.fn('mont', CH + 'StopAnimMontage', 3600, -250, AnimMontage=WAKE)
        b.link('pawn', 'ReturnValue', 'mont', 'self')
        b.link(last, 'then', 'mont', 'execute')
        b.chain('mont', 'mode')
        b.comment('Never leave him lying', ['pawn', 'mesh', 'mode', 'mont'])
    b.run()
    return 'added'


if __name__ == '__main__':
    print('GETUP', dict(vanish=add('WardrobeVanish', 'SetOldWall', 'play'),
                        finish=add('FinishWardrobeTransition', 'PlayerSand', 'stop')))
