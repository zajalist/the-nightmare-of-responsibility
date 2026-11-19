"""One in-place L2 ink treatment. Offline plans/assets; native steps need a grant.

The two small procedural masks are reused by drive, tasks and conversation.
All body text remains horizontal. Shared phone changes target L2-only children.
"""
import os
from pathlib import Path
import sys
sys.path[:0]=[str(Path(__file__).parent),'P:/FoA/Tools/Unreal']
from build_drive import call, HUD as DRIVE
from journey_data import HUD as JOURNEY
from interview_data import WIDGET as INTERVIEW

ROOT='/Game/FoA/Level2/UI'
PHONE='/Game/FoA/UI/Game/WBP_Phone'
SOURCE=Path('P:/FoA/Tools/Textures/level2')
WHITE=[1.,1.,1.,1.]
BLACK=[0.,0.,0.,1.]
RED=[.62,0.,0.,1.]
FONT='/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI'
DISPLAY='/Game/FoA/UI/Fonts/F_FoA_Display.F_FoA_Display'


def canvas(x,y,w,h,bottom=False,stretch=False,z=1):
    return dict(anchors_min=[0,int(bottom)],anchors_max=[int(stretch),int(bottom)],
        alignment=[0,int(bottom)],position=[x,y],size=[w,h],z_order=z,auto_size=False)


def brush(name):
    return f'(ResourceObject=Texture2D\'{ROOT}/{name}.{name}\',DrawAs=Box,ImageSize=(X=512,Y=256),Margin=(Left=.08,Top=.08,Right=.08,Bottom=.08),TintColor=(SpecifiedColor=(R=1,G=1,B=1,A=1)))'


def status_icon(name,texture,x,y,size):
    path=f'/Game/FoA/Gameplay/Encounter/Icons/{texture}.{texture}'
    return dict(name=name,**{'class':'Image'},slot_props=canvas(x,y,size,size),
                properties=dict(Brush=f"(ResourceObject=Texture2D'{path}',DrawAs=Image,ImageSize=(X={size},Y={size}))",
                                Visibility='HitTestInvisible'))


def text(size,display=False,black=False):
    return dict(Font=dict(FontObject=DISPLAY if display else FONT,
        TypefaceFontName='ExtraBold' if display else 'SemiBold',Size=size),
        ColorAndOpacity=dict(SpecifiedColor=BLACK if black else WHITE),
        AutoWrapText=True,ShadowOffset=dict(X=0,Y=0),ShadowColorAndOpacity=[0,0,0,0],
        Visibility='HitTestInvisible')


def tilt(angle):
    return dict(RenderTransform=dict(Translation=dict(X=0,Y=0),Scale=dict(X=1,Y=1),
                                     Shear=dict(X=0,Y=0),Angle=angle),
                RenderTransformPivot=dict(X=.5,Y=.5))


def plate(name,slot,tag=False,color=None,angle=0):
    return dict(name=name,**{'class':'Border'},slot_props=slot,properties=dict(
        Background=brush('T_L2InkTag' if tag else 'T_L2InkPanel'),BrushColor=color or WHITE,
        Visibility='HitTestInvisible',**tilt(angle)))


