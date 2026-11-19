"""Every morning runs the same T0 (QA #18, 2026-11-10). The T0 phone (OpenMorningPhone, RaiseMorningPhone) only opens
while BeatIndex < 0, so a skip or an early report never reopens it mid-day. ResetToTitle put BeatIndex back to -1, but
StartNextMorning (Restart Day, the rollover card and FailDay all end there) did not: the new morning kept the old beat
(T1 or later) and its phone never opened. StartNextMorning now clears the beat like ResetToTitle before BeginMorning.
BeatIndex going back to -1 is also what resets the phone clock's first-open stamp (UI's UpdateClock).
  StartNextMorning: StartNewDay, ResetHouse, ReturnToBed, BeatIndex = -1, Beat = none, bRollingOver = false,
                    BeginMorning, EnableInput.
Hayba only; idempotent; build_director.py matches.  python Tools/Unreal/flow/patch_new_morning_beat.py"""
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
os.environ['HAYBA_AGENT_ID'] = 'story'

assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + P], ttl_s=120, wait_s=240)
try:
    ns, es = inspect(P, 'StartNextMorning')
    if any(n['title'] == 'Set BeatIndex' for n in ns):
        print('kept: StartNextMorning already clears the beat')
    else:
        bed = find(ns, 'ReturnToBed')
        after = next(x for x in es if x['from_node'] == bed and x['from_pin'] == 'then')
        b = Batch(P, 'StartNextMorning')
        b.cut(bed, 'then', after['to_node'], after['to_pin'])
        b.set('beatindex', 'BeatIndex', 1000, -220)
        b.pin('beatindex', 'BeatIndex', -1)
        b.set('beat', 'Beat', 1150, -220)
        b.link(bed, 'then', 'beatindex', 'execute')
        b.chain('beatindex', 'beat')
        b.link('beat', 'then', after['to_node'], after['to_pin'])
        b.comment('A new morning starts before T0', ['beatindex', 'beat'])
        b.run()
        print('StartNextMorning clears the beat before BeginMorning')
    ns, _ = inspect(P, 'StartNextMorning')
    assert any(n['title'] == 'Set BeatIndex' for n in ns)
finally:
    h.release('story', token)
