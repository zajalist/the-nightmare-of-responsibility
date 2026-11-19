"""Summarize Unreal's native CSV profiler output; no runtime instrumentation.

Coordinator closes the editor, then launches one game process:
  UnrealEditor.exe P:/FoA/FoA.uproject /Game/FoA/Maps/L_Tutorial_Bedroom
    -game -windowed -ResX=960 -ResY=540 -DisableAsyncCompute
    -csvCaptureFrames=3000 -ExitAfterCsvProfiling -csvCompression=0

UE 5.8 CsvProfiler.cpp starts a boot capture from csvCaptureFrames, includes a
dummy engine-init first frame, writes Saved/Profiling/CSV and exits on completion.
This script preserves that first frame in the total and reports it separately.
Do not compare engine initialization directly with PIE's already-loaded world.
"""
import csv
import json
from pathlib import Path
import sys

import numpy as np


def summarize(path):
    with open(path, encoding='utf-8-sig', newline='') as stream:
        rows = csv.reader(stream)
        header = next(rows)
        assert 'FrameTime' in header, f'No native FrameTime column: {header}'
        column = header.index('FrameTime')
        frames = []
        for row in rows:
            try:
                value = float(row[column])
            except (ValueError, IndexError):
                continue  # trailing profiler metadata/repeated header
            if np.isfinite(value) and value >= 0:
                frames.append(value)
    assert len(frames) > 1, 'Native profiler did not capture frames'

    def stats(values):
        return dict(frames=len(values), seconds=round(sum(values)/1000, 3),
                    p50_ms=round(float(np.percentile(values, 50)), 2),
                    p95_ms=round(float(np.percentile(values, 95)), 2),
                    p99_ms=round(float(np.percentile(values, 99)), 2),
                    over_50_ms=sum(x > 50 for x in values), max_ms=max(values))

    elapsed = 0.0
    hitches = []
    for i, ms in enumerate(frames):
        elapsed += ms/1000
        if ms > 50:
            hitches.append(dict(frame=i, elapsed_s=round(elapsed, 3), ms=ms))
    result = dict(source=str(Path(path).resolve()), all_frames=stats(frames),
                  engine_init_first_frame_ms=frames[0],
                  after_engine_init=stats(frames[1:]), hitches=hitches,
                  caveat='Cold standalone boot capture; PIE starts in an already-loaded editor. '
                         'Transition input timing must be recorded separately.')
    target = Path(path).with_suffix('.summary.json')
    target.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    summarize(sys.argv[1])
