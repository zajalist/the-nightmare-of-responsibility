"""Use the encounter's truthful effect/blocked copy for recovery choices too."""
import json
from pathlib import Path
import redesign_battle_choices as b
assert not b.c('editor_get_state')['pie_running']
b.TOKEN=b.hc.lease_acquire(b.OWNER,['asset:'+b.WBP],ttl_s=30,wait_s=2)
try:
    for name in ('Breathe','Mirror'): b.variable('Txt_'+name+'Detail')
    b.props('ActBox',s={'fill':2.0}); b.props('CmdButtons',s={'fill':1.2})
    b.c('blueprint_compile',path=b.WBP)
    data=json.loads(Path('Saved/UIShots/battle_feedback_full.json').read_text())['RefreshCommands']
    g=b.Graph('RefreshCommands',data)
    for i,name in enumerate(('Breathe','Mirror')):
        if any(n['title']=='Get Txt_'+name+'Detail' for n in data['nodes']): continue
        move=g.node('Get '+name+'Move'); button=g.node('Get Btn_'+name)
        enabled=next(e['to_node'] for e in data['edges'] if e['from_node']==button and e['to_pin']=='self')
        detail=g.fn(b.ENC+':MoveDetail',1000+i*800,900)
        g.connect(g.node('Get Encounter'),detail,'Encounter','self'); g.connect(move,detail,name+'Move','Move')
        widget=g.get('Txt_'+name+'Detail',1000+i*800,1200)
        st=g.fn('/Script/UMG.TextBlock:SetText',1300+i*800,900)
        g.connect(widget,st,'Txt_'+name+'Detail','self'); g.connect(detail,st,'Detail','InText')
        tail=g.after(enabled,st); g.connect(st,tail)
    if g.ops: g.apply()
    result=b.c('blueprint_compile',path=b.WBP,save=True)
    assert result['error_count']==result['warning_count']==0,result
    Path('Saved/UIShots/battle_recovery_details.json').write_text(json.dumps(result,indent=2))
    print('Recovery effects and blocked remedies now use actual MoveDetail. Saved clean.')
finally: b.hc.release(b.OWNER,b.TOKEN)
