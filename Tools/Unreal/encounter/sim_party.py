"""Offline balance sim for the T8 party battle; the same rules as BP_Encounter / BP_Garment, numbers from encounter_data.
  python Tools/Unreal/encounter/sim_party.py [runs]
Prints win rate and turns to win for a few player skill levels (chance to hit each prompted key)."""
import random
import sys

from encounter_data import MOVES, OPPONENTS

KEYS, KEYS_TO_HIT, TIER = 3, 2, 2  # BP_Encounter defaults: KeyCount, KeysToHit, Tier (2 = Open)


class Garment:
    def __init__(self, gid, rng, tier, opening=False):
        self.id, self.d, self.rng, self.tier = gid, OPPONENTS[gid], rng, tier
        self.progress, self.stunned, self.intent = 0, False, None
        self.pick(opening)

    @property
    def alive(self):
        return self.progress < self.d["Resistance"]

    @property
    def enraged(self):
        return self.d["Resistance"] - self.progress < 0.3 * self.d["Resistance"]

    def pick(self, opening=False):
        if opening and self.d["OpeningMove"]:
            self.intent = self.d["OpeningMove"]
            return
        col = 3 if self.enraged else self.tier
        total, pick = 0.0, None
        for m, w in self.d["MoveWeights"].items():  # one-pass weighted pick, as PickIntent does
            total += w[col]
            if w[col] > 0 and self.rng.random() * total < w[col]:
                pick = m
        self.intent = pick


def battle(rng, p_key, p_wide=None, knows=False, tier=TIER):
    p_wide = p_wide or min(1.0, p_key + 0.13)
    lead = OPPONENTS["Shirt"]
    order = list(lead["Party"])
    order.insert(len(order) // 2, "Shirt")
    gs = [Garment(g, rng, tier, opening=(g == "Shirt" and knows)) for g in order]
    comp, res, st, free = lead["StartComposure"], lead["StartResolve"], set(), knows
    for turn in range(1, 80):
        alive = [g for g in gs if g.alive]

        def can(mid):
            m = MOVES[mid]
            cost = 0 if (m["bRevealsNext"] and free) else m["ResolveCost"]
            return res >= cost and not (m["BlockedBy"] and m["BlockedBy"] in st)

        # ---- a sensible player
        target, mid = None, None
        threat = [g for g in alive if MOVES[g.intent]["bTelegraphed"] and not g.stunned]
        stun = [(g, a) for g in threat for a in g.d["ActMoves"] if MOVES[a]["bStuns"] and can(a)]
        if stun:
            target, mid = stun[0]
        elif comp <= 25 and can("CheckMirror"):
            mid = "CheckMirror"
        else:
            target = min(alive, key=lambda g: (g.d["Resistance"] - g.progress, g.d["Resistance"]))
            prog = next(a for a in target.d["ActMoves"] if MOVES[a]["ProgressDelta"] > 0)
            if can(prog):
                mid = prog
            elif MOVES[prog]["BlockedBy"] in st:  # clear the blocking status with whichever Act move clears it
                clear = [(g, a) for g in alive for a in g.d["ActMoves"] if MOVES[a]["StatusCleared"] == MOVES[prog]["BlockedBy"]]
                target, mid = clear[0]
            elif can("DeepBreath"):
                mid = "DeepBreath"
            else:  # constricted and broke: loosen the tie
                target, mid = next((g, "Loosen") for g in alive if g.id == "Tie") if any(g.id == "Tie" for g in alive) \
                    else (None, "CheckMirror" if can("CheckMirror") else "FindArmhole")
        m = MOVES[mid]
        cost = 0 if (m["bRevealsNext"] and free) else m["ResolveCost"]
        if m["bRevealsNext"]:
            free = False
        mult = 1
        if m["bTimedInput"]:
            p = p_wide if (m["BoostedBy"] and m["BoostedBy"] in st) else p_key
            st.discard(m["BoostedBy"])
            hits = sum(rng.random() < p for _ in range(KEYS))
            mult = 2 if hits == KEYS else (1 if hits >= KEYS_TO_HIT else 0)
        res = max(0, min(lead["StartResolve"], res - cost + m["ResolveDelta"]))
        comp = max(0, min(lead["StartComposure"], comp + m["ComposureDelta"]))
        st.discard(m["StatusCleared"])
        if m["StatusApplied"]:
            st.add(m["StatusApplied"])
        if target is not None:
            target.progress = max(0, min(target.d["Resistance"], target.progress + m["ProgressDelta"] * mult))
            if m["bStuns"] and target.alive:
                target.stunned = True
        if not any(g.alive for g in gs):
            return "win", turn, comp
        # ---- the enemy phase
        for g in gs:
            if not g.alive:
                continue
            if g.stunned:
                g.stunned = False
                continue
            e = MOVES[g.intent]
            comp = max(0, comp + e["ComposureDelta"])
            res = max(0, min(lead["StartResolve"], res + e["ResolveDelta"]))
            if e["StatusApplied"]:
                st.add(e["StatusApplied"])
            g.progress = max(0, min(g.d["Resistance"], g.progress + e["ProgressDelta"]))
        comp = max(0, comp - lead["DrainPerTurn"])
        for g in gs:
            if g.alive:
                g.pick()
        if comp <= 0:
            return "lose", turn, comp
    return "lose", 80, comp


def report(label, runs, **kw):
    rng = random.Random(11)
    out = [battle(rng, **kw) for _ in range(runs)]
    wins = sorted(t for r, t, _ in out if r == "win")
    q = lambda f: wins[int(f * (len(wins) - 1))] if wins else "-"  # noqa: E731
    left = sorted(c for r, _, c in out if r == "win")
    print(f"{label:<30} win {100 * len(wins) / runs:5.1f}%   turns to win: median {q(.5)}, p10 {q(.1)}, p90 {q(.9)}"
          f"   composure left (median) {left[len(left) // 2] if left else '-'}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    report("strong (95% per key)", n, p_key=0.95)
    report("typical (80% per key)", n, p_key=0.8)
    report("struggling (60% per key)", n, p_key=0.6)
    report("very weak (40% per key)", n, p_key=0.4)
    report("typical, knows the pattern", n, p_key=0.8, knows=True)
