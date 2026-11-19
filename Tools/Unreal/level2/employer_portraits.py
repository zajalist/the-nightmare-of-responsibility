"""Original cut-paper portraits and their entrance in the job dialogue."""
from pathlib import Path
import os

import build_drive as b
import build_interview as ui
import build_job_hunt as jobs

ROOT = '/Game/FoA/Level2/UI'
NAMES = ('T_Employer_Market', 'T_Employer_Dispatch', 'T_Employer_Northline')
BP, UI, G = jobs.BP, jobs.UI, jobs.G
W = '/Script/UMG.Widget:'


def generate(folder):
    from PIL import Image, ImageDraw

    inks = ((188,74,35),(19,120,117),(81,93,147))
    for i,(name,accent) in enumerate(zip(NAMES,inks)):
        image=Image.new('RGBA',(864,864))
        draw=ImageDraw.Draw(image)
        def poly(points,fill):
            draw.polygon([(3*x,3*y) for x,y in points],fill)
        def line(points,fill,width=2):
            draw.line([(3*x,3*y) for x,y in points],fill,3*width,joint='curve')
        paper=(236,228,209); shadow=(167,151,128); black=(17,17,22)
        poly(((27,30),(278,11),(270,252),(11,278)),black)
        poly(((36,35),(270,18),(262,245),(19,268)),paper)
        poly(((43,42),(262,27),(254,238),(27,259)),accent)
        for x in range(45,258,7):
            line(((x,44),(max(33,x-18),242)),tuple(max(0,c-18) for c in accent),1)
        poly(((28,256),(45,213),(95,192),(105,169),(168,165),(184,190),(239,206),(253,239)),black)
        poly(((103,166),(166,166),(173,190),(149,215),(111,194)),shadow)
        if i==0:
            poly(((94,64),(137,53),(177,74),(196,115),(183,167),(158,188),(122,179),(98,151),(85,103)),black)
            poly(((99,85),(141,72),(172,90),(184,116),(173,161),(151,179),(123,170),(102,146),(94,112)),paper)
            poly(((91,101),(101,68),(124,51),(156,50),(182,65),(194,97),(173,95),(163,78),(139,81),(117,102)),black)
            poly(((45,222),(80,202),(97,196),(123,219),(148,211),(170,197),(189,201),(206,247),(58,258)),accent)
            line(((89,203),(105,244)),paper,4);line(((174,201),(165,245)),paper,4)
        elif i==1:
            poly(((95,72),(151,58),(184,79),(194,117),(180,158),(154,185),(123,177),(94,144),(87,100)),black)
            poly(((101,83),(148,72),(173,89),(183,113),(171,150),(153,174),(125,166),(104,140),(96,105)),paper)
            poly(((89,107),(89,75),(111,51),(155,48),(183,64),(194,99),(174,87),(145,76),(119,81),(104,104)),black)
            line(((89,109),(88,85),(99,63),(121,49),(156,47),(179,65),(191,96)),paper,4)
            poly(((81,97),(95,96),(100,129),(86,132)),black)
            line(((92,128),(105,146),(133,148)),black,3)
            poly(((44,222),(89,196),(113,220),(146,221),(177,195),(229,214),(250,239)),shadow)
            poly(((70,209),(86,200),(100,252),(82,255)),paper)
            poly(((184,197),(199,201),(214,245),(197,248)),paper)
        else:
            poly(((92,79),(129,53),(176,68),(195,97),(186,151),(159,185),(127,187),(104,163),(87,113)),black)
            poly(((103,82),(138,69),(174,83),(184,101),(176,150),(155,175),(129,177),(108,156),(97,112)),paper)
            poly(((90,119),(83,94),(93,66),(115,54),(149,49),(174,57),(193,79),(190,99),(176,84),(156,73),(120,78),(105,93),(102,112)),black)
            poly(((92,207),(107,192),(142,219),(163,204),(176,190),(197,212),(170,249),(112,253)),paper)
            poly(((132,222),(147,218),(154,229),(151,248),(139,250),(132,231)),accent)
            line(((100,110),(127,107),(137,113),(151,106),(178,104)),black,3)
            line(((104,111),(108,127),(128,127),(133,113)),black,2)
            line(((147,109),(150,125),(171,122),(176,106)),black,2)
        poly(((153,87),(177,98),(182,115),(171,153),(153,174),(157,153),(147,142),(155,123)),shadow)
        line(((107,114),(118,111),(129,114)),black,3)
        line(((152,111),(164,109),(172,111)),black,3)
        line(((139,115),(133,137),(145,141)),black,2)
        line(((123,151),(138,154),(155,150)),black,2)
        for x in range(108,171,5):
            if x<121 or x>155:
                line(((x,146),(x+4,155)),shadow,1)
        image.resize((512,512),Image.Resampling.LANCZOS).save(folder/(name+'.png'))


