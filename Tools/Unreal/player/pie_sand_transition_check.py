"""Five-second runtime proof of true sand coverage state and exact original material/visibility restoration."""
import json
import os
import time
import unreal
PARTS=('Body','Face','StartOutfit','Shirt','Trousers','Socks','Tie','Suit','BootsWornMesh')
VALUES=(1.,.5,.1,.5,.8,1.)
S=dict(start=time.monotonic(),index=0,handle=None,pawn=None,original=None,visibility=None,rows=[],done=False)


def slots(p):
    return {n:[c.get_material(i) for i in range(c.get_num_materials())]
            for n in PARTS for c in [p.get_editor_property(n)]}


def finish(result,error=None):
    if S['done']:return
    S['done']=True;unreal.unregister_slate_post_tick_callback(S['handle'])
    if S['pawn']:S['pawn'].call_method('SetSandTransition',(0.,False))
    with open('P:/FoA/Saved/CharacterShots/sand_transition_runtime.json','w') as f:
        json.dump(dict(result=result,error=error,rows=S['rows']),f,indent=2)
    print('SAND TRANSITION',result,error or '')


def tick(_dt):
    try:
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        assert world,'PIE ended';elapsed=time.monotonic()-S['start']
        if elapsed>5:return finish('FAIL','5 second cap')
        p=unreal.GameplayStatics.get_player_character(world,0)
        if S['pawn'] is None:
            assert p and not p.get_editor_property('bSandTransition')
            S['pawn']=p;S['original']=slots(p)
            S['visibility']={n:p.get_editor_property(n).is_visible() for n in ('Hair','Eyebrows')}
        if elapsed<S['index']*.45:return
        if S['index']<len(VALUES):
            amount=VALUES[S['index']];p.call_method('SetSandTransition',(amount,True))
            mid=p.get_editor_property('SandTransitionMID')
            actual=mid.get_scalar_parameter_value('Amount');mode=mid.get_scalar_parameter_value('Transition')
            assert abs(actual-amount)<.0001 and abs(mode-1.)<.0001,(actual,mode)
            assert all(all(m==mid for m in materials) for materials in slots(p).values())
            visibility={n:p.get_editor_property(n).is_visible() for n in ('Hair','Eyebrows')}
            if amount<.25:assert not any(visibility.values())
            if amount>.7:assert visibility==S['visibility']
            S['rows'].append(dict(amount=amount,actual_amount=actual,transition=mode,visibility=visibility,saved_slots=len(p.get_editor_property('SandOriginalMaterials'))))
            folder='P:/FoA/Saved/CharacterShots/sand_transition';os.makedirs(folder,exist_ok=True)
            pc=unreal.GameplayStatics.get_player_controller(world,0)
            unreal.SystemLibrary.execute_console_command(world,f'Shot filename={folder}/coverage_{S["index"]:02d}.png -nosuffix',pc)
            S['index']+=1
        else:
            p.call_method('SetSandTransition',(0.,False))
            assert slots(p)==S['original'],'Original material slots changed'
            assert {n:p.get_editor_property(n).is_visible() for n in S['visibility']}==S['visibility']
            assert not p.get_editor_property('bSandTransition') and not p.get_editor_property('SandOriginalMaterials')
            assert abs(p.get_editor_property('SandTransitionMID').get_scalar_parameter_value('Transition'))<.0001
            finish('PASS')
    except Exception as exc:finish('FAIL',repr(exc))


S['handle']=unreal.register_slate_post_tick_callback(tick)
print('Sand transition restoration proof scheduled; 5 second cap')
