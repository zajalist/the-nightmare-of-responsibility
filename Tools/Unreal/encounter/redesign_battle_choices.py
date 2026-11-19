"""In-place native battle composition and truthful action cards. Never rebuilds widget objects."""
import json
from pathlib import Path
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc
WBP='/Game/FoA/Gameplay/Encounter/WBP_Encounter'
ENC='/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C'
FONT='/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
OWNER='ui_pacing_recovery'; TOKEN=None
def c(cmd, **p):
    r=hc.call(cmd,p,owner=OWNER,lease=TOKEN); assert r.get('ok'),r
    d=r.get('data',{}); assert d.get('ok',True) and not d.get('failed') and not d.get('failed_properties') and not d.get('unknown_slot_props'),d
    return d
def props(n,p=None,s=None):
    return c('ui_set_widget_properties',widget_blueprint_path=WBP,widget_name=n,**({'properties':p} if p else {}),**({'slot_props':s} if s else {}))
def text(n,t,size=22):
    return {'class':'TextBlock','name':n,'properties':{'Text':t,'Font':{'FontObject':FONT,'TypefaceFontName':'SemiBold','Size':size},'ColorAndOpacity':{'SpecifiedColor':[.92,.92,.92,1]},'AutoWrapText':True}}
def add(n,parent):
    if not c('ui_query',path=WBP,name_pattern=n['name']).get('matches'):
        c('ui_build_tree',widget_blueprint_path=WBP,parent_widget_name=parent,tree=n)
def move(n,parent,**slot):
    matches=c('ui_query',path=WBP,name_pattern=n).get('matches',[])
    if any(w['name']==n and w.get('parent')==parent for w in matches):
        if slot: props(n,s=slot)
        return
    c('ui_mutate_tree',operation='reparent',widget_blueprint_path=WBP,widget_name=n,new_parent_name=parent,slot_props=slot)
