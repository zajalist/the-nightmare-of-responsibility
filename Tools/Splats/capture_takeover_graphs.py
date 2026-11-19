"""Bounded graph captures, one private render target at a time."""
import json
import os
from pathlib import Path
import time
import unreal
OUT=Path('P:/FoA/Saved/GraphShots/RoomTakeover');OUT.mkdir(parents=True,exist_ok=True)
BP=unreal.load_asset('/Game/FoA/Gameplay/Ambient/BP_RoomTakeover')
MAT=unreal.load_asset('/Game/FoA/Art/Materials/M_SandPainting')
INTRO=unreal.load_asset('/Game/FoA/UI/Materials/M_UI_Panel')
NAMES=['SetStage','Reset','Grow','ApplyStage','ApplyDeposit','ApplyClothingClues','PlayScare','EndScare','UpdatePainting','WatchPainting','InspectPainting','PaintingThought','EndPainting','ResetPainting','EventGraph']
TASKS=[(BP,n,OUT/(n+'.png')) for n in NAMES]+[(MAT,'',OUT/'SandPaintingMaterial.png')]
if os.environ.get('FOA_VASE_GRAPHS')=='1':
    NAMES=['ResetVase','CancelVaseFormation','BreakVaseThenBoss','ShatterVase','StepVase','FinishVaseBoss','ApplyVaseShard']
    TASKS=[(BP,n,OUT/(n+'.png')) for n in NAMES]
if os.environ.get('FOA_MATERIAL_GRAPHS')=='1':
    TASKS=[(MAT,'',OUT/'SandPaintingMaterial.png'),(INTRO,'',OUT/'IntroRiceInkMaterial.png')]
RECEIPT='materials_complete.json' if os.environ.get('FOA_MATERIAL_GRAPHS')=='1' else 'complete.json'
S={'i':0,'at':0,'start':time.time(),'handle':None,'files':[]}
def tick(dt):
    try:
        if time.time()-S['start']>50:raise RuntimeError('Graph capture timeout')
        if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE began; graph capture stopped')
        if time.time()-S['at']<2.4:return
        if S['i']:
            assert TASKS[S['i']-1][2].exists(),TASKS[S['i']-1][2]
        if S['i']==len(TASKS):
            unreal.unregister_slate_post_tick_callback(S['handle'])
            for asset in {a for a,n,p in TASKS}:unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(asset)
            (OUT/RECEIPT).write_text(json.dumps(S['files'],indent=1));return
        a,n,path=TASKS[S['i']]
        unreal.FoAGraphToolsLibrary.capture_graph_png(a,n,str(path),True)
        S['files'].append(str(path));S['at']=time.time();S['i']+=1
    except Exception as e:
        unreal.unregister_slate_post_tick_callback(S['handle'])
        (OUT/'error.txt').write_text(str(e))
S['handle']=unreal.register_slate_post_tick_callback(tick)
