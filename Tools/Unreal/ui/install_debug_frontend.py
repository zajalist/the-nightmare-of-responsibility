"""Idempotent F9 lifecycle patch, also called by the canonical frontend builder."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
D='/Game/FoA/UI/Game/WBP_Debug';F='/Game/FoA/UI/Framework/BP_FoAFrontEnd'
C=lambda p:p+'.'+p.rsplit('/',1)[1]+'_C'
K='/Script/Engine.KismetSystemLibrary:';UW='/Script/UMG.UserWidget:'
def fn(path,name):
    g=Graph.function(path,name);return g,entry_node(g)
# Frontend keeps one nonfocusable widget, independent of phone or menu references.
ensure_vars(F,[('DebugPanel',ptype(unreal.UserWidget),'','Debug',False)])
for name in ('ToggleDebugPanel','CloseDebugPanel'):Graph.function(F,name)
g,e=fn(F,'CloseDebugPanel');ref=g.get('DebugPanel',0,200);v=g.call(K+'IsValid',250,200);g.link(ref,'DebugPanel',v,'Object');b=g.branch(500,0);g.link(v,'ReturnValue',b,'Condition');rm=g.call('/Script/UMG.Widget:RemoveFromParent',750,0);g.link(ref,'DebugPanel',rm,'self');clear=g.set('DebugPanel',1000,0);g.exec_chain(e,b,rm,clear);g.comment('Close diagnostics safely','',g.ed.list_all_nodes())
g,e=fn(F,'ToggleDebugPanel');ref=g.get('DebugPanel',0,200);v=g.call(K+'IsValid',250,200);g.link(ref,'DebugPanel',v,'Object');b=g.branch(500,0);g.link(v,'ReturnValue',b,'Condition');g.exec_chain(e,b)
close=g.call(C(F)+':CloseDebugPanel',800,-150);g.link(b,'True',close,'execute')
cw=g.node('UserInterface|CreateWidget',800,150);g.default(cw,'Class',C(D));pc=g.get('PC',500,400);g.link(pc,'PC',cw,'OwningPlayer');g.link(b,'False',cw,'execute')
s=g.set('DebugPanel',1100,150);g.link(cw,'ReturnValue',s,'DebugPanel');add=g.call(UW+'AddToViewport',1400,150,ZOrder=1000);g.link(s,'DebugPanel',add,'self');g.exec_chain(cw,s,add);g.comment('Toggle read only diagnostics','',g.ed.list_all_nodes())
# Add only the new F9 event; never clear the shared event graph.
g=Graph(F);existing=[n for n in g.ed.list_all_nodes() if n.get_class().get_name()=='K2Node_InputKey' and str(BEL.get_node_title(n))=='F9']
if not existing:
    names=[n for n in g.ed.list_available_nodes([]) if n.startswith('Input|') and n.rsplit('|',1)[-1]=='F9'];assert names
    key=g.node(names[0],0,2500);key.set_editor_property('consume_input',True);key.set_editor_property('execute_when_paused',True)
    toggle=g.call(C(F)+':ToggleDebugPanel',350,2500);g.link(key,'Pressed',toggle,'execute');g.comment('Inspect without changing state','',[key,toggle])
# Clean owned overlay at menu/gameplay transitions, preserving every existing outgoing call.
for name in ('EnterGameplay','ShowScreen','ReturnToTitle'):
    g=Graph(F,name);e=entry_node(g);pin=g.pin(e,'then','out');dest=list(PIN.list_connected_pins(pin))
    if any('CloseDebugPanel' in str(BEL.get_node_title(PIN.get_owning_node(p))).replace(' ','') for p in dest):continue
    n=g.call(C(F)+':CloseDebugPanel',-350,0)
    PIN.break_pin_links(pin)
    for p in dest:assert PIN.try_create_connection(g.pin(n,'then','out'),p)
    g.exec_chain(e,n);g.comment('Clear transition diagnostics','',[n])

exec(open('P:/FoA/Tools/Unreal/ui/install_debug_shortcuts.py', encoding='utf-8').read())
compile_save(F)