def variable(n): c('ui_set_variable',widget_blueprint_path=WBP,widget_name=n,is_variable=True)
def layout():
    props('CommandPanel',{'Padding':'(Left=26,Top=20,Right=26,Bottom=20)','Clipping':'ClipToBounds'},dict(anchors_min=[0,1],anchors_max=[1,1],alignment=[0,1],position=[48,-56],size=[48,350],auto_size=False))
    props('ActBox',s={'fill':2.0,'padding':[0,0,36,0]}); props('CmdButtons',s={'fill':1.2})
    props('Txt_Target',text('x','',30)['properties'],{'padding':[0,0,0,20]})
    props('BattleActRow',{'Visibility':'Collapsed'})
    add({'class':'HorizontalBox','name':'ActCards'},'ActBox'); variable('ActCards')
    for i in range(3):
        card='ActCard'+str(i); button='Btn_Act'+str(i)
        add({'class':'VerticalBox','name':card},'ActCards')
        props(card,s={'fill':1,'padding':[0,0,24 if i<2 else 0,0]})
        move(button,card,padding=[0,0,0,16])
        props(button,{'bPlainLabel':True,'LabelSize':30.0,'TextAlphaRest':1.0,'TextAlphaDisabled':.5,'Clipping':'ClipToBounds'})
        detail=text('Txt_Act'+str(i)+'Detail','',23); detail['slot_props']={'padding':[2,0,12,0]}
        add(detail,card); variable(detail['name'])
        props(detail['name'],{'WrapTextAt':430.0})
    # Secondary commands are quieter and have their effects directly below them.
    props('UtilityColumns',{'Visibility':'Collapsed'})
    add({'class':'VerticalBox','name':'RecoveryChoices'},'CmdButtons')
    for name,line in [('Breathe','Restore 15 Resolve and 5 Composure.'),('Mirror','Restore 20 Composure. Reveal intentions.'),('NextTarget','Switch freely. No turn spent.')]:
        move('BattleRow_'+name,'RecoveryChoices',padding=[0,0,0,3])
        props('Btn_'+name,{'LabelSize':25.0,'Clipping':'ClipToBounds'})
        detail=text('Txt_'+name+'Detail',line,20); detail['slot_props']={'padding':[40,0,0,12]}
        add(detail,'RecoveryChoices')
    props('BattleRow_Items',{'Visibility':'Collapsed'}); props('Btn_Items',{'Visibility':'Collapsed','bIsEnabled':False})
    props('BattleRow_Flee',{'Visibility':'Collapsed'}); props('Btn_Flee',{'Visibility':'Collapsed','bIsEnabled':False})
    # Full-width compact roster preserves every garment's live public status.
    props('EnemyPanel',{'Padding':'(Left=20,Top=16,Right=20,Bottom=16)'},dict(anchors_min=[0,0],anchors_max=[1,0],alignment=[0,0],position=[48,172],size=[48,235],auto_size=False))
    props('EnemyRows',{'Visibility':'Collapsed'})
    add({'class':'HorizontalBox','name':'GarmentRoster'},'BattleEnemyHost'); variable('GarmentRoster')
    for i in range(5):
        move('Row'+str(i),'GarmentRoster',fill=1,padding=[0,0,18,0])
        props('Txt_Enemy'+str(i),text('x','',24)['properties']|{'WrapTextAt':270.0})
        props('Pips'+str(i),{'Visibility':'Collapsed'})
        props('Txt_Intent'+str(i),text('x','',20)['properties']|{'WrapTextAt':270.0},dict(padding=[0,8,0,0]))
        t=text('Txt_Progress'+str(i),'0 of 1',21); t['slot_props']={'padding':[0,8,0,0]}; add(t,'Row'+str(i)); variable(t['name'])
    props('SelfBox',s=dict(anchors_min=[1,0],anchors_max=[1,0],alignment=[1,0],position=[-48,20],size=[400,110],auto_size=False))
    props('Box_Resolve',s={'padding':[0,10,0,0]})
    move('Txt_Statuses','RootCanvas',anchors_min=[0,0],anchors_max=[0,0],alignment=[0,0],position=[48,88],size=[1050,48],auto_size=False)
    props('Txt_Statuses',{'Visibility':'HitTestInvisible','WrapTextAt':1050.0})
    for stat in ('Composure','Resolve'):
        props('Txt_'+stat+'Label',text('x',stat,23)['properties']); props('Txt_'+stat,text('x','100',23)['properties'])
        props('Size_Bar_'+stat,{'WidthOverride':400.0,'bOverride_WidthOverride':True})
    props('Txt_BattleHelp',text('x','Your turn',30)['properties'],dict(anchors_min=[0,0],anchors_max=[0,0],alignment=[0,0],position=[48,34],size=[1050,52],auto_size=False))
    add(text('Txt_BattleControls','Arrows choose. Enter confirms. Every round costs 4 Composure.',21),'RootCanvas')
    props('Txt_BattleControls',s=dict(anchors_min=[0,1],anchors_max=[0,1],alignment=[0,1],position=[56,-16],size=[1450,32],auto_size=False))
    props('LogPanel',{'Padding':'(Left=24,Top=10,Right=24,Bottom=10)'},dict(anchors_min=[.5,1],anchors_max=[.5,1],alignment=[.5,1],position=[0,-425],size=[1450,72],auto_size=True))  # UI's plate fix (B3): the plate fits its text
    props('Txt_Narration',{'WrapTextAt':1390.0})

class Graph:
    def __init__(self,name,data): self.name=name; self.data=data; self.ops=[]
    def node(self,title):
        a=[n['node_id'] for n in self.data['nodes'] if n['title']==title]; assert len(a)==1,(title,a); return a[0]
    def add(self,kind,**kw):
        d=c('blueprint_add_node',path=WBP,graph_name=self.name,node_type=kind,**kw)
        return d['node_id'],d.get('pins',[])
    def fn(self,name,x=6000,y=500): return self.add('call_function',function_name=name,x=x,y=y)[0]
    def get(self,name,x=6000,y=800): return self.add('variable_get',variable_name=name,x=x,y=y)[0]
    def connect(self,a,b,ap='then',bp='execute'): self.ops.append(dict(op='connect',from_node=a,from_pin=ap,to_node=b,to_pin=bp))
    def disconnect(self,n,p): self.ops.append(dict(op='disconnect',node_id=n,pin_name=p))
    def set(self,n,p,v):
        if v != '': self.ops.append(dict(op='set_pin',node_id=n,pin_name=p,value=str(v)))
    def replace_get(self,old,new):
        n=self.node('Get '+old); m=self.get(new)
        for e in self.data['edges']:
            if e['from_node']==n:
                self.disconnect(e['to_node'],e['to_pin']); self.connect(m,e['to_node'],new,e['to_pin'])
    def after(self,n,new):
        edges=[e for e in self.data['edges'] if e['from_node']==n and e['from_pin']=='then']; assert len(edges)==1,edges
        self.disconnect(n,'then'); self.connect(n,new); return edges[0]['to_node']
    def cast(self,cls,x=6000,y=0):
        n,pins=self.add('cast',class_path='/Script/UMG.'+cls,x=x,y=y)
        # Native dynamic cast result names omit the palette's display-space aliases.
        out=next(p.get('name',p.get('pin_name')) for p in pins if p.get('name',p.get('pin_name','')).startswith('As'))
        return n,out
    def apply(self):
        self.ops.append(dict(op='fit_comments',title_only=True))
        return c('blueprint_graph_batch',path=WBP,graph_name=self.name,ops=self.ops)

