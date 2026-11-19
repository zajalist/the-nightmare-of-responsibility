"""Two-second direct HUD ownership/layout proof in free roam; coordinator owns the PIE lifecycle."""
import json
import time
import unreal

S=dict(start=time.monotonic(),handle=None,phase=0,hud=None,widgets=None,baseline=None,done=False,rows=[])


def child(widget,name):
    trees=[t for t in unreal.ObjectIterator(unreal.load_class(None,'/Script/UMG.WidgetTree')) if t.get_outer()==widget]
    matches=[w for t in trees for w in [unreal.find_object(t,name)] if w]
    assert len(matches)==1,(name,[w.get_path_name() for w in matches])
    return matches[0]


def layout():
    w=S['widgets'];slot=w['Size_ContextPrompt'].get_editor_property('slot')
    return dict(width_override=w['Size_ContextPrompt'].get_editor_property('bOverride_WidthOverride'),
        width=w['Size_ContextPrompt'].get_editor_property('width_override'),
        slot={n:str(slot.get_editor_property(n)) for n in ('padding','horizontal_alignment','vertical_alignment')},
        border_padding=str(w['Brd_ToolPrompt'].get_editor_property('padding')),
        border_color=str(w['Brd_ToolPrompt'].get_editor_property('brush_color')))


def end(result,error=None):
    if S['done']:return
    S['done']=True;unreal.unregister_slate_post_tick_callback(S['handle'])
    try:
        if S['hud'] and S['hud'].get_editor_property('bToolStatus'):S['hud'].call_method('HideToolStatus',())
    except Exception as exc:result='FAIL';error=repr(exc)
    with open('P:/FoA/Saved/UIShots/tool_prompt_runtime.json','w') as f:
        json.dump(dict(result=result,error=error,rows=S['rows']),f,indent=2)
    print('TOOL HUD LAYOUT',result,error or '')


def tick(_dt):
    try:
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        assert world,'PIE ended'
        elapsed=time.monotonic()-S['start']
        if elapsed>2:return end('FAIL','Two second cap')
        if S['phase']==0:
            fe=unreal.GameplayStatics.get_actor_of_class(world,unreal.load_class(None,
                '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
            hud=fe.get_editor_property('HUD');assert hud and not hud.get_editor_property('bToolStatus'),'Run from free roam'
            S['hud']=hud;S['widgets']={n:child(hud,n) for n in ('Size_ContextPrompt','Brd_ToolPrompt','Txt_Prompt')}
            S['baseline']=layout()
            hud.call_method('ShowToolStatus',('Ease back',))
            hud.call_method('SetToolFeedback',(.76,True))
            S['phase']=1;S['at']=elapsed+.4
        elif S['phase']==1 and elapsed>S['at']:
            current=layout();assert current['width_override'] and abs(current['width']-320)<.01,current
            assert 'RIGHT' in current['slot']['horizontal_alignment'].upper(),current
            rects={}
            for n,w in S['widgets'].items():
                g=w.get_paint_space_geometry();size=unreal.SlateLibrary.get_local_size(g)
                rects[n]=dict(w=size.x,h=size.y)
            assert abs(rects['Size_ContextPrompt']['w']-320)<1,rects
            assert 0<rects['Txt_Prompt']['w']<=321 and 0<rects['Txt_Prompt']['h']<80,rects
            assert rects['Brd_ToolPrompt']['h']>rects['Txt_Prompt']['h'],rects
            S['rows'].append(dict(label='active',layout=current,rects=rects))
            pc=unreal.GameplayStatics.get_player_controller(world,0)
            unreal.SystemLibrary.execute_console_command(world,
                'Shot showui filename=P:/FoA/Saved/UIShots/tool_prompt_active.png -nosuffix',pc)
            S['hud'].call_method('HideToolStatus',());S['phase']=2;S['at']=elapsed+.2
        elif S['phase']==2 and elapsed>S['at']:
            current=layout()
            # ClearWidthOverride preserves the stored numeric override but restores its exact enabled state.
            for key in ('width_override','slot','border_padding','border_color'):
                assert current[key]==S['baseline'][key],(key,current,S['baseline'])
            assert not S['hud'].get_editor_property('bToolStatus')
            S['rows'].append(dict(label='restored',layout=current));end('PASS')
    except Exception as exc:end('FAIL',repr(exc))


S['handle']=unreal.register_slate_post_tick_callback(tick)
print('Tool HUD direct layout proof armed;2second cap')
