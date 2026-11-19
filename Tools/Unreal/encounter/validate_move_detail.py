"""Bounded editor-only function checks; no PIE or persistent actor."""
import json
from pathlib import Path
import unreal
import sys
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import bp_layout

BP='/Game/FoA/Gameplay/Encounter/BP_Encounter'
actor=unreal.get_default_object(unreal.load_class(None,BP+'.BP_Encounter_C'))
original={name:actor.get_editor_property(name) for name in ('Resolve','Statuses','bFreePreview')}
rows=[]
try:
    for move,resolve,statuses,free,expected in [
        ('DeepBreath',0,[],False,'15 Resolve and 5 Composure'),
        ('DeepBreath',0,['Constricted'],False,'Loosen the tie'),
        ('CheckMirror',0,[],True,'Reveal the next enemy moves'),
        ('CheckMirror',0,[],False,'Need 5 Resolve'),
        ('FindArmhole',0,[],False,'x1.75'),
        ('ButtonUp',40,[],False,'Fasten 1 button'),
        ('ButtonUp',40,['SleeveLabyrinth'],False,'Find Armhole'),
        ('ButtonUp',9,[],False,'Need 10 Resolve'),
        ('MatchPair',0,[],False,'Match the socks'),
        ('PullOn',10,['Mismatched'],False,'Match Pair'),
        ('PullOn',10,[],False,'Dress the selected sock'),
        ('UntwistLeg',0,[],False,'Cancel this garment'),
        ('StepIn',10,['TwistedLeg'],False,'Untwist Leg'),
        ('StepIn',10,[],False,'Complete the pants'),
        ('Loosen',0,[],False,'Release constriction'),
        ('TieKnot',10,['Constricted'],False,'Loosen the tie'),
        ('TieKnot',10,[],False,'Complete the tie')]:
        actor.set_editor_property('Resolve',resolve)
        actor.set_editor_property('Statuses',[unreal.Name(s) for s in statuses])
        actor.set_editor_property('bFreePreview',free)
        asset=unreal.load_asset('/Game/FoA/Gameplay/Encounter/Data/DA_Move_'+move)
        detail=str(actor.call_method('MoveDetail',(asset,)))
        can=actor.call_method('CanUseMove',(asset,))
        cost=actor.call_method('MoveCost',(asset,))
        row=dict(move=move,resolve=resolve,statuses=statuses,free=free,detail=detail,can=can,cost=cost)
        rows.append(row)
        assert expected in detail,row
        assert len(detail)<=100,row
finally:
    for name,value in original.items(): actor.set_editor_property(name,value)
    Path('P:/FoA/Saved/Integration/battle_move_detail/cases.json').write_text(json.dumps(rows,indent=2))
print('MoveDetail PASS',len(rows),'representative cases')
exported=bp_layout.parse_t3d(bp_layout.export_t3d(unreal.load_asset(BP)))
Path('P:/FoA/Saved/Integration/battle_move_detail/full_graph.json').write_text(json.dumps(exported['MoveDetail'],indent=2))
unreal.EditorAssetLibrary.save_asset(BP)
unreal.FoAGraphToolsLibrary.capture_graph_png(unreal.load_asset(BP),'MoveDetail','P:/FoA/Saved/GraphShots/BP_Encounter_MoveDetail.png',True)