def actions(data):
    g=Graph('RefreshAct',data)
    if any(n['title']=='Get ActCards' for n in data['nodes']): return
    g.replace_get('ActButtons','ActCards')
    child=g.node('GetChildAt'); cast=g.node('Cast To WBP_SandButton')
    card,cardpin=g.cast('PanelWidget',500,-300)
    bchild=g.fn('/Script/UMG.PanelWidget:GetChildAt',700,300)
    g.connect(child,card,'ReturnValue','Object'); g.connect(card,bchild,cardpin,'self')
    g.disconnect(cast,'Object'); g.connect(bchild,cast,'ReturnValue','Object')
    incoming=next(e for e in data['edges'] if e['to_node']==cast and e['to_pin']=='execute')
    g.disconnect(cast,'execute'); g.connect(incoming['from_node'],card,incoming['from_pin']); g.connect(card,cast)
    for n in data['nodes']:
        if n['title']=='SetVisibility':
            g.disconnect(n['node_id'],'self'); g.connect(child,n['node_id'],'ReturnValue','self')
    dchild=g.fn('/Script/UMG.PanelWidget:GetChildAt',2700,600); g.set(dchild,'Index',1); g.connect(card,dchild,cardpin,'self')
    dc,dcp=g.cast('TextBlock',2800,-120); g.connect(dchild,dc,'ReturnValue','Object')
    detail=g.fn(ENC+':MoveDetail',2750,350); g.connect(g.node('Get Encounter'),detail,'Encounter','self'); g.connect(g.node('Get'),detail,'Item','Move')
    st=g.fn('/Script/UMG.TextBlock:SetText',3100,-120); g.connect(dc,st,dcp,'self'); g.connect(detail,st,'Detail','InText')
    tail=g.after(g.node('SetIsEnabled'),dc); g.connect(dc,st); g.connect(st,tail)
    return g.apply()

def roster(data):
    g=Graph('RefreshRow',data)
    if any(n['title']=='Get GarmentRoster' for n in data['nodes']):
        fmt=g.node('Format Text')
        if any(e['from_node']==fmt for e in data['edges']): return
        assert next(p['default'] for n in data['nodes'] if n['node_id']==fmt for p in n['pins'] if p['name']=='Format')=='{Done} of {Total}'
        child=next(n['node_id'] for n in data['nodes'] if n['title']=='GetChildAt' and any(p['name']=='Index' and p['default']=='3' for p in n['pins']))
        cast=next(e['to_node'] for e in data['edges'] if e['from_node']==child and e['to_pin']=='Object')
        cp=next(p['name'] for n in data['nodes'] if n['node_id']==cast for p in n['pins'] if p['name'].startswith('As'))
        return finish_roster(g,data,fmt,cast,cp)
    g.replace_get('EnemyRows','GarmentRoster')
    gate=g.node('AND Boolean')
    real=next(e for e in data['edges'] if e['to_node']==gate and e['to_pin']=='B')
    out=next(e for e in data['edges'] if e['from_node']==gate)
    g.disconnect(out['to_node'],out['to_pin']); g.connect(real['from_node'],out['to_node'],real['from_pin'],out['to_pin'])
    rb=g.node('Cast To VerticalBox'); pin=next(p['name'] for n in data['nodes'] if n['node_id']==rb for p in n['pins'] if p['name'].startswith('As'))
    child=g.fn('/Script/UMG.PanelWidget:GetChildAt',4900,400); g.connect(rb,child,pin,'self'); g.set(child,'Index',3)
    cast,cp=g.cast('TextBlock',5100,-120); g.connect(child,cast,'ReturnValue','Object')
    fmt,_=g.add('format_text',x=5100,y=600); g.set(fmt,'Format','{Done} of {Total}')
    # Format pin reconstruction occurs before its argument connections.
    g.apply(); g.ops=[]
    return finish_roster(g,data,fmt,cast,cp)

