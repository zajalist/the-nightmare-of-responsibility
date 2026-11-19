"""Palm-led snooze slap in centimetres; no engine dependency.
v2 (2026-11-09, "he slaps it from the top"): the hand rises 22 cm over the lid, holds one beat, then drops 20 cm in
0.14 s and is still accelerating at contact (about 2.9 m/s); v1 hovered 10 cm up and touched down at 0.6 m/s.
22 cm keeps the elbow at about shoulder height (build_anims.py guards it), so it reads as a raise, not a chicken wing.
v3 (main, 2026-11-09 "give it impact"): the palm drives 5 cm into the clock in 0.06 s with a small rebound, presses,
sinks 8.5 cm with the collapse onto the pile top (origin +5.5), holds in the pile ~0.4 s, then withdraws.

Contact stays at sequence25.30. Each waypoint has a purpose: gather, raise,
hover, strike, give, follow the collapsing sand, clear it, return to support.
The wrist relaxes during the lift and becomes flat only for the strike.
"""
import wake_math as m


def sample(u, start, contact, forward, up, duration=3.5, contact_time=1.5):
    shift = contact_time - 1.5
    at = lambda t: t + shift
    lift = lambda p, height: m.add(p, m.mul(up, height))
    back = lambda p, distance: m.sub(p, m.mul(forward, distance))
    # Time, wrist position, wrist flexion degrees, torso lean weight.
    keys = [
        (0.0, start, 0.0, 0.0),
        (at(.30), lift(m.lerp(start, contact, .25), 6), 0.0, .25),   # the hand leaves the mattress
        (at(.80), lift(back(contact, 6), 20), 0.0, .80),               # raised high behind the clock: the wind-up
        (at(1.22), lift(back(contact, 2), 22), 0.0, 1.0),              # apex: one reluctant beat
        (at(1.38), lift(contact, 19), 0.0, 1.0),                       # tips over into the strike
        (contact_time, contact, 0.0, 1.0),                             # 19 cm in 0.12 s, still accelerating (~3.2 m/s)
        (at(1.56), lift(contact, -5), -6.0, 1.0),                      # drives 5 cm into the caving clock
        (at(1.66), lift(contact, -4), -3.0, 1.0),                      # a small rebound
        (at(1.95), lift(contact, -4.5), 0.0, 1.0),                     # pressed
        (at(2.35), lift(contact, -8.5), 0.0, 1.0),                     # sinks with the collapsing sand onto the pile top
        (at(2.72), lift(contact, -9), 0.0, .95),                       # held down in the pile, about 0.4 s
        (at(3.05), lift(back(contact, 12), 4), 0.0, .65),              # withdraws, sand falling off the fingers
        (duration, start, 0.0, 0.0),
    ]
    assert all(a[0] < b[0] for a, b in zip(keys, keys[1:])), 'Invalid slap timing'
    if u <= 0:
        return start, 0.0, 0.0
    for a, b in zip(keys, keys[1:]):
        if u <= b[0]:
            t = max(0.0, min(1.0, (u-a[0])/(b[0]-a[0])))
            # Descend without easing out before impact; the next segment absorbs it.
            k = t*t if b[0] == contact_time else m.smooth(t)
            return (m.lerp(a[1], b[1], k), a[2]+(b[2]-a[2])*k,
                    a[3]+(b[3]-a[3])*m.smooth(t))
    return start, 0.0, 0.0
