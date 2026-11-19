"""T8 "Get Dressed" rhythm battle: one source for the prototype, the sim (sim_rhythm.py) and the UE data build.
Design: docs/design/battle/battle_redesign.md.
A round is one garment. Its attack is a Phrase: 8 counts at the round's Tempo, one char per count:
  L / R  a hand on that side (catch the sock, block the kick, catch the cuff)   key A / D
  H      hop (the trouser leg sweeps low)                                         key Space
  G      grab (the collar lunges, the tie strikes). Missing a G hurts double      key E
  X      a decoy: the odd sock, the tie's feint. Do NOT press.
  .      rest
Dress is the player's attack: the same notation, played after choosing Dress, its windows widened by Grip."""

GOOD, PERFECT = 0.150, 0.060  # judgement windows, seconds either side of the beat
LEAD = 2                      # counts a cue ring shows before its beat (3 when the player knows the pattern)
KNOWN_WIDEN = 1.3             # Knows.ShirtPattern: practice. Every window is this much wider
START_COMPOSURE, BREATHE, PERFECT_HEAL, FLUB_COST, DRESSED_HEAL = 100, 10, 0, 8, 15

ROUNDS = [
    dict(Id="Socks", Garments=["Sock", "Sock"], Tempo=84, GripNeeded=8, Damage=7,
         Intro="Two socks hop out of the sand. They are not a pair.",
         Phrases=["L...R...", "L.R.L.R.", "L.X.R.X."],
         Dress="L.R.G", DressLine="Left foot, right foot, pull.",
         Win="Socks on. They are warm, and somehow that is worse.",
         Flub="You put a sock on your hand. It waves at you."),
    dict(Id="Trousers", Garments=["Trousers"], Tempo=96, GripNeeded=12, Damage=9,
         Intro="The trousers stand up on their own and start to skip.",
         Phrases=["H...H...", "H.H.H.HH", "HH.L.HHR"],
         Dress="H.L.H.R.G", DressLine="Hop, left leg, hop, right leg, zip.",
         Win="Trousers on. Both legs agree, for once.",
         Flub="Both feet in one leg. You hop in a small, sad circle."),
    dict(Id="Shirt", Garments=["Shirt"], Tempo=104, GripNeeded=12, Damage=11,
         Intro="The shirt is inside out, and it knows.",
         Phrases=["L.R.L.R.", "LL.R.RG.", "R.RL.LRG"],
         Dress="G.G.L.R", DressLine="Grab the hem, turn it, left arm, right arm.",
         Win="It is the right way round. It does not like that.",
         Flub="Your head goes through a sleeve. It is very dark in there."),
    dict(Id="Tie", Garments=["Tie"], Tempo=112, GripNeeded=14, Damage=14,
         Intro="The tie uncoils from the collar like something that has waited all night.",
         Phrases=["...G...G", "L.R.X.G.", "LR..X..G", "H.L.R..G"],
         Dress="GGGGGG.LRLG", DressLine="Six buttons, then over, under, around and through.",
         Win="A full Windsor. You did not know you could.",
         Flub="A perfect knot. Around your wrist."),
]
# In the Tie round, H is your own trousers kicking. They are on you now. They still kick.

VICTORY = "You are dressed. Nobody will ever know what it took."
DEFEAT = "You sit down on the bed, half dressed. The day is over."
KNOWN_LINE = "You remember how this goes."  # Knows.ShirtPattern: Socks and Trousers go straight to Dress at full Grip


def ease(grip, needed):
    """Dress window multiplier: 0.6 at no Grip, 1.5 at full."""
    return 0.6 + 0.9 * min(1.0, grip / needed)


def to_win(dress):
    """Beats you must land in a Dress command: three in four, rounded up."""
    n = sum(c != '.' for c in dress)
    return -(-3 * n // 4)
