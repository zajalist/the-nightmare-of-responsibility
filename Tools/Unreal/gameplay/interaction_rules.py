"""Shared constants and offline expectations for the authored interaction sequence."""
KEY_SPEED = 90.0
KEY_STOP = 45.0
KEY_FINISH_INPUT = 105.0
SCREW_SPEED = 300.0
SCREW_TURNS = 2
SCREW_COUNT = 4


def may_apply(stage, row, known=(), boots_worn=False):
    if row['Verb'] in ('Look', 'Notify'):
        return True
    if stage < 2:
        return False
    key, nxt, give = row['Interactable'], row['NextState'], row['Give']
    if give == 'Key' and stage < 3 and 'Knows.KeyInBoot' not in known:
        return False
    if key == 'Door':
        if nxt == 'KeyJammed' and row['Item'] == 'Key':
            return (stage >= 4 and boots_worn) or 'Knows.KeySnaps' in known
        if nxt in ('PlateOff', 'LatchFree'):
            return stage >= 5 or 'Knows.KeySnaps' in known
        if nxt == 'HandleOff':
            return stage >= 6 or 'Knows.WardrobeFalls' in known
    if key == 'Shirt' and row['Verb'] == 'Take':
        return stage >= 7
    if key.startswith('Boot') and nxt == 'Worn':
        return stage >= 4
    return True


def tool_step(mode, angle, input_angle, step, turn, dt):
    """Expected bounded turning behavior used by native runtime proof assertions."""
    dt = min(max(dt, 0.0), 0.1)
    turn = min(max(turn, -1.0), 1.0)
    if mode == 'Key':
        input_angle = max(0.0, min(KEY_FINISH_INPUT, input_angle + turn * KEY_SPEED * dt))
        return min(KEY_STOP, input_angle), input_angle, step, input_angle >= KEY_FINISH_INPUT
    angle = max(0.0, angle + turn * SCREW_SPEED * dt)
    if angle >= 360.0 * SCREW_TURNS:
        step += 1
        angle = 0.0
    return angle, input_angle, step, step >= SCREW_COUNT


if __name__ == '__main__':
    from data_rows import INTERACTIONS
    boot = next(r for r in INTERACTIONS if r['Give'] == 'Key')
    key = next(r for r in INTERACTIONS if r['Item'] == 'Key' and r['NextState'] == 'KeyJammed')
    screw = next(r for r in INTERACTIONS if r['Item'] == 'Screwdriver' and r['NextState'] == 'PlateOff')
    shirt = next(r for r in INTERACTIONS if r['Give'] == 'Shirt')
    assert not may_apply(2, boot) and may_apply(3, boot)
    assert may_apply(2, boot, {'Knows.KeyInBoot'})
    assert not may_apply(3, key) and not may_apply(4, key)
    assert may_apply(4, key, boots_worn=True) and may_apply(2, key, {'Knows.KeySnaps'})
    assert not may_apply(4, screw) and may_apply(2, screw, {'Knows.KeySnaps'})
    assert not may_apply(6, shirt) and may_apply(7, shirt)
    assert all(may_apply(-1, r) for r in INTERACTIONS if r['Verb'] == 'Look')
    a, i, s, done = 0.0, 0.0, 0, False
    for _ in range(20):
        a, i, s, done = tool_step('Key', a, i, s, 0, 1 / 30)
    assert (a, i, s, done) == (0, 0, 0, False)
    for _ in range(20):
        a, i, s, done = tool_step('Key', a, i, s, 1, 1 / 30)
    assert a == KEY_STOP and not done
    for _ in range(30):
        a, i, s, done = tool_step('Key', a, i, s, 1, 1 / 30)
    assert done and a == KEY_STOP
    a, i, s = 0.0, 0.0, 0
    for _ in range(288):
        a, i, s, done = tool_step('Screwdriver', a, i, s, 1, 1 / 30)
    assert done and s == 4
    print('PASS first-day order, known shortcuts, idle tool, key tension stop, and four two-turn screws in9.6s')
