"""Native Slate screenshots with authored content; restore every preview edit.

This is a layout fixture, not a gameplay proof. No PIE or player save is touched.
"""
import json
import os
from pathlib import Path
import shutil
import sys
import time
import l2_ink_style as ink
import interview_data as data
import journey_data
from finalize_l2_graphs import call,checked_compile
import editor_lock


def run(kind):
    path=ink.INTERVIEW if kind in ('question','feedback','stress') else ink.JOURNEY if kind.startswith('journey') else {'drive':ink.DRIVE}[kind]
    owner='main-city-ui';os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner,FOA_CALLER=owner)
    editor_lock.acquire(owner,wait_s=5,ttl=120,areas=[path]);saved={}
    try:
        assert not call('editor_get_state')['pie_running']
        rows=call('ui_query',path=path,name_pattern='Txt_',include_properties=True)['matches']
        saved={row['name']:row['properties']['text'] for row in rows if 'text' in row.get('properties',{})}
        if kind=='question':
            row=data.CONTACTS[1]
            values=dict(Speaker=row['speaker'],Question=row['question'],Status='Employability 20',
                Evidence=data.NOTES[1],Hint='Up and Down choose. Enter or gamepad A confirms. You can also click an answer.',
                **{'Answer'+str(i):choice['text'] for i,choice in enumerate(row['choices'])})
        elif kind=='stress':
            row=data.SECTIONS[0]['followups'][0]
            values=dict(Speaker='Interviewer',Question=row['question'],Status='Employability 66     Composure 100',
                Evidence=data.NOTES[0],Hint='Up and Down choose. Enter or gamepad A confirms. You can also click an answer.',
                **{'Answer'+str(i):choice['text'] for i,choice in enumerate(row['choices'])})
        elif kind=='feedback':
            answers=[choice for section in data.SECTIONS for turn in (section,*section['followups']) for choice in turn['choices']]
            row=max(answers,key=lambda choice:len(choice['text'])+len(choice['reply']))
            values=dict(Speaker='Interviewer',Question='You: '+row['text']+'\n\n'+row['reply'],
                Status='Employability 93     Composure 100',Evidence='',Hint='Release, then press Enter or gamepad A. You can also click Continue.',
                Answer0='Continue.',Answer1='',Answer2='')
            for name,slot in [('ConversationEdge',dict(size=[16,352])),('ConversationPanel',dict(size=[24,336])),
                              ('SpeakerBack',dict(position=[44,-334])),('SpeakerTag',dict(position=[40,-344])),
                              ('Txt_Speaker',dict(position=[96,-350])),('Txt_Question',dict(position=[96,-154],size=[96,176])),
                              ('Btn_Answer0',dict(position=[56,-84],size=[92,56]))]:
                call('ui_set_widget_properties',widget_blueprint_path=path,widget_name=name,slot_props=slot)
            for name in ('Btn_Answer1','Btn_Answer2','EvidencePanel'):
                # Designer previews deliberately reveal collapsed widgets; opacity
                # mirrors the live Count=1 branch without drawing their frames.
                call('ui_set_widget_properties',widget_blueprint_path=path,widget_name=name,properties=dict(Visibility='Collapsed',RenderOpacity=0.))
        elif kind.startswith('journey'):
            if kind=='journey_intro':
                values=dict(Title='Queen Street',Body='Dad left the car.\n\nThere is a Career Center ahead.\n\nFirst, look at the C.V.',Hint='Enter or gamepad Y to inspect the C.V.',Progress='')
            elif kind=='journey_cv':
                values=dict(Title='My C.V.',Body='Experience\nI have no job experience.\n\nSkills\n\nAvailability',Hint='Enter or gamepad Y to get in the car',Progress='')
            elif kind=='journey_long':
                values=dict(Title='Career Center',Body=journey_data.SCENES[0]['dialogue'][1],Hint='Enter or gamepad Y to continue',Progress='Employability 20')
            else:
                values=dict(Title='Grocery supervisor',Body=data.CONTACTS[1]['task'],Hint='E or gamepad A to straighten the labels',Progress='Find a job     Employability 20')
            values['Body']=journey_data.compact_body(values['Body'])
        else:
            values=dict(Place='Queen Street',Composure='Composure 100',Employability='Find a job   Employability 20',Cue='Turn right at the next street')
        for name,value in values.items():
            call('ui_set_widget_properties',widget_blueprint_path=path,widget_name='Txt_'+name,properties=dict(Text=value))
        if path==ink.INTERVIEW:
            for i in range(3):call('ui_set_widget_properties',widget_blueprint_path=path,widget_name='AnswerPad'+str(i),
                properties=dict(BrushColor=ink.RED if i==0 else ink.WHITE,Background=ink.brush('T_L2InkTag' if i==0 else 'T_L2InkPanel')))
        checked_compile(path)
        # Give Slate a real frame after property changes/compile before creating
        # a render fixture; otherwise an invalidated tree can capture blank text.
        time.sleep(.3)
        out=Path('P:/FoA/Saved/Integration/city_ui');out.mkdir(parents=True,exist_ok=True)
        captures=[]
        for width,height in ((1280,720),(1920,1080)):
            name=f'l2_ink_{kind}_{width}_after.png'
            receipt=call('ui_render_widget_to_png',widget_blueprint_path=path,width=width,height=height,
                         out_path=str(time.time_ns())+'_'+name,inline_image=False)
            assert receipt['artifact_verified'] and receipt.get('coverage_percent',0)>0,receipt
            shutil.copy2(receipt['out_path'],out/name);captures.append(str(out/name))
        (out/('capture_'+kind+'.json')).write_text(json.dumps(dict(kind=kind,fixture=True,files=captures),indent=2))
        print(json.dumps(captures),flush=True)
    finally:
        try:
            for name,value in saved.items():
                call('ui_set_widget_properties',widget_blueprint_path=path,widget_name=name,properties=dict(Text=value))
            if path==ink.INTERVIEW:
                for row in ink.plans()[path]:
                    if row['name'] in ('ConversationEdge','ConversationPanel','SpeakerBack','SpeakerTag','Txt_Speaker','Txt_Question','Txt_Hint','Btn_Answer0'):
                        call('ui_set_widget_properties',widget_blueprint_path=path,widget_name=row['name'],slot_props=row['slot_props'])
                for name in ('Btn_Answer1','Btn_Answer2','EvidencePanel'):
                    call('ui_set_widget_properties',widget_blueprint_path=path,widget_name=name,
                         properties=dict(Visibility='HitTestInvisible' if name=='EvidencePanel' else 'Visible',RenderOpacity=1.))
            checked_compile(path)
            call('python_exec_file',path='P:/FoA/Tools/Unreal/ui/close_ui_editors.py',
                 env={'FOA_ASSETS':path},resources=['asset:'+path])
        finally:editor_lock.release(owner)


if __name__=='__main__':run(sys.argv[1])
