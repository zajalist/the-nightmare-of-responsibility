"""GPU cost of M_PP_FaceBlur from the profilegpu frames a FOA_PROF=1 face burst requests (plain Python, after the burst).
  python Tools/Unreal/face/pp_cost.py [run]   -> prints and writes Saved/FaceShots/<run>/pp_cost.json
For each '[face] profilegpu <tag>' marker, the next 'Profiling the next GPU frame' block is searched for the face
blur pass and the other post-process material passes (ms on this GPU at the PIE viewport size)."""
import json
import re
import sys
from pathlib import Path

LOG = Path('P:/FoA/Saved/Logs/FoA.log')


def parse(text):
    """UE 5.8 profilegpu tables: the leaf row named M_PP_FaceBlur carries its GPU ms (last 'x.xxx ms' on the row)."""
    out = {}
    for m in re.finditer(r'\[face\] profilegpu (\w+)', text):
        tag = m.group(1)
        start = text.find('GPU Profile for Frame', m.end())
        if start < 0:
            continue
        end = text.find('GPU Profile for Frame', start + 10)
        block = text[start:end if end > 0 else start + 600000]
        rows = []
        for line in block.splitlines():
            if re.search(r'M_PP_|PostProcessing |Tonemap ', line):
                ms = re.findall(r'(\d+\.\d+) ms', line)
                segs = [x.strip() for x in line.split('Display:')[-1].split('┃') if x.strip()]
                rows.append((segs[-1][:60] if segs else '', float(ms[-1]) if ms else None))
        frame = re.search(r'Frame Time\s*:\s*(\d+\.\d+)ms', block)
        size = re.search(r'Tonemap (\d+)x(\d+)', block)
        face = [r[1] for r in rows if r[0].startswith('M_PP_FaceBlur')]
        px = int(size.group(1)) * int(size.group(2)) if size else None
        out[tag] = dict(face_ms=face[0] if face else None, frame_ms=float(frame.group(1)) if frame else None,
                        viewport=size.group(0) if size else None,
                        face_ms_1080p=round(face[0] * 1920 * 1080 / px, 3) if face and px else None, rows=rows)
    return out


if __name__ == '__main__':
    run = sys.argv[1] if len(sys.argv) > 1 else None
    res = parse(LOG.read_text(encoding='utf-8', errors='ignore'))
    for tag, r in res.items():
        print(tag, 'face blur', r['face_ms'], 'ms at', r['viewport'], '->', r['face_ms_1080p'], 'ms at 1080p; GPU frame', r['frame_ms'], 'ms')
    if run:
        Path(f'P:/FoA/Saved/FaceShots/{run}/pp_cost.json').write_text(json.dumps(res, indent=1))
