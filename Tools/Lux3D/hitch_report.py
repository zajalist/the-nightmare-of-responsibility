"""Summarise 'stat dumphitches' blocks in a log slice: per hitch, the game-thread items directly under FrameTime
(depth 3) above 2 ms; then totals per item across all hitches.
  python Tools/Lux3D/hitch_report.py Saved/WorldShots/perf/<run>_log.txt"""
import collections
import re
import sys

LINE = re.compile(r'LogStats:(\s+)([\d.]+)ms \(\s*\d+\)\s+-\s+(.+?)( - STAT|$| - STATGROUP)')
blocks, cur, in_game = [], None, False
for raw in open(sys.argv[1], encoding='utf-8', errors='replace'):
    if 'Thread Hitch' in raw:
        ms = float(re.search(r'([\d.]+)ms', raw).group(1))
        cur = {'ms': ms, 'items': collections.Counter()}
        blocks.append(cur)
        in_game = False
        continue
    if cur is None:
        continue
    if '------------------ Game Thread' in raw:
        in_game = True
        continue
    if '------------------ ' in raw:
        in_game = False
        continue
    m = LINE.search(raw)
    if in_game and m and len(m.group(1)) == 7:   # depth 3: the frame's direct children
        cur['items'][m.group(3).strip()] += float(m.group(2))

tot = collections.Counter()
for i, b in enumerate(blocks, 1):
    top = [(k, round(v, 1)) for k, v in b['items'].most_common(3) if v >= 2]
    tot.update(b['items'])
    print(f"{i:3d} {b['ms']:6.1f} ms  {top}")
print('\nhitches', len(blocks), 'total hitch ms', round(sum(b['ms'] for b in blocks)))
for k, v in tot.most_common(8):
    print(f'{v:8.1f} ms  {k}')