def import_portraits():
    directory=Path(os.environ['TEMP'])/'hayba-asset-connectors'/'foa-employer-portraits'/'textures'
    directory.mkdir(parents=True,exist_ok=True)
    generate(directory)
    for name in NAMES:
        if not Path('P:/FoA/Content/FoA/Level2/UI',name+'.uasset').exists():
            b.call('asset_import',source_file=str(directory/(name+'.png')),destination_path=ROOT,asset_type='texture')
        b.call('texture_set_settings',path=ROOT+'/'+name,properties=dict(lod_group='UI',
               compression_settings='EditorIcon',mip_gen_settings='NoMipmaps',never_stream=True,srgb=True))
        b.call('asset_save',asset_paths=[ROOT+'/'+name])


def declare():
    b.call('blueprint_add_variable',path=BP,variable_name='EmployerEntrance',variable_type='float',
           default_value='0',update_existing=True)
    if not b.h.call('blueprint_inspect_graph',{'path':BP,'graph_name':'TickEmployer'}).get('ok'):
        b.call('blueprint_add_function',path=BP,function_name='TickEmployer')
    ui.declare(UI,{'PaintEmployer':[('Index','int'),('Alpha','float')]})
    if not b.call('ui_query',path=UI,name_pattern='EmployerPortrait').get('matches'):
        b.call('ui_build_tree',widget_blueprint_path=UI,parent_widget_name='RootCanvas',tree=[{
            'class':'Image','name':'EmployerPortrait','properties':{'Visibility':'Collapsed'},
            'slot_props':dict(anchors_min=[0,1],anchors_max=[0,1],alignment=[0,1],
                              position=[31,-390],size=[302,302],z_order=2)}])
    b.call('ui_set_variable',widget_blueprint_path=UI,widget_name='EmployerPortrait',is_variable=True)
    b.call('ui_set_widget_properties',widget_blueprint_path=UI,widget_name='EmployerPortrait',
           slot_props={'position':[34,-482],'size':[315,315],'z_order':2})
    b.call('ui_compile_widget',widget_blueprint_path=UI)


def paint(g,index,alpha=1):
    g.do(b.cls(UI)+':PaintEmployer',self=g.getv('InterviewHUD'),Index=index,Alpha=alpha)


def paint_widget():
    g=G(UI,'PaintEmployer')
    image=g.getv('EmployerPortrait')
    visible=ui.guard(g,g.math('GreaterEqual_IntInt',A=g.arg('Index'),B=0))
    paths=tuple(f'{ROOT}/{name}.{name}' for name in NAMES)
    texture=jobs.pick(g,'Object',paths,g.arg('Index'))
    texture=g.cast(texture,'/Script/Engine.Texture2D','Texture 2D')
    g.do('/Script/UMG.Image:SetBrushFromTexture',self=image,Texture=texture,bMatchSize=False)
    g.do(W+'SetVisibility',self=image,InVisibility='HitTestInvisible')
    g.do(W+'SetRenderOpacity',self=image,InOpacity=g.arg('Alpha'))
    x=g.math('Lerp',A=-72,B=0,Alpha=g.arg('Alpha'))
    g.do(W+'SetRenderTranslation',self=image,Translation=g.math('MakeVector2D',X=x,Y=0))
    g.side(visible,False)
    g.do(W+'SetVisibility',self=image,InVisibility='Collapsed')
    g.finish()


def tick():
    g=G(BP,'TickEmployer')
    pitch=ui.guard(g,ui.eq(g,'DialogueMode',jobs.PITCH))
    ui.valid(g,g.getv('InterviewHUD'))
    elapsed=g.math('Subtract_DoubleDouble',A=g.f(b.GS+'GetTimeSeconds'),B=g.getv('EmployerEntrance'))
    alpha=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=elapsed,B=.28),Min=0,Max=1)
    paint(g,g.getv('Stop'),alpha)
    done=ui.guard(g,g.math('GreaterEqual_DoubleDouble',A=alpha,B=1))
    cleared=g.do(b.SL+'K2_ClearTimer',FunctionName='TickEmployer')
    g.link(pitch,'else',cleared[0],'execute')
    g.finish()


def install():
    import_portraits()
    declare()
    paint_widget()
    tick()
