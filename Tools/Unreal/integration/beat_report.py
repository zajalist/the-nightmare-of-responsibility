"""Integration lane: pass/fail per beat from a pie_loop timeline (offline).
  python Tools/Unreal/integration/beat_report.py Saved/Integration/<name>_timeline.json
A beat passes when the director entered it; 'via' says whether it got there by its trigger event or a forced report,
and misses list the WAITs that timed out (the beat the chain expected and the beat it was really on)."""
import json
import sys

TRIGGER = {'T1': 'PhoneWakeUp', 'T2': 'FirstSteps', 'T3': 'Searched', 'T4': 'KeyTaken', 'T5': 'KeySnapped',
           'T6': 'LatchFreed', 'T7': 'WardrobeLanded', 'T8': 'ShirtTaken', 'T9': 'EncounterWon', 'T10': 'PayoffEnded'}


def main():
    log = json.load(open(sys.argv[1], encoding='utf-8'))
    entered, last_cmd = {}, None
    for e in log:
        if e['kind'] == 'cmd':
            last_cmd = e['cmd']
        elif e['kind'] == 'beat' and e['beat'] not in entered:
            entered[e['beat']] = (e['t'], last_cmd, e.get('mpc'))
    for b in ['T0'] + list(TRIGGER):
        if b in entered:
            t, cmd, mpc = entered[b]
            print(f'PASS {b:4s} at {t:6.2f}s via {cmd}  mpc={mpc}')
        else:
            print(f'FAIL {b:4s} never entered')
    for e in log:
        if e['kind'] == 'miss':
            print(f"MISS at {e['t']:6.2f}s: waited for {e['want']}, was on {e['beat']}")
    for e in log:
        if e['kind'] == 'state':
            print(f"  state {e['t']:6.2f}s " + ' '.join(f'{k}={v}' for k, v in e.items() if k not in ('t', 'kind')))
    seq = [e['beat'] for e in log if e['kind'] == 'beat']
    print('beat sequence:', ' > '.join(seq))


if __name__ == '__main__':
    main()
