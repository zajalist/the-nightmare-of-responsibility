"""World hiring boards and parking targets for the open job route."""

import os
from pathlib import Path
import sys
from math import cos, sin, radians

sys.path.insert(0,str(Path(__file__).resolve().parent))
from drive_data import GOALS
from job_hunt_data import JOBS, BOSS_MINIMUM

BOSS=3
DESTINATIONS=(*GOALS,(48844,340,2))
NAMES=(*(job.employer for job in JOBS),'Central Personnel')
BOARDS=tuple((f'JobBoard{i}',f'JobBoardText{i}') for i in range(len(DESTINATIONS)))
# Off the carriageway, with clearance from the dynamically positioned parking post.
BOARD_POSES=((15995,820,156,180),(33680,9100,156,180),(45860,-7260,156,90),(49290,960,156,180))


def closest(g,position):
    distance=g.math('Vector_Distance',V1=position,V2=','.join(map(str,DESTINATIONS[0])))
    target=0
    for i,where in enumerate(DESTINATIONS[1:],1):
        candidate=g.math('Vector_Distance',V1=position,V2=','.join(map(str,where)))
        better=g.math('Less_DoubleDouble',A=candidate,B=distance)
        if i==BOSS:
            better=g.math('BooleanAND',A=better,B=g.math('GreaterEqual_IntInt',A=g.getv('Employability'),B=BOSS_MINIMUM))
        distance=g.math('SelectFloat',A=candidate,B=distance,bPickA=better)
        target=g.math('SelectInt',A=i,B=target,bPickA=better)
    return target,distance


def next_job(g):
    result=BOSS
    for i in reversed(range(len(JOBS))):
        result=g.math('SelectInt',A=result,B=i,bPickA=g.getv(f'Edited{i}'))
    return g.math('SelectInt',A=BOSS,B=result,bPickA=g.math('GreaterEqual_IntInt',A=g.getv('Employability'),B=BOSS_MINIMUM))


def declare():
    import build_drive as b
    b.call('blueprint_add_variable',path=b.CAR,variable_name='ArrivalJob',variable_type='int',default_value='0',update_existing=True)
    info=b.call('blueprint_get_info',path=b.ROAD);existing={row['name'] for row in info.get('components',[])}
    for panel,text in BOARDS:
        for name,kind in ((panel,'StaticMeshComponent'),(text,'TextRenderComponent')):
            if name not in existing:b.call('blueprint_add_component',path=b.ROAD,component_name=name,component_class_path='/Script/Engine.'+kind)
    b.call('python_exec_file',path=Path(__file__).resolve().as_posix(),env={'FOA_JOB_ROUTE':'boards'},resources=['asset:'+b.ROAD])


def templates():
    import unreal as u
    from free_drive_setup import templates as road_templates
    path='/Game/FoA/Level2/Drive/BP_L2RoadNetwork'
    bp,sub,lib,gathered,handles,components=road_templates(path)
    for i,((panel,text),(x,y,z,yaw)) in enumerate(zip(BOARDS,BOARD_POSES)):
        for name in (panel,text):assert sub.attach_subobject(handles['Root'],handles[name])
        background=components[panel];label=components[text]
        background.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
        background.set_material(0,u.load_asset('/Game/FoA/Level2/Drive/MI_L2Dark'))
        # A freestanding panel reaches the pavement with the type in its upper half.
        background.set_editor_property('relative_scale3d',u.Vector(.24,4.8,4.35))
        background.set_editor_property('relative_location',u.Vector(x,y,z))
        forward=u.Vector(cos(radians(yaw)),sin(radians(yaw)),0)
        label.set_editor_property('relative_location',u.Vector(x,y,z+65)+forward*16)
        label.set_text(u.Text(NAMES[i].upper()+('\nINTERVIEW' if i==BOSS else '\nHIRING')))
        label.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER)
        label.set_vertical_alignment(u.VerticalTextAligment.EVRTA_TEXT_CENTER)
        label.set_text_render_color(u.Color(250,246,236,255));label.set_world_size(48.)
        for component in (background,label):
            component.set_editor_property('relative_rotation',u.Rotator(yaw=yaw))
            component.set_editor_property('cast_shadow',False)
            component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
            component.set_visibility(i!=BOSS)
    assert u.EditorAssetLibrary.save_loaded_asset(bp,False)


if __name__=='__main__':
    assert os.environ.get('FOA_JOB_ROUTE')=='boards'
    templates()
