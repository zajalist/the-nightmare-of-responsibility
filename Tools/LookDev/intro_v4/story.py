"""Intro v4 timing, the one source for WBP_IntroStory's defaults and M_IntroPlate's HLSL table (intro lane).
Panel index order is fixed: BP_RoomAudio.UpdateIntro keys its cues on it (1-3 sand whoosh, 1 phone buzz, 4 the stinger
and sand scatter), so a panel is lengthened here, never inserted. Lines are docs/design/story/script.md section 1.
  secs     panel length (s)            fin   sand forms the frame in over this (0 = hard cut in)
  at, out  the line's Play and Dismiss times (at 0 = no line: the hook is wordless, the coordinator's call 06:05;
           out 0 = no Dismiss timer)
  fout     sand sweeps the frame out over this (0 = hard cut out)"""
WATCH = 'It never does anything. It just waits for me to give up.'
PANELS = [  # name, line, secs, fin, fout, at, out, mood
    ('Room', "Seventeen days. Not that anyone's counting.", 9.0, 1.9, 0.95, 2.1, 7.8, 0),
    ('Phone', 'Mom made me a list.', 7.2, 1.1, 0.95, 2.4, 6.0, 0),
    ('Shirt', "It's a shirt. It's just a shirt.", 7.0, 1.1, 0.95, 1.5, 5.8, 0),
    ('Watcher', WATCH, 9.0, 1.1, 0.0, 1.8, 8.35, 0),   # blows away as the light fails, gone 0.2 s before the hard cut
    ('Lunge', '', 2.4, 0.0, 1.25, 0.0, 0.0, 0),
]
TOTAL = sum(p[2] for p in PANELS)


def hlsl_table():
    """secs, fin, fout per panel as a ternary chain (Custom nodes take no static arrays on every platform)."""
    rows = [f'float3({p[2]:.2f}, {p[3]:.2f}, {p[4]:.2f})' for p in PANELS]
    expr = rows[-1]
    for i in range(len(rows) - 2, -1, -1):
        expr = f'panel == {i} ? {rows[i]} : {expr}'
    return f'float3 tim = {expr};'


assert 30 <= TOTAL <= 45, TOTAL
assert all((p[1] == '' and p[5] == p[6] == 0) or (0 < p[5] < p[2] and (p[6] == 0 or p[5] < p[6] <= p[2] - p[4]))
           for p in PANELS), 'a line sits inside its panel (words may blow away into the sand-out)'
assert all(p[4] > 0 or p[6] == 0 or p[6] + 0.42 <= p[2] for p in PANELS), 'before a hard cut the 0.42 s scatter ends in time'
assert [p[0] for p in PANELS] == ['Room', 'Phone', 'Shirt', 'Watcher', 'Lunge'], 'BP_RoomAudio cue order'
