"""Refine actual 960px battle capture: secondary clipping, roster spacing and selected label."""
import json
from pathlib import Path
import redesign_battle_choices as b

def apply():
    assert not b.c('editor_get_state')['pie_running']
    b.TOKEN=b.hc.lease_acquire(b.OWNER,['asset:'+b.WBP],ttl_s=45,wait_s=2)
    try:
        b.props('CommandPanel',s={'size':[48,350]})
        b.props('LogPanel',s={'position':[0,-425]})
        b.props('EnemyPanel',s={'position':[48,172],'size':[48,235]})
        b.props('SelfBox',s={'position':[-48,20]})
        b.props('Txt_NextTargetDetail',{'Text':'Switch freely. No turn spent.'})
        data=json.loads(Path('Saved/UIShots/battle_feedback_full.json').read_text())['RefreshRow']
        g=b.Graph('RefreshRow',data)
        if not any(n['title']=='Get GarmentId' for n in data['nodes']):
            kind,_=g.add('variable_get',variable_name='GarmentId',class_path='/Game/FoA/Gameplay/Encounter/PDA_Opponent.PDA_Opponent_C',x=5300,y=1000)
            g.connect(g.node('Get Data'),kind,'Data','self')
            same=g.fn('/Script/Engine.KismetMathLibrary:EqualEqual_NameName',5500,1000); g.connect(kind,same,'GarmentId','A'); g.set(same,'B','Shirt')
            unit=g.fn('/Script/Engine.KismetMathLibrary:SelectString',5700,1000); g.connect(same,unit,'ReturnValue','bPickA'); g.set(unit,'A','Buttons '); g.set(unit,'B','Progress ')
            count=g.fn('/Script/Engine.KismetTextLibrary:Conv_TextToString',5500,800); g.connect(g.node('Format Text'),count,'Result','InText')
            join=g.fn('/Script/Engine.KismetStringLibrary:Concat_StrStr',6000,800); g.connect(unit,join,'ReturnValue','A'); g.connect(count,join,'ReturnValue','B')
            txt=g.fn('/Script/Engine.KismetTextLibrary:Conv_StringToText',6250,800); g.connect(join,txt,'ReturnValue','InString')
            dest=next(e['to_node'] for e in data['edges'] if e['from_node']==g.node('Format Text'))
            g.disconnect(dest,'InText'); g.connect(txt,dest,'ReturnValue','InText')
            # Selected garment has an explicit textual cue, not an opacity-only distinction.
            name=g.node('Get DisplayName')
            namedest=next(e['to_node'] for e in data['edges'] if e['from_node']==name and e['to_pin']=='InText')
            focus=next(n['node_id'] for n in data['nodes'] if n['title'] in ('SelectFloat','Select Float'))
            eq=next(e for e in data['edges'] if e['to_node']==focus and e['to_pin']=='bPickA')
            prefix=g.fn('/Script/Engine.KismetMathLibrary:SelectString',2800,1100); g.set(prefix,'A','Selected: '); g.set(prefix,'B',''); g.connect(eq['from_node'],prefix,eq['from_pin'],'bPickA')
            plain=g.fn('/Script/Engine.KismetTextLibrary:Conv_TextToString',2800,900); g.connect(name,plain,'DisplayName','InText')
            labelled=g.fn('/Script/Engine.KismetStringLibrary:Concat_StrStr',3100,900); g.connect(prefix,labelled,'ReturnValue','A'); g.connect(plain,labelled,'ReturnValue','B')
            final=g.fn('/Script/Engine.KismetTextLibrary:Conv_StringToText',3400,900); g.connect(labelled,final,'ReturnValue','InString')
            g.disconnect(namedest,'InText'); g.connect(final,namedest,'ReturnValue','InText')
            g.apply()
        else:
            prefix=next(n['node_id'] for n in data['nodes'] if n['title']=='SelectString' and any(p['name']=='A' and p['default']=='Selected: ' for p in n['pins']))
            if not any(e['from_node']==prefix for e in data['edges']):
                name=g.node('Get DisplayName')
                namedest=next(e['to_node'] for e in data['edges'] if e['from_node']==name and e['to_pin']=='InText')
                focus=next(n['node_id'] for n in data['nodes'] if n['title'] in ('SelectFloat','Select Float'))
                eq=next(e for e in data['edges'] if e['to_node']==focus and e['to_pin']=='bPickA')
                plain=[n['node_id'] for n in data['nodes'] if n['title']=='To String (Text)'][-1]
                labelled=[n['node_id'] for n in data['nodes'] if n['title']=='Append'][-1]
                final=[n['node_id'] for n in data['nodes'] if n['title']=='To Text (String)'][-1]
                g.connect(eq['from_node'],prefix,eq['from_pin'],'bPickA'); g.connect(name,plain,'DisplayName','InText')
                g.connect(prefix,labelled,'ReturnValue','A'); g.connect(plain,labelled,'ReturnValue','B'); g.connect(labelled,final,'ReturnValue','InString')
                g.disconnect(namedest,'InText'); g.connect(final,namedest,'ReturnValue','InText'); g.apply()
        result=b.c('blueprint_compile',path=b.WBP,save=True)
        assert result['error_count']==result['warning_count']==0,result
        Path('Saved/UIShots/battle_choice_readability.json').write_text(json.dumps(result,indent=2))
        print('Battle panel clearance, selected garment and named progress saved',result)
    finally: b.hc.release(b.OWNER,b.TOKEN)
if __name__=='__main__': apply()
