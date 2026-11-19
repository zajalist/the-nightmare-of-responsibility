"""Narrow encounter-only card geometry and CV icon selectors; no shared button edits."""
import json
import os
from pathlib import Path
import shutil
import sys
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/ui']
import battle_torn_cards as b
import editor_lock
from cv_data import MOVE_ICONS

CV_ICONS=MOVE_ICONS
OUT=Path('P:/FoA/Saved/Integration/cv_card_style')


def geometry_plan(nodes,edges):
    if any(n['title']=='Readable card label bounds' for n in nodes):return None
    entry=next(n['node_id'] for n in nodes if n['title']=='TornConfigure')
    tail=next(n['node_id'] for n in nodes if n['title'].replace(' ','')=='SetVisibility' and
              not any(e['from_node']==n['node_id'] and e['from_pin']=='then' for e in edges))
    batch=b.B(b.WBP,'TornConfigure');button=(entry,'Button')
    label=batch.get('Txt_Label',b.SB,button);ret=batch.get('Ret_Sand',b.SB,button)
    ret_slot=batch.fn('/Script/UMG.WidgetLayoutLibrary:SlotAsOverlaySlot',Widget=ret)
    ret_fill=batch.fn('/Script/UMG.OverlaySlot:SetVerticalAlignment',self=ret_slot,InVerticalAlignment='VAlign_Fill')
    label_slot=batch.fn('/Script/UMG.WidgetLayoutLibrary:SlotAsOverlaySlot',Widget=label)
    horizontal=batch.fn('/Script/UMG.OverlaySlot:SetHorizontalAlignment',self=label_slot,InHorizontalAlignment='HAlign_Fill')
    vertical=batch.fn('/Script/UMG.OverlaySlot:SetVerticalAlignment',self=label_slot,InVerticalAlignment='VAlign_Fill')
    padding=batch.fn('/Script/UMG.OverlaySlot:SetPadding',self=label_slot,InPadding='(Left=10,Top=0,Right=10,Bottom=4)')
    # AutoWrapText already uses the arranged width; fill alignment gives it the
    # full 202px card minus20px padding, rather than the menu's desired width.
    batch.chain(tail,ret_fill,horizontal,vertical,padding)
    batch.ops.append(dict(op='comment',title='Readable card label bounds',node_ids=list(batch.refs)))
    return batch


def icons_plan(nodes,edges):
    if any(n['title']=='Distinct CV action icons' for n in nodes):return None
    entry=next(n['node_id'] for n in nodes if n['title']=='RefreshBattleActionIcon')
    texture_cast=next(n['node_id'] for n in nodes if n['title']=='Cast To Texture2D')
    incoming=next(e for e in edges if e['to_node']==texture_cast and e['to_pin']=='Object')
    batch=b.B(b.WBP,'RefreshBattleActionIcon');texture=(incoming['from_node'],incoming['from_pin'])
    for move,icon in CV_ICONS.items():
        matches=batch.fn('/Script/Engine.KismetMathLibrary:EqualEqual_ObjectObject',A=(entry,'Move'),
                         B=f'/Game/FoA/Level2/CV/Data/DA_Move_{move}.DA_Move_{move}')
        texture=batch.fn('/Script/Engine.KismetMathLibrary:SelectObject',
                         A=f'/Game/FoA/Gameplay/Encounter/Icons/T_BattleGame_{icon}.T_BattleGame_{icon}',
                         B=texture,bSelectA=matches)
    batch.ops.append(dict(op='disconnect',node_id=texture_cast,pin_name='Object'))
    batch.link(texture,'ReturnValue',texture_cast,'Object')
    batch.ops.append(dict(op='comment',title='Distinct CV action icons',node_ids=list(batch.refs)))
    return batch


def run():
    owner='main-level2-cv-style';os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner,FOA_CALLER=owner)
    editor_lock.acquire(owner,wait_s=5,ttl=60,areas=[b.WBP])
    try:
        assert not b.c('editor_get_state')['pie_running']
        source=Path('P:/FoA/Content/FoA/Gameplay/Encounter/WBP_Encounter.uasset')
        backup=Path('P:/FoA/Saved/Backups/level-integration-20261111/CVCardStyle')/source.name
        if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
        for icon in CV_ICONS.values():
            assert Path('P:/FoA/Content/FoA/Gameplay/Encounter/Icons/T_BattleGame_'+icon+'.uasset').exists()
        receipts={}
        for graph,planner in (('TornConfigure',geometry_plan),('RefreshBattleActionIcon',icons_plan)):
            nodes,edges=b.graph(b.WBP,graph);batch=planner(nodes,edges)
            if batch:batch.run()
            result=b.c('blueprint_compile',path=b.WBP,save=True)
            assert result['error_count']==result['warning_count']==0,result
            after,connections=b.graph(b.WBP,graph)
            receipts[graph]=dict(nodes=len(after),edges=len(connections),compile=result,operations=len(batch.ops) if batch else 0)
        OUT.mkdir(parents=True,exist_ok=True);(OUT/'applied.json').write_text(json.dumps(receipts,indent=2))
        print(json.dumps(receipts),flush=True)
    finally:editor_lock.release(owner)


if __name__=='__main__':run()
