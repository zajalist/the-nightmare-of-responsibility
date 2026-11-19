"""Level 2 page rows, using the existing encounter data schema and rules."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'encounter'))
from encounter_data import mv

ROOT = '/Game/FoA/Level2/CV'
DATA = ROOT + '/Data'
P, O = 'Player', 'Opponent'
MOVE_ICONS=dict(CVFindDetail='Target',CVRewriteExperience='Resolve',CVSortFacts='Button',
                CVRewriteLogistics='Knot',CVLoosenClaim='Grip',CVRewriteReliability='Foot')
MOVES = {
    'CVFindDetail': mv('Find a detail', P, 'I did put the room back together.',
                       applied='ArmholeFound', cleared='SleeveLabyrinth'),
    'CVRewriteExperience': mv('Rewrite experience', P, 'Five years. In my own room.', cost=10, prog=1,
                              timed=True, blocked='SleeveLabyrinth', boosted='ArmholeFound'),
    'CVSortFacts': mv('Sort the facts', P, 'Stocking. Sorting. Inventory.', cleared='Mismatched', stuns=True),
    'CVRewriteLogistics': mv('Rewrite skills', P, 'The labels were straight.', cost=5, prog=1, blocked='Mismatched'),
    'CVLoosenClaim': mv('Loosen the claim', P, 'Available. That part is true.', cleared='Constricted', stuns=True),
    'CVRewriteReliability': mv('Rewrite availability', P, 'I got up. Eventually.', cost=5, prog=1,
                               timed=True, blocked='Constricted'),
    'CVOriginalExperience': mv('The original experience', O, 'I have no job experience.', comp=-8, prog=-1,
                               telegraph='You see the old line through the ink.'),
    'CVBlank': mv('Blanked', O, 'The experience field whites out.', applied='SleeveLabyrinth'),
    'CVOriginalLogistics': mv('The original skills', O, 'I straightened some labels.', comp=-10, prog=-1,
                              telegraph='You see the shelf under the heading.'),
    'CVMisfile': mv('Misfiled', O, 'The facts move into the wrong field.', applied='Mismatched'),
    'CVOriginalReliability': mv('The original availability', O, 'I got out of bed today.', comp=-12, prog=-1,
                                telegraph='You see seventeen boxes fill in.'),
    'CVConstrict': mv('Cornered', O, 'The margins close around the claim.', applied='Constricted'),
    'CVWait': mv('The page holds still', O, 'The ink dries.'),
}

OPPONENTS = {}
for oid, title, acts, attack, status, line in (
    ('CVExperience', 'Experience', ['CVFindDetail', 'CVRewriteExperience'], 'CVOriginalExperience', 'CVBlank',
     '5 Years of Experience in Interior Management.'),
    ('CVLogistics', 'Skills', ['CVSortFacts', 'CVRewriteLogistics'], 'CVOriginalLogistics', 'CVMisfile',
     '3 Years of Experience in Warehousing and Office Logistics.'),
    ('CVReliability', 'Availability', ['CVLoosenClaim', 'CVRewriteReliability'], 'CVOriginalReliability', 'CVConstrict',
     'Available Immediately. Reliable Under Pressure.'),
):
    OPPONENTS[oid] = dict(DisplayName=title, Level=1, Resistance=4, DrainPerTurn=2, StartComposure=100,
        StartResolve=40, ActMoves=acts, OpeningMove='CVWait',
        # Assisted-policy estimate: 100/100 wins, median24/p90 33 turns (sim_cv.py seeds0..99).
        MoveWeights={attack:(1,1,1,2), status:(1,1,1,1), 'CVWait':(4,4,4,4)},
        KnowledgeFlag='Knows.CVPattern', Party=[], IntroLine=line, WinLine=title + ' revised.',
        LoseLine='The old words come back. Try the draft again.', VictoryLine='The page is complete. Submit C.V.',
        Mesh='/Engine/BasicShapes/Cube', MeshTransform=(0,0,70,0,.035,1.0,1.4), Tint=(.92,.92,.92),
        GarmentId='', EquipSocket='', Rig=None, AttackAnim=None)
OPPONENTS['CVExperience']['Party'] = ['CVLogistics', 'CVReliability']

DETAILS = {
    'CVFindDetail':'Clear Blanked. Widen the next Rewrite experience timing window.',
    'CVRewriteExperience':'Revise one part of Experience. Perfect timing revises two.',
    'CVSortFacts':'Clear Misfiled. Cancel this section\'s next action.',
    'CVRewriteLogistics':'Revise one part of Skills. No timing required.',
    'CVLoosenClaim':'Clear Cornered. Cancel this section\'s next action.',
    'CVRewriteReliability':'Revise one part of Availability. Perfect timing revises two.',
}
STATUS_LABELS = {'SleeveLabyrinth':'Blanked', 'ArmholeFound':'Detail found', 'Mismatched':'Misfiled',
                 'Constricted':'Cornered'}


def employability(progress):
    return 60 + 40 * sum(min(4, max(0, p)) for p in progress) // 12