def finish_roster(g,data,fmt,cast,cp):
    g.connect(g.node('Get Progress'),fmt,'Progress','Done'); g.connect(g.node('Get Resistance'),fmt,'Resistance','Total')
    st=g.fn('/Script/UMG.TextBlock:SetText',5400,-120); g.connect(cast,st,cp,'self'); g.connect(fmt,st,'Result','InText')
    line=g.node('StatusLine'); dest=next(e['to_node'] for e in data['edges'] if e['from_node']==line and e['to_pin']=='InText')
    tail=g.after(dest,cast); g.connect(cast,st); g.connect(st,tail)
    return g.apply()

def presentation(data,commands):
    g=Graph('RefreshBattlePresentation',data)
    for n in data['nodes']:
        for p in n['pins']:
            if p['direction']=='input' and p['default']=='Your turn. Arrows or D-pad choose; Enter or A confirms.': g.set(n['node_id'],p['name'],'Your turn. Choose your next move.')
            if p['direction']=='input' and p['default']=='Find Armhole strengthens Button Up.': g.set(n['node_id'],p['name'],'Find the armhole for easier timing, then button up.')
        if n['title']=='Get Btn_Items':
            for e in data['edges']:
                if e['from_node']==n['node_id'] and next(nn['title'] for nn in data['nodes'] if nn['node_id']==e['to_node'])=='GetIsEnabled':
                    g.disconnect(e['to_node'],'self'); replacement=g.get('Btn_NextTarget'); g.connect(replacement,e['to_node'],'Btn_NextTarget','self')
        # Keep target name supplied by RefreshCommands instead of overwriting it with generic Act.
        if n['title']=='SetText (Text)' and any(p['name']=='InText' and (p['default']=='Act' or p['default'].endswith(', "Act")')) for p in n['pins']):
            incoming=[e for e in data['edges'] if e['to_node']==n['node_id'] and e['to_pin']=='execute']
            if not incoming: continue
            inc=incoming[0]
            out=next(e for e in data['edges'] if e['from_node']==n['node_id'] and e['from_pin']=='then')
            g.disconnect(n['node_id'],'execute'); g.disconnect(n['node_id'],'then'); g.connect(inc['from_node'],out['to_node'],inc['from_pin'],out['to_pin'])
    # The last focus fallback must focus Change target, not hidden Items.
    for n in data['nodes']:
        if n['title']=='Get Btn_Items':
            for e in data['edges']:
                if e['from_node']==n['node_id'] and next(nn['title'] for nn in data['nodes'] if nn['node_id']==e['to_node'])=='FocusButton':
                    new=g.get('Btn_NextTarget'); g.disconnect(e['to_node'],'self'); g.connect(new,e['to_node'],'Btn_NextTarget','self')
    g.apply()
    g=Graph('RefreshCommands',commands)
    for name in ('Btn_Items','Btn_Flee'):
        node=g.node('Get '+name)
        dest=next(e['to_node'] for e in commands['edges'] if e['from_node']==node)
        g.disconnect(dest,'bInIsEnabled'); g.set(dest,'bInIsEnabled','false')
    g.apply()

def main():
    global TOKEN
    assert not c('editor_get_state')['pie_running']
    data=json.loads(Path('Saved/UIShots/battle_feedback_full.json').read_text())
    TOKEN=hc.lease_acquire(OWNER,['asset:'+WBP],ttl_s=60,wait_s=5)
    try:
        if '--finish' not in sys.argv: layout(); c('blueprint_compile',path=WBP)
        receipt={'actions':actions(data['RefreshAct']),'roster':roster(data['RefreshRow'])}
        presentation(data['RefreshBattlePresentation'],data['RefreshCommands'])
        receipt['compile']=c('blueprint_compile',path=WBP,save=True)
        Path('Saved/UIShots/battle_choice_redesign.json').write_text(json.dumps(receipt,indent=2))
        assert receipt['compile']['error_count']==receipt['compile']['warning_count']==0,receipt['compile']
        print('Battle action cards, five-garment roster and visible turn hierarchy saved. Runtime proof pending.')
    finally: hc.release(OWNER,TOKEN)
if __name__=='__main__': main()
