"""Native spring-arm chase camera; the boom handles walls and owner exclusion."""
import math
import build_drive as b

ARM=850.0
PIVOT=185.0
PITCH=12.0


def selftest():
    # At rest the camera is above the sedan, and sees its roof plus street-level facades.
    eye=PIVOT+ARM*math.sin(math.radians(PITCH))
    assert 300<eye<400
    assert ARM*math.cos(math.radians(PITCH))>800
    assert PITCH<80/2
    print('Chase camera framing check passed',round(eye,1),'cm above car root')


def build():
    for name,typ,value in [('CameraPitch','float','12'),('CameraYawOffset','float','0'),('CameraReady','bool','false')]:
        b.call('blueprint_add_variable',path=b.CAR,variable_name=name,variable_type=typ,default_value=value,
               category='Drive Camera',instance_editable=name!='CameraReady',update_existing=True)
    info=b.call('blueprint_get_info',path=b.CAR)
    if 'UpdateCamera' not in info['functions']:
        b.call('blueprint_add_function',path=b.CAR,function_name='UpdateCamera',inputs=[dict(name='Delta',type='float')])
    g=b.G(b.CAR,'UpdateCamera');boom=g.getv('CameraBoom');dt=g.arg('Delta')
    active=g.branch(g.getv('Active'));g.side(active)
    pc=g.f(b.GS+'GetPlayerController',PlayerIndex=0)
    back=g.math('BooleanOR',A=g.f('/Script/Engine.PlayerController:IsInputKeyDown',self=pc,Key='Q'),
                B=g.f('/Script/Engine.PlayerController:IsInputKeyDown',self=pc,Key='Gamepad_LeftShoulder'))
    car=g.f(b.K+'BreakRotator',InRot=g.f(b.A+'K2_GetActorRotation'))
    offset=g.math('SelectFloat',A=180,B=g.getv('CameraYawOffset'),bPickA=back)
    yaw=g.math('Add_DoubleDouble',A=(car[0],'Yaw'),B=offset)
    pitch=g.math('FClamp',Value=g.getv('CameraPitch'),Min=5,Max=22)
    target=g.math('MakeRotator',Pitch=g.math('Multiply_DoubleDouble',A=-1,B=pitch),Yaw=yaw,Roll=0)
    smooth=g.math('RInterpTo',Current=g.f(b.SC+'K2_GetComponentRotation',self=boom),Target=target,DeltaTime=dt,InterpSpeed=6)
    rotation=g.math('SelectRotator',A=smooth,B=target,bPickA=g.getv('CameraReady'))
    g.do(b.SC+'K2_SetWorldRotation',self=boom,NewRotation=rotation,bSweep=False,bTeleport=True)
    g.setv('CameraReady',True);g.finish()

def wire():
    nodes,_=b.inspect(b.CAR,'EventGraph')
    if any(n['title'].replace(' ','')=='UpdateCamera' for n in nodes):return
    tick=next(n['node_id'] for n in nodes if n['title']=='Event Tick')
    step=next(n['node_id'] for n in nodes if n['title'].replace(' ','')=='DriveStep')
    graph=b.Batch(b.CAR,'EventGraph')
    graph.fn('camera',b.cls(b.CAR)+':UpdateCamera',800,800)
    graph.chain(step,'camera');graph.link(tick,'DeltaSeconds','camera','Delta')
    graph.comment('Camera follow',['camera']);graph.run()


if __name__=='__main__':selftest()
