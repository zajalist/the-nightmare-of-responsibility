"""Offline balance sim for the T8 rhythm battle (rhythm_data.py). Same rules as the prototype and BP_Encounter.
  python Tools/Unreal/encounter/sim_rhythm.py [runs]
A player is a timing spread (Gaussian, seconds), a lapse rate (wrong key or frozen) and a decoy-press rate.
Prints win rate, fight length in minutes and the lowest Composure a winner hit, per skill, first day and with Knows.ShirtPattern."""
import random
import sys

from rhythm_data import (BREATHE, DRESSED_HEAL, FLUB_COST, GOOD, KNOWN_WIDEN, LEAD, PERFECT, PERFECT_HEAL, ROUNDS, START_COMPOSURE, ease,
                         to_win)

WIDEN = 1.0
SKILLS = {"strong": (0.050, 0.03, 0.08), "typical": (0.085, 0.08, 0.25),
          "struggling": (0.120, 0.14, 0.40), "very weak": (0.160, 0.22, 0.55)}


def judge(rng, sigma, lapse, scale=1.0):
    scale *= WIDEN
    """2 perfect, 1 good, 0 miss."""
    if rng.random() < lapse:
        return 0
    e = abs(rng.gauss(0, sigma))
    return 2 if e <= PERFECT * scale else 1 if e <= GOOD * scale else 0


def fight(rng, skill, knows=False):
    sigma, lapse, decoy = SKILLS[skill]
    global WIDEN
    WIDEN = KNOWN_WIDEN if knows else 1.0
    if knows:  # memory: yesterday's patterns are today's
        lapse, decoy = lapse * 0.6, decoy * 0.5
    comp, t, low = START_COMPOSURE, 5.0, START_COMPOSURE  # intro
    for i, r in enumerate(ROUNDS):
        beat = 60.0 / r["Tempo"]
        need = r["GripNeeded"]
        grip, k = (need if knows and i < 2 else 0), 0
        t += 2.0  # round line
        while True:
            if grip < need and not (knows and i < 2):  # their phrase
                ph = r["Phrases"][min(k, len(r["Phrases"]) - 1) if k < len(r["Phrases"]) else k % len(r["Phrases"])]
                k += 1
                t += (len(ph) + LEAD) * beat + 0.8
                for c in ph:
                    if c == '.':
                        continue
                    if c == 'X':
                        if rng.random() < decoy:
                            comp -= r["Damage"]
                            grip = max(0, grip - 1)
                        else:
                            grip += 1
                        continue
                    j = judge(rng, sigma, lapse)
                    if j == 0:
                        comp -= r["Damage"] * (2 if c == 'G' else 1)
                        low = min(low, comp)
                        grip = max(0, grip - 1)
                    else:
                        grip += j
                        comp = min(START_COMPOSURE, comp + (PERFECT_HEAL if j == 2 else 0))
                    if comp <= 0:
                        return "lose", t, 0
                grip = min(grip, need)
                t += 1.2  # the choice
                if grip < need and not (comp <= 30 and grip >= need / 2):
                    comp = min(START_COMPOSURE, comp + BREATHE)  # Breathe: let it come again
                    continue
            # Dress
            d = r["Dress"]
            t += (len(d) + LEAD) * beat + 0.8
            hits = sum(judge(rng, sigma, lapse, ease(grip, need)) > 0 for c in d if c != '.')
            if hits >= to_win(d):
                t += 2.5  # equip beat
                comp = min(START_COMPOSURE, comp + (DRESSED_HEAL if i < len(ROUNDS) - 1 else 0))
                break
            comp -= FLUB_COST
            grip //= 2
            t += 1.5
            if comp <= 0:
                return "lose", t, 0
    return "win", t + 5.0, low


def report(skill, runs, knows=False):
    rng = random.Random(7)
    out = [fight(rng, skill, knows) for _ in range(runs)]
    wins = sorted(t / 60 for r, t, _ in out if r == "win")
    loses = sorted(t / 60 for r, t, _ in out if r == "lose")
    q = lambda xs, f: f"{xs[int(f * (len(xs) - 1))]:.1f}" if xs else "-"  # noqa: E731
    left = sorted(c for r, _, c in out if r == "win")
    print(f"{skill + (' knows' if knows else ''):<18} win {100 * len(wins) / runs:5.1f}%   win minutes: median "
          f"{q(wins, .5)} p90 {q(wins, .9)}   lose at minute {q(loses, .5)}   lowest composure {q(left, .5)}")
    return len(wins) / runs, wins


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    res = {s: report(s, n) for s in SKILLS}
    for s in SKILLS:
        report(s, n, knows=True)
    # self-check: skill must matter, and the typical fight must sit in the 2.5 to 5 minute band
    assert res["strong"][0] > res["typical"][0] > res["struggling"][0] > res["very weak"][0], "skill does not matter"
    med = res["typical"][1][len(res["typical"][1]) // 2]
    assert 2.5 <= med <= 5.0, f"typical fight is {med:.1f} min"
    print("self-check ok")