def plans():
    # Stretched Canvas slots use size.x as the right margin. No 1920-only width.
    dialogue=[plate('ConversationEdge',canvas(16,-18,16,392,True,True,-1),True,angle=-.6),
        plate('ConversationPanel',canvas(24,-26,24,376,True,True,0),True,BLACK,-.6),
        plate('SpeakerBack',canvas(44,-374,672,88,True,False,1),True,BLACK,-4),
        plate('SpeakerTag',canvas(40,-384,656,76,True,False,2),True,angle=-4),
        plate('EvidencePanel',dict(canvas(-32,24,400,200),anchors_min=[1,0],anchors_max=[1,0],alignment=[1,0])),
        dict(name='Txt_Speaker',slot_props=canvas(96,-390,544,84,True,False,3),properties=dict(text(44,True,True),**tilt(-4))),
        dict(name='Txt_Question',slot_props=canvas(96,-300,96,72,True,True,3),properties=text(24)),
        dict(name='Txt_Status',slot_props=canvas(64,35,650,44),properties=text(28,True)),
        dict(name='Txt_Evidence',slot_props=dict(canvas(-72,44,304,160,False,False,2),anchors_min=[1,0],anchors_max=[1,0],alignment=[1,0]),properties=text(22)),
        dict(name='Txt_Hint',slot_props=canvas(96,-40,96,32,True,True,3),properties=text(22))]
    dialogue.append(plate('StatusPanel',canvas(24,24,730,64,False,False,0)))
    for i,y in enumerate((-226,-154,-82)):
        dialogue.extend([dict(name='Btn_Answer'+str(i),slot_props=canvas(56+i*24,y,92-i*24,64,True,True,3),
            properties=dict(BackgroundColor=WHITE)),
            dict(name='AnswerPad'+str(i),slot_props=dict(horizontal_alignment='Fill',vertical_alignment='Fill'),
                 # Slate box corners use the texture's 1024px actual size,
                 # not the brush's desired ImageSize. Keep text past x39.
                 properties=dict(Padding=[60,10,52,10],Background=brush('T_L2InkPanel'))),
            dict(name='Txt_Answer'+str(i),slot_props=dict(horizontal_alignment='Fill',vertical_alignment='Center'),properties=text(24))])
    journey=[plate('TaskFrame',canvas(16,-18,800,408,True,False,-1),True,angle=.8),
        plate('Page',canvas(24,-26,784,392,True,False,0),True,BLACK,.8),
        plate('TaskBack',canvas(46,-366,720,88,True,False,1),True,BLACK,-4),
        plate('TaskTag',canvas(40,-378,704,76,True,False,2),True,angle=-4),
        dict(name='Txt_Title',slot_props=canvas(94,-386,596,84,True,False,3),properties=dict(text(44,True,True),**tilt(-4))),
        dict(name='Txt_Progress',slot_props=canvas(76,-326,660,32,True),properties=text(23,True)),
        dict(name='Txt_Body',slot_props=canvas(76,-106,662,204,True),properties=dict(text(27),LineHeightPercentage=.75)),
        dict(name='Txt_Hint',slot_props=canvas(76,-42,662,54,True),properties=text(23)),
        dict(name='Bar_L2Employability',slot_props=canvas(76,-306,660,8,True),properties=dict(FillColorAndOpacity=RED))]
    drive=[plate('DriveFrame',canvas(16,42,570,274,False,False,-1),True,angle=-1.2),
        plate('Brd_DriveStatus',canvas(24,50,554,258,False,False,0),True,BLACK,-1.2),
        plate('DrivePlaceBack',canvas(40,36,550,88,False,False,1),True,BLACK,-4),
        plate('DrivePlaceTag',canvas(32,24,536,80,False,False,2),True,angle=-4),
        plate('Brd_DriveControls',dict(canvas(0,-24,1080,72,True,False,0),anchors_min=[.5,1],anchors_max=[.5,1],alignment=[.5,1])),
        dict(name='Txt_Place',slot_props=canvas(84,18,440,76,False,False,3),properties=dict(text(44,True,True),**tilt(-4))),
        status_icon('Icon_Composure','T_BattleGame_Composure',76,123,30),
        status_icon('Icon_Employability','T_Battle_Items',76,169,27),
        dict(name='Txt_Composure',slot_props=canvas(120,120,406,44),properties=text(32,True)),
        dict(name='Txt_Employability',slot_props=canvas(120,168,406,32),properties=text(23)),
        dict(name='Bar_L2Employability',slot_props=canvas(76,204,450,10),properties=dict(FillColorAndOpacity=RED)),
        dict(name='Txt_Cue',slot_props=canvas(76,230,450,64),properties=text(29,True)),
        dict(name='Txt_Controls',slot_props=dict(canvas(0,-41,1010,38,True),anchors_min=[.5,1],anchors_max=[.5,1],alignment=[.5,1]),
             properties=dict(text(24),Text='W drive    S brake / reverse    A D steer    Q look back    Space brace    C C.V.'))]
    phone=[dict(name='L2CVBlock',slot_props=dict(padding=[0,0,0,0])),
        dict(name='Txt_L2Employability',properties=text(28,True)),
        dict(name='Size_L2Employability',properties=dict(HeightOverride=9.),slot_props=dict(padding=[0,4,0,6])),
        dict(name='Bar_L2Employability',properties=dict(FillColorAndOpacity=RED))]
    phone += [dict(name='Txt_L2CV'+str(i),properties=text(27),slot_props=dict(padding=[0,0,0,4])) for i in range(3)]
    return {INTERVIEW:dialogue,JOURNEY:journey,DRIVE:drive,PHONE:phone}


