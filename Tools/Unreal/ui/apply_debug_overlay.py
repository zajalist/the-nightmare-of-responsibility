"""Scoped debug overlay authoring; refuses user PIE, compiles only through native Hayba."""
import os,sys,json
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h,ue_remote
D='/Game/FoA/UI/Game/WBP_Debug';F='/Game/FoA/UI/Framework/BP_FoAFrontEnd';B='/Game/FoA/Gameplay/BP_BeatDirector'
owner='clothing_search';os.environ['FOA_AGENT']=owner;os.environ['HAYBA_AGENT_ID']=owner
assert not h.call('editor_get_state')['data']['pie_running']
areas=['asset:'+p for p in (D,F,B)];token=h.lease_acquire(owner,areas,ttl_s=180,wait_s=3);os.environ['FOA_LEASE']=token

def call(name,**params):
    r=h.call(name,params,owner=owner,lease=token,timeout=45);assert r.get('ok'),r
    d=r.get('data',{});assert not d.get('failed_properties') and not d.get('error_count') and not d.get('num_errors'),d
    comp=d.get('compile',{});assert not comp.get('error_count') and not comp.get('num_errors') and comp.get('ok',True),d
    if 'compile' in name:print(name,json.dumps(d))
    return d
try:
    created=h.call('ui_create_widget',dict(path='/Game/FoA/UI/Game',name='WBP_Debug'),owner=owner,lease=token)
    assert created.get('ok') or 'exist' in str(created).lower(),created
    rows=[('Txt_Title','Playtest diagnostics       F9  Close',23),('Txt_Story','Story',18),('Txt_Interaction','Interaction',18),('Txt_Camera','Camera',18),('Txt_Locks','Locks',18),('Txt_Inventory','Inventory',18),('Txt_Battle','Battle',18),('Txt_Controls','F6  Next step in Levels 1 and 2\nSkipping uses separate debug progress.\nHold Space  Skip intro\nP  Phone     Hold Ctrl  Crouch     E  Interact',17)]
    if not call('ui_query',path=D,name_pattern='DebugFrame')['matches']:
        call('ui_build_tree',widget_blueprint_path=D,parent_widget_name='RootCanvas',tree={'class':'Border','name':'DebugFrame','properties':{'BrushColor':'(R=.006,G=.006,B=.006,A=.92)','Padding':'(Left=24,Top=20,Right=24,Bottom=20)','Visibility':'HitTestInvisible'},'slot_props':{'position':[48,145],'size':[660,640]},'children':[{'class':'VerticalBox','name':'DebugRows','children':[{'class':'TextBlock','name':n,'properties':{'Text':t},'slot_props':{'padding':[0,0,0,14]}} for n,t,z in rows]}]})
    for name,text,size in rows:
        call('ui_set_widget_properties',widget_blueprint_path=D,widget_name=name,properties={'Text':text,'AutoWrapText':False,'WrapTextAt':610.,'Font':{'FontObject':'/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI','TypefaceFontName':'Regular','Size':size},'ColorAndOpacity':'(SpecifiedColor=(R=.92,G=.92,B=.92,A=1))'})
        call('ui_set_variable',widget_blueprint_path=D,widget_name=name,is_variable=True)
    call('ui_set_widget_properties',widget_blueprint_path=D,widget_name='RootCanvas',properties={'Visibility':'HitTestInvisible'})
    call('ui_compile_widget',widget_blueprint_path=D)
    q=Path('P:/FoA/Saved/Integration/debug_overlay_compile_queue.jsonl');q.write_text('')
    for part in ('director','frontend'):
        q.write_text('')
        assert ue_remote.run_hayba('P:/FoA/Tools/Unreal/ui/author_debug_shortcuts.py',
            {'FOA_HAYBA_QUEUE':str(q),'FOA_DEBUG_PART':part},areas,owner,token)
        for row in map(json.loads,q.read_text().splitlines()):call(row['cmd'],**row['params'])
    call('blueprint_set_defaults',path=D,properties={'bIsFocusable':False})
    call('ui_save_widget',widget_blueprint_path=D)
    call('ui_query',path=D,flatten=True)
    print('Debug overlay saved; runtime proof pending')
finally:h.release(owner,token);os.environ.pop('FOA_LEASE',None)
