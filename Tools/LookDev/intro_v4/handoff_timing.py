"""Hook-to-LS_WakeUp timing of an IN1 run (intro lane): the intro's length, the hook stinger and the wake-up alarm in the
runner's audio samples (0.5 s apart, so +-0.5 s), and the film phase start in the driver log.
  python Tools/LookDev/intro_v4/handoff_timing.py <run>/IN1"""
import json
import sys

run = sys.argv[1]
first = {}
for r in json.load(open(f'{run}/audio.json')):
    for snd in r['sounds']:
        first.setdefault(snd[0], r['t'])
log = json.load(open(f'{run}/play.json'))['log']
end = next(e for e in log if e.get('kind') == 'intro_end')
sting, alarm = first.get('SFX_Horror_Stinger_01'), first.get('SFX_Clock_AlarmMechanism_01')
print(dict(intro_s=end['secs'], panels=end['panels'], phase=end['phase'], stinger=sting, alarm=alarm,
           stinger_to_alarm=round(alarm - sting, 2) if sting and alarm else None))