def assets():
    from PIL import Image,ImageDraw
    SOURCE.mkdir(parents=True,exist_ok=True)
    for name,tag in (('T_L2InkPanel',False),('T_L2InkTag',True)):
        im=Image.new('RGBA',(4096,2048));draw=ImageDraw.Draw(im)
        points=lambda values:[(4*x,4*y) for x,y in values]
        draw.polygon(points([(34,8),(1008,0),(980,460),(968,454),(990,500),(0,512)]),fill='white')
        if not tag:
            draw.polygon(points([(39,13),(1003,5),(975,455),(960,449),(978,495),(5,507)]),fill=(0,0,0,255))
        im.resize((1024,512),Image.Resampling.LANCZOS).save(SOURCE/(name+'.png'))
    return [str(p) for p in SOURCE.glob('T_L2Ink*.png')]


def import_assets():
    import shutil
    staging=Path(os.environ['TEMP'])/'hayba-asset-connectors'/'level2-ink'/'textures'
    staging.mkdir(parents=True,exist_ok=True)
    for source in assets():
        path=Path(source);target=staging/path.name;shutil.copy2(path,target)
        if not Path('P:/FoA/Content/FoA/Level2/UI',path.stem+'.uasset').exists():
            call('asset_import',source_file=str(target),destination_path=ROOT,asset_type='texture')
        call('texture_set_settings',path=ROOT+'/'+path.stem,properties=dict(lod_group='UI',
            compression_settings='EditorIcon',mip_gen_settings='NoMipmaps',never_stream=True,srgb=True))
        call('asset_save',asset_paths=[ROOT+'/'+path.stem])


def apply(path):
    # 2026-11-17 coordinator: the ui lane owns the journey card's and the interview's look (no ink plates there now)
    assert path not in (INTERVIEW,JOURNEY),'look owned by the ui lane: Tools/Unreal/ui/textfx/l2_look.py'
    call('python_exec_file',path='P:/FoA/Tools/Unreal/ui/close_ui_editors.py',
         env={'FOA_ASSETS':path},resources=['asset:'+path])
    for row in plans()[path]:
        name=row['name'];found=call('ui_query',path=path,name_pattern=name).get('matches',[])
        if not any(w['name']==name for w in found):
            assert row.get('class') in ('Border','Image'),('Build existing widgets first',path,name)
            call('ui_build_tree',widget_blueprint_path=path,parent_widget_name='RootCanvas',tree=[row])
        else:
            keys=('properties',) if path==INTERVIEW and name.startswith(('AnswerPad','Txt_Answer')) else ('slot_props','properties')
            result=call('ui_set_widget_properties',widget_blueprint_path=path,widget_name=name,
                **{k:v for k,v in row.items() if k in keys})
            assert not result.get('unknown_slot_props') and not result.get('rejected_properties'),result
    if path==INTERVIEW:
        call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/ink_slot_setup.py',resources=['asset:'+path])
        for name in ('ConversationEdge','ConversationPanel','SpeakerBack','SpeakerTag'):
            call('ui_set_variable',widget_blueprint_path=path,widget_name=name,is_variable=True)
    result=call('blueprint_compile',path=path,save=True)
    assert not result.get('error_count') and not result.get('warning_count'),result


def phone_context():
    import build_interview as interview
    import build_phone_progress as phone
    interview.declare(PHONE,{},[('Saved'+name+'Brush','struct:/Script/SlateCore.SlateBrush','') for name in phone.INK_BORDERS])
    for name in phone.INK_BORDERS:
        call('ui_set_variable',widget_blueprint_path=PHONE,widget_name=name,is_variable=True)
    result=call('blueprint_compile',path=PHONE,save=True)
    assert not result.get('error_count') and not result.get('warning_count'),result


if __name__=='__main__':
    if sys.argv[1]=='assets':print(assets())
    else:
        import editor_lock
        owner=os.environ.get('FOA_AGENT','main-level2-ink')
        os.environ.update(FOA_AGENT=owner,HAYBA_AGENT_ID=owner,FOA_CALLER=owner)
        target={'interview':INTERVIEW,'journey':JOURNEY,'drive':DRIVE,'phone':PHONE}.get(sys.argv[1])
        editor_lock.acquire(owner,wait_s=5,ttl=120,areas=[target or ROOT])
        try:
            assert not call('editor_get_state')['pie_running']
            import_assets() if sys.argv[1]=='import' else apply(target)
        finally:editor_lock.release(owner)
