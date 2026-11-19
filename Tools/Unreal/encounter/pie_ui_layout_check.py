"""Twelve-second command layout proof at one actual viewport size selected by the coordinator."""
import json
import os
import time
import unreal

S=dict(start=time.monotonic(),handle=None,phase=0,at=0,index=0,rows=[],old=None,done=False)
EXPECTED=(int(os.environ.get('FOA_EXPECT_WIDTH','1280')),int(os.environ.get('FOA_EXPECT_HEIGHT','720')))
SIZES=(EXPECTED,)


def rect(widget):
    # GetCachedGeometry aliases TickSpaceGeometry. These event-driven widgets do not tick;
    # paint geometry is the real arranged rectangle used for the visible frame.
    geometry=widget.get_paint_space_geometry()
    origin=unreal.SlateLibrary.local_to_absolute(geometry,unreal.Vector2D())
    size=unreal.SlateLibrary.get_absolute_size(geometry)
    local=unreal.SlateLibrary.get_local_size(geometry)
    return dict(x=origin.x,y=origin.y,w=size.x,h=size.y,local_w=local.x,local_h=local.y)


def live_child(widget,name):
    # BindWidget members may retain an unpainted template after nested-widget recompilation.
    # Resolve the object in this live UserWidget's own duplicated tree, never a class/default tree.
    trees=[tree for tree in unreal.ObjectIterator(unreal.load_class(None,'/Script/UMG.WidgetTree')) if tree.get_outer()==widget]
    candidates=[child for tree in trees for child in [unreal.find_object(tree,name)] if child]
    if len(candidates)==1:return candidates[0]
    # Retired duplicated trees may remain until GC. Only the painted tree has real cached geometry.
    painted=[child for child in candidates if rect(child)['w']>0 and rect(child)['h']>0]
    assert len(painted)==1,(widget.get_path_name(),name,'Expected one painted live child',
                           [(child.get_path_name(),rect(child)) for child in candidates])
    return painted[0]


def contains(outer,inner,tolerance=2):
    return (inner['x']>=outer['x']-tolerance and inner['y']>=outer['y']-tolerance
            and inner['x']+inner['w']<=outer['x']+outer['w']+tolerance
            and inner['y']+inner['h']<=outer['y']+outer['h']+tolerance)


def end(reason,error=None):
    if S['done']: return
    S['done']=True
    unreal.unregister_slate_post_tick_callback(S['handle'])
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    with open('P:/FoA/Saved/EncounterCaptures/ui_layout_runtime.json','w') as f:
        json.dump(dict(result=reason,error=error,samples=S['rows']),f,indent=2)
    print('BATTLE UI LAYOUT',reason,error or '')


def tick(_dt):
    try:
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not world:return end('FAIL','PIE ended')
        now=time.monotonic()-S['start']
        if now>12:return end('FAIL','12 second cap awaiting held PlayerCommand')
        enc=unreal.GameplayStatics.get_actor_of_class(world,unreal.load_class(None,
            '/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C'))
        if not enc or not enc.get_editor_property('bActive') or str(enc.get_editor_property('BattleState'))!='PlayerCommand': return
        pc=unreal.GameplayStatics.get_player_controller(world,0)
        w=enc.get_editor_property('Widget')
        if S['phase']==0:
            S['phase']=1;S['at']=now+.7
        elif now>S['at']:
            enemies=w.get_editor_property('EnemyRows')
            visible=[i for i in range(enemies.get_children_count()) if enemies.get_child_at(i).is_visible()]
            labels={}
            bounds={}
            for name in ('Btn_Act0','Btn_Act1','Btn_Breathe','Btn_Mirror','Btn_Items','Btn_Flee','Btn_NextTarget'):
                button=live_child(w,name)
                label=live_child(button,'Txt_Label');hit_widget=live_child(button,'Btn_Hit')
                labels[name]=dict(label=str(button.get_editor_property('Label')),
                    size=label.get_font_size(),plain=button.get_editor_property('bPlainLabel'))
                if button.is_visible():
                    hit=rect(hit_widget);text=rect(label)
                    S['rows'].append(dict(measuring=name,button_path=button.get_path_name(),
                        hit_path=hit_widget.get_path_name(),text_path=label.get_path_name(),hit=hit,text=text))
                    assert hit['local_h']>=51.9 and hit['w']>0,(name,'short hit target',hit)
                    assert contains(hit,text),(name,'text outside hit target',hit,text)
                    focus=live_child(button,'Img_CommandFocus')
                    assert not focus.is_visible() or button.get_editor_property('bHovered'),(name,'inactive focus frame')
                    frame=rect(focus)
                    if focus.is_visible():assert contains(frame,text),(name,'text outside focus frame',frame,text)
                    bounds[name]=dict(hit=hit,text=text,focus=frame,focus_visible=focus.is_visible())
            for name,a in bounds.items():
                for other,b in bounds.items():
                    if name>=other:continue
                    aa,bb=a['hit'],b['hit']
                    overlap_x=min(aa['x']+aa['w'],bb['x']+bb['w'])-max(aa['x'],bb['x'])
                    overlap_y=min(aa['y']+aa['h'],bb['y']+bb['h'])-max(aa['y'],bb['y'])
                    assert overlap_x<=2 or overlap_y<=2,('overlapping hit targets',name,other,aa,bb)
            actual=tuple(pc.get_viewport_size())
            assert all(abs(a-b)<=2 for a,b in zip(actual,EXPECTED)),('Wrong actual viewport',EXPECTED,actual)
            assert len(visible)==1 and visible[0]==enc.get_editor_property('Target'),visible
            assert not w.get_editor_property('Txt_BattlePhase').is_visible()
            assert w.get_editor_property('CommandPanel').is_visible()
            assert all(x['plain'] and abs(x['size']-(28 if name.startswith('Btn_Act') else 26))<.01
                       for name,x in labels.items()),labels
            assert labels['Btn_Breathe']['label']=='Deep breath'
            S['rows'].append(dict(requested=SIZES[S['index']],actual=actual,visible_enemies=visible,labels=labels,bounds=bounds))
            folder='P:/FoA/Saved/EncounterCaptures/ui_layout';os.makedirs(folder,exist_ok=True)
            unreal.SystemLibrary.execute_console_command(world,f'Shot showui filename={folder}/command_{actual[0]}x{actual[1]}.png -nosuffix',pc)
            S['index']+=1;S['phase']=0
            if S['index']==len(SIZES):return end('PASS')
    except Exception as exc:end('FAIL',repr(exc))


S['handle']=unreal.register_slate_post_tick_callback(tick)
print('Battle UI layout proof armed; awaiting real PlayerCommand, 12 second cap')
