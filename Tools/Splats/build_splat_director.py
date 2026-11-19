"""Native Hayba Blueprint builder. One step under a Level2 lease: assets | events.
One director per test map. G retriggers at the camera's visibility hit (500 cm fallback).
"""
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
from held_tool_graphs import Batch, inspect
from build_splat_dynamics import call, MPC, ROOT, require_lease

BP = ROOT + '/Blueprints/BP_SplatFXDirector'
K = '/Script/Engine.KismetMathLibrary:'
GS = '/Script/Engine.GameplayStatics:'
ML = '/Script/Engine.KismetMaterialLibrary:'


def assets():
    from hayba_call import call as raw
    if not raw('blueprint_inspect', {'path': BP}).get('ok'):
        call('blueprint_create', name='BP_SplatFXDirector', package_path=BP, parent_class_path='/Script/Engine.Actor')
    for name, typ, value, edit in [
        ('AmbientIntensity', 'float', '0.8', True), ('SandRadius', 'float', '300', True),
        ('SandCentre', 'linear_color', '(R=0,G=0,B=150,A=0)', True),
        ('Wind', 'linear_color', '(R=1,G=0.3,B=0,A=0)', True),
        ('TargetBuilding', 'float', '-1', True), ('EventStartTime', 'float', '0', False)]:
        call('blueprint_add_variable', path=BP, variable_name=name, variable_type=typ, default_value=value,
             instance_editable=edit, category='Splat Dynamics', update_existing=True)
    call('blueprint_compile', path=BP); call('asset_save', asset_paths=[BP])


def events():
    ns, _ = inspect(BP, 'EventGraph')
    assert not any(n['title'] == 'Write dynamics' for n in ns), 'Director already built; inspect before editing'
    b = Batch(BP, 'EventGraph')
    # A freshly created actor has three empty event stubs; only these are replaced.
    if ns:
        b.ops.append(dict(op='remove', node_ids=[n['node_id'] for n in ns]))
    b.ops.append(dict(op='add_event', ref='begin', event_name='ReceiveBeginPlay', x=0, y=0))
    b.fn('pc', GS + 'GetPlayerController', 0, 250, PlayerIndex=0)
    b.fn('enable', '/Script/Engine.Actor:EnableInput', 320, 0)
    b.link('pc', 'ReturnValue', 'enable', 'PlayerController'); b.chain('begin', 'enable')
    b.comment('Enable debug trigger', ['begin', 'pc', 'enable'])

    b.ops.append(dict(op='add_event', ref='tick', event_name='ReceiveTick', x=0, y=650))
    previous = 'tick'
    refs = ['tick']
    for i, (var, vector) in enumerate([('AmbientIntensity', False), ('Wind', True), ('SandCentre', True),
                                       ('SandRadius', False), ('TargetBuilding', False)]):
        x = 320 + i * 380
        b.get('v'+str(i), var, x, 900)
        b.fn('mpc'+str(i), ML + ('SetVectorParameterValue' if vector else 'SetScalarParameterValue'),
             x, 650, Collection=MPC, ParameterName=var)
        b.link('v'+str(i), var, 'mpc'+str(i), 'ParameterValue')
        b.chain(previous, 'mpc'+str(i)); previous = 'mpc'+str(i)
        refs += ['v'+str(i), previous]
    b.fn('now', GS+'GetTimeSeconds', 0, 1400)
    b.get('start', 'EventStartTime', 0, 1600)
    b.fn('age', K+'Subtract_DoubleDouble', 300, 1400)
    b.link('now', 'ReturnValue', 'age', 'A'); b.link('start', 'EventStartTime', 'age', 'B')
    b.fn('delay', K+'Subtract_DoubleDouble', 600, 1250, B=4)
    b.link('age', 'ReturnValue', 'delay', 'A')
    b.fn('back', K+'Subtract_DoubleDouble', 600, 1550, A=11)
    b.link('age', 'ReturnValue', 'back', 'B')
    b.fn('min', K+'FMin', 900, 1400)
    b.link('delay', 'ReturnValue', 'min', 'A'); b.link('back', 'ReturnValue', 'min', 'B')
    b.fn('div', K+'Divide_DoubleDouble', 1200, 1400, B=3)
    b.link('min', 'ReturnValue', 'div', 'A')
    b.fn('clamp', K+'FClamp', 1500, 1400, Min=0, Max=1)
    b.link('div', 'ReturnValue', 'clamp', 'Value')
    b.fn('phase', ML+'SetScalarParameterValue', 2220, 650, Collection=MPC, ParameterName='SandProgress')
    b.link('clamp', 'ReturnValue', 'phase', 'ParameterValue'); b.chain(previous, 'phase')
    b.comment('Write dynamics', refs + ['now','start','age','delay','back','min','div','clamp','phase'])

    b.node('key', 'input_key', 0, 2100, key='G')
    b.fn('cm', GS+'GetPlayerCameraManager', 0, 2400, PlayerIndex=0)
    b.fn('loc', '/Script/Engine.PlayerCameraManager:GetCameraLocation', 300, 2350)
    b.fn('rot', '/Script/Engine.PlayerCameraManager:GetCameraRotation', 300, 2650)
    b.link('cm', 'ReturnValue', 'loc', 'self'); b.link('cm', 'ReturnValue', 'rot', 'self')
    b.fn('forward', K+'GetForwardVector', 600, 2650); b.link('rot', 'ReturnValue', 'forward', 'InRot')
    b.fn('reach', K+'Multiply_VectorFloat', 900, 2650, B=500)
    b.link('forward', 'ReturnValue', 'reach', 'A')
    b.fn('end', K+'Add_VectorVector', 1200, 2450)
    b.link('loc', 'ReturnValue', 'end', 'A'); b.link('reach', 'ReturnValue', 'end', 'B')
    b.fn('trace', '/Script/Engine.KismetSystemLibrary:LineTraceSingle', 1500, 2100,
         TraceChannel='TraceTypeQuery1', bTraceComplex='true', DrawDebugType='None', bIgnoreSelf='true')
    b.link('key', 'Pressed', 'trace', 'execute')
    b.link('loc', 'ReturnValue', 'trace', 'Start'); b.link('end', 'ReturnValue', 'trace', 'End')
    b.fn('hit', GS+'BreakHitResult', 1800, 2500)
    b.link('trace', 'OutHit', 'hit', 'Hit')
    b.fn('select', K+'SelectVector', 2150, 2500)
    b.link('trace', 'ReturnValue', 'select', 'bPickA')
    b.link('hit', 'ImpactPoint', 'select', 'A'); b.link('end', 'ReturnValue', 'select', 'B')
    b.fn('color', K+'Conv_VectorToLinearColor', 2450, 2500)
    b.link('select', 'ReturnValue', 'color', 'InVec')
    b.set('centre', 'SandCentre', 2450, 2100); b.link('color', 'ReturnValue', 'centre', 'SandCentre')
    b.fn('debugNow', GS+'GetTimeSeconds', 2750, 2550)
    b.fn('immediate', K+'Subtract_DoubleDouble', 3050, 2550, B=4)
    b.link('debugNow', 'ReturnValue', 'immediate', 'A')
    b.set('restart', 'EventStartTime', 3050, 2100)
    b.link('immediate', 'ReturnValue', 'restart', 'EventStartTime')
    b.chain('trace', 'centre', 'restart')
    b.comment('Sand at look point', ['key','cm','loc','rot','forward','reach','end','trace','hit','select',
                                     'color','centre','debugNow','immediate','restart'])
    b.run()


if __name__ == '__main__':
    require_lease()
    {'assets': assets, 'events': events}[sys.argv[1]]()
