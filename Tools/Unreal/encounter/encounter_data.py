"""The T8 battle's numbers: one source for the PDA_Move / PDA_Opponent data assets and the offline sim (sim_party.py).
Moves: deltas land on the Nightmare (Composure, Resolve); ProgressDelta lands on a garment (the target for the player's
Act moves, the garment itself for enemy moves, so Wrong Button undoes a button). Statuses live on the Nightmare.
Garments: Resistance is how much progress dresses you in it (the Shirt's 6 buttons). The leader row also carries the
fight-wide numbers (Composure, Resolve, the per-turn drain, the knowledge flag, the lose and victory lines) and its Party.
MoveWeights are (Plausible, Suspicious, Open, Enraged): the tier picks a column, and below 30% left a garment enrages.
Base numbers from docs/mechanics/level1-mechanics.html, "Getting dressed, in numbers"; the party is the user's scope
expansion (an old-RPG boss fight)."""

N = ""  # an empty Name cell = None


def mv(name, owner, narration, cost=0, comp=0, res=0, prog=0, applied=N, cleared=N, blocked=N, boosted=N, timed=False,
       reveals=False, stuns=False, telegraph="", swaps=False):
    return dict(DisplayName=name, Owner=owner, ResolveCost=cost, ComposureDelta=comp, ResolveDelta=res,
                ProgressDelta=prog, StatusApplied=applied, StatusCleared=cleared, BlockedBy=blocked, BoostedBy=boosted,
                bTimedInput=timed, bRevealsNext=reveals, bStuns=stuns, bTelegraphed=bool(telegraph),
                TelegraphLine=telegraph, bSwapsTwin=swaps, Narration=narration)


P, O = "Player", "Opponent"
MOVES = {
    # The Nightmare's own commands (Breathe, Mirror)
    "DeepBreath": mv("Deep Breath", P, "In for four. Out for four. Like the video said.", comp=5, res=15,
                     blocked="Constricted"),
    "CheckMirror": mv("Check Mirror", P, "Look at it. Actually look.",
                      cost=5, comp=20, reveals=True),
    # Act, on the Shirt
    "FindArmhole": mv("Find Armhole", P, "Armhole. Found it.",
                      applied="ArmholeFound", cleared="SleeveLabyrinth"),
    "ButtonUp": mv("Button Up", P, "One button. Next button. Don't think.", cost=10, prog=1, timed=True,
                   blocked="SleeveLabyrinth", boosted="ArmholeFound"),
    # Act, on a Sock
    "MatchPair": mv("Match the Pair", P, "These two. These are a pair. Stay.",
                    cleared="Mismatched"),
    "PullOn": mv("Pull On", P, "Heel. Heel. Come on.", cost=5, prog=1,
                 blocked="Mismatched"),
    # Act, on the Trousers
    "UntwistLeg": mv("Untwist the Leg", P, "Other way. Other way round.",
                     cleared="TwistedLeg", stuns=True),
    "StepIn": mv("Step In", P, "Left leg. Don't fall over. Right leg.", cost=5, prog=1,
                 timed=True, blocked="TwistedLeg"),
    # Act, on the Tie
    "Loosen": mv("Loosen", P, "Get off my neck.", cleared="Constricted",
                 stuns=True),
    "TieKnot": mv("Tie the Knot", P, "Over, under, through. Like Dad showed me.", cost=5, prog=1,
                  timed=True, blocked="Constricted"),
    # The Shirt
    "SleeveLabyrinth": mv("Sleeve Labyrinth", O, "There was a sleeve. Where's the sleeve.",
                          applied="SleeveLabyrinth"),
    "StaticCling": mv("Static Cling", O, "Why is it sticking to me.", res=-12),
    "WrongButton": mv("Wrong Button", O, "Wrong hole. Start again.", comp=-8,
                      prog=-1),
    # The Socks
    "SwapPlaces": mv("Swap Places", O, "That's not the same sock.",
                     applied="Mismatched", swaps=True),
    "ColdToes": mv("Cold Toes", O, "The floor's freezing.", comp=-5),
    # The Trousers
    "TwistLeg": mv("Twist", O, "It's twisted. How is it twisted.", applied="TwistedLeg"),
    "Kick": mv("Kick", O, "Ow. My shin.", comp=-10,
               telegraph="The pants pull one leg back."),
    # The Tie
    "Coil": mv("Coil", O, "Too tight. Can't breathe.", applied="Constricted"),
    "Strike": mv("Strike", O, "Not the face.", comp=-12,
                 telegraph="The tie rears back and goes very still."),
    # Everyone
    "HangThere": mv("Hang There", O, "It's just hanging there."),
}

