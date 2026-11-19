"""Engine-side count for pie_burst_cap.py: parses the 'au.DumpActiveSounds' blocks the driver wrote to FoA.log after
each window and counts Sand_Burst entries per dump (the audio device's own active-sound list).
  python Tools/Audio/cap_dump_report.py <first FoA.log line of the run>"""
import re
import sys

lines = open('P:/FoA/Saved/Logs/FoA.log', encoding='utf-8', errors='replace').read().splitlines()[int(sys.argv[1]):]
key, counts, total = None, {}, {}
for ln in lines:
    m = re.search(r'\[horror-cap\] dump (\w+\.\d)', ln)
    if m:
        key = m.group(1)
        counts[key] = 0
        continue
    if key and 'Active Sound Count' in ln:
        total[key] = int(re.search(r'Count: (\d+)', ln).group(1))
    elif key and 'LogAudio' in ln and 'Sand_Burst' in ln:
        counts[key] += 1
for k in counts:
    print(f'{k}: Sand_Burst active in the device = {counts[k]} (device total {total.get(k)})')
