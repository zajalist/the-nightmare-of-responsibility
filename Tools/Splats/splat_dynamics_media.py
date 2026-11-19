"""Summarize measured CSV states and extract proof stills. No editor access."""
import csv
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import sys

OUT = Path('P:/FoA/Saved/Codex/splat_dynamics')
MARKER = re.compile(r'(dream|city)_(off_rest|on_rest|off_sand|on_sand)_(before|after)\.png')


def summarize(path):
    segments = {}
    current = None
    with path.open(newline='', encoding='utf-8-sig') as stream:
        for row in csv.DictReader(stream):
            match = MARKER.search(row.get('EVENTS', ''))
            if match:
                key = match[1] + '_' + match[2]
                current = key if match[3] == 'before' else None
                if current:
                    segments[current] = []
            if current:
                try:
                    gpu = float(row['GPUTime'])
                    if gpu > 0:
                        segments[current].append(gpu)
                except (KeyError, ValueError, TypeError):
                    pass
    result = {}
    for key, values in segments.items():
        # Exclude boundary screenshot and editor-call frames by taking the middle half.
        samples = sorted(values[len(values)//4:len(values)*3//4])
        assert len(samples) >= 10, (key, 'too few measured frames', len(samples))
        result[key] = {'gpu_ms_median': round(statistics.median(samples), 4),
                       'gpu_ms_p95': round(samples[math.ceil(len(samples)*.95)-1], 4),
                       'sample_frames': len(samples), 'segment_frames': len(values), 'source': path.name}
    return result


def main():
    result = {}
    for path in sorted(OUT.glob('*_perf_Profile*.csv')):
        result.update(summarize(path))
    if result:
        (OUT / 'gpu_timings.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
    for kind in ('dream', 'city'):
        video = OUT / (kind + '_dynamics.mp4')
        if not video.exists():
            continue
        for label, seconds in [('ambient', 1), ('fall', 4.5), ('pile', 6.5), ('reform', 9), ('restored', 12.5)]:
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(seconds), '-i', str(video),
                            '-frames:v', '1', str(OUT / (kind+'_'+label+'.png'))], check=True)
        p = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=width,height,nb_frames',
                            '-of', 'json', str(video)], capture_output=True, text=True, check=True)
        (OUT / (kind+'_video_metadata.json')).write_text(p.stdout)


if __name__ == '__main__':
    main()