# Mesh is a placeholder until the character lane's rigged garments land (then only Mesh and MeshTransform change).
# GarmentId is what BP_FoAPlayer.Equip(GarmentId) shows on the hero (contract: Shirt, Trousers, Socks, Tie).
# MeshTransform = (x, y, z, yaw, sx, sy, sz) relative to the garment's slot once risen; z keeps the hem in the sand.
SHIRT_MESH = "/Game/FoA/Lux3D/the_shirt_enemy/SM_Lux3D_ShirtEnemy"
CYL = "/Engine/BasicShapes/Cylinder"
OPPONENTS = {
    "Shirt": dict(GarmentId="Shirt", DisplayName="The Shirt (inside out)", Level=30, Resistance=6, DrainPerTurn=4, StartComposure=100,
                  StartResolve=40, ActMoves=["FindArmhole", "ButtonUp"], OpeningMove="HangThere",
                  MoveWeights={"SleeveLabyrinth": (0.5, 1, 1, 3), "StaticCling": (2, 2, 3, 3), "WrongButton": (0, 1, 1, 2),
                               "HangThere": (12, 12, 12, 2)},
                  KnowledgeFlag="Knows.ShirtPattern", Party=["Sock", "Trousers", "Tie", "Sock"],
                  IntroLine="The Shirt (inside out) blocks the way. It has been ironed.",
                  WinLine="Last button. It's just a shirt again.",
                  LoseLine="You sit back down on the bed, half dressed. There goes today.",
                  VictoryLine="You're dressed. Nobody will ever know what that took.",
                  Mesh=SHIRT_MESH, MeshTransform=(0, 0, 48, 90, 1.6, 1.6, 1.6), Tint=(1.0, 1.0, 1.0),
                  EquipSocket="spine_03"),
    "Sock": dict(GarmentId="Socks", DisplayName="A Sock", Level=4, Resistance=1, DrainPerTurn=0, StartComposure=0, StartResolve=0,
                 ActMoves=["MatchPair", "PullOn"], OpeningMove=N,
                 MoveWeights={"SwapPlaces": (0.5, 1, 1, 3), "ColdToes": (2, 2, 3, 3), "HangThere": (12, 12, 12, 2)},
                 KnowledgeFlag=N, Party=[], IntroLine="A sock appears. Then another sock. They are not a pair.",
                 WinLine="One sock on. It's warm. Why is it warm.", LoseLine="", VictoryLine="",
                 Mesh=CYL, MeshTransform=(0, 0, 22, 0, 0.22, 0.22, 0.45), Tint=(0.85, 0.85, 0.85), EquipSocket="foot_l"),
    "Trousers": dict(GarmentId="Trousers", DisplayName="The Pants", Level=12, Resistance=1, DrainPerTurn=0, StartComposure=0,
                     StartResolve=0, ActMoves=["UntwistLeg", "StepIn"], OpeningMove=N,
                     MoveWeights={"TwistLeg": (0.5, 1, 1, 3), "Kick": (1, 2, 2, 3), "HangThere": (12, 12, 12, 2)},
                     KnowledgeFlag=N, Party=[], IntroLine="The pants stand up by themselves. That's new.",
                     WinLine="Pants on. Both legs, same direction.", LoseLine="", VictoryLine="",
                     Mesh=CYL, MeshTransform=(0, 0, 50, 0, 0.55, 0.35, 1.0), Tint=(0.35, 0.35, 0.35),
                     EquipSocket="pelvis"),
    "Tie": dict(GarmentId="Tie", DisplayName="The Tie", Level=18, Resistance=1, DrainPerTurn=0, StartComposure=0, StartResolve=0,
                ActMoves=["Loosen", "TieKnot"], OpeningMove=N,
                MoveWeights={"Coil": (0.5, 1, 1, 3), "Strike": (1, 2, 2, 3), "HangThere": (12, 12, 12, 2)},
                KnowledgeFlag=N, Party=[],
                IntroLine="The tie uncoils. It's been waiting all night.",
                WinLine="A full Windsor. Since when can you do a Windsor?", LoseLine="", VictoryLine="",
                Mesh=CYL, MeshTransform=(0, 0, 60, 0, 0.14, 0.05, 1.2), Tint=(0.2, 0.2, 0.2), EquipSocket="neck_01"),
}

# The character lane's rigged garments (Characters/Garments). Used instead of Mesh as soon as the asset exists:
# rig asset, the attack clip keyword in its AnimSequence names, and the transform for the rig (pivot at the floor,
# modelled facing -Y, so yaw 90 turns it to face the Nightmare; scale as for the placeholder).
RIGS = {"Shirt": ("SK_Garment_Shirt", "Lash", (0, 0, -12, 90, 1.6, 1.6, 1.6)),
        "Sock": ("SK_Garment_Sock", "Hop", (0, 0, -6, 90, 1.0, 1.0, 1.0)),
        "Trousers": ("SK_Garment_Trousers", "Kick", (0, 0, -10, 90, 1.0, 1.0, 1.0)),
        "Tie": ("SK_Garment_Tie", "CoilStrike", (0, 0, 10, 90, 1.4, 1.4, 1.4))}
