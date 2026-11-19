"""One small wave-crossing impulse, integrated into the existing swept car move.

The model below verifies the scalar radial math offline. Runtime remains native
Blueprint; the existing MPC supplies the same origin and timestamp as the shader.
"""
from dataclasses import dataclass
import build_drive as b
import drive_data as d

VARIABLES=[('ShockwaveStamp','real','-10'),('ShockwaveGap','real','0'),
           ('ShockwaveFired','bool','false'),('ShockwaveVelocity','vector','0,0,0'),
           ('ShockwaveOffset','vector','0,0,0')]
SIGNATURES={'UpdateShockwave':[('Delta','real')],'ResetShockwave':[]}


@dataclass
class State:
    stamp:float=-10.
    gap:float=0.
    fired:bool=False
    speed:float=0.


def advance(state,stamp,age,distance,dt,strength=1.):
    dt=max(0.,min(.1,dt));new=stamp!=state.stamp
    # Quarter-band pressure has become visible; the leading edge itself is zero.
    gap=distance+d.SHOCKWAVE_BAND*.25-max(0.,age)*d.SHOCKWAVE_SPEED
    old_gap=distance+d.SHOCKWAVE_BAND*.25 if new else state.gap
    already=state.fired and not new
    fired=(strength>0 and stamp>=0 and 0<=age<=d.SHOCKWAVE_DURATION and
           distance>1. and not already and old_gap>=0 and gap<=0)
    speed=d.SHOCKWAVE_NUDGE_SPEED if fired else state.speed
    used=min(dt,speed/d.SHOCKWAVE_NUDGE_DECEL)
    offset=speed*used-.5*d.SHOCKWAVE_NUDGE_DECEL*used*used
    return State(stamp,gap,already or fired,max(0.,speed-d.SHOCKWAVE_NUDGE_DECEL*dt)),offset,fired


def setup():
    for name,typ,value in VARIABLES:
        b.call('blueprint_add_variable',path=b.CAR,variable_name=name,variable_type=typ,
               default_value=value,category='Drive',update_existing=True)
    info=b.call('blueprint_get_info',path=b.CAR)
    for name,inputs in SIGNATURES.items():
        if name not in info['functions']:
            b.call('blueprint_add_function',path=b.CAR,function_name=name,inputs=[dict(name=n,type=t) for n,t in inputs])


def reset():
    g=b.G(b.CAR,'ResetShockwave')
    for name,_,value in VARIABLES:g.setv(name,False if value=='false' else value)
    g.finish()


def update():
    g=b.G(b.CAR,'UpdateShockwave')
    impact=g.do(b.ML+'GetVectorParameterValue',Collection=b.CITY_MPC,ParameterName='Impact0')
    parts=g.math('BreakColor',InColor=impact)
    stamp=(parts[0],'B');strength=(parts[0],'A')
    age=g.math('Subtract_DoubleDouble',A=g.f(b.GS+'GetTimeSeconds'),B=stamp)
    origin=g.math('MakeVector',X=(parts[0],'R'),Y=(parts[0],'G'),Z=0)
    pos=g.math('BreakVector',InVec=g.f(b.A+'K2_GetActorLocation'))
    flat=g.math('MakeVector',X=(pos[0],'X'),Y=(pos[0],'Y'),Z=0)
    radial=g.math('Subtract_VectorVector',A=flat,B=origin)
    distance=g.math('VSize',A=radial)
    radius=g.math('Multiply_DoubleDouble',A=g.math('FMax',A=age,B=0),B=d.SHOCKWAVE_SPEED)
    pressure_distance=g.math('Add_DoubleDouble',A=distance,B=d.SHOCKWAVE_BAND*.25)
    gap=g.math('Subtract_DoubleDouble',A=pressure_distance,B=radius)
    new=g.math('NotEqual_DoubleDouble',A=stamp,B=g.getv('ShockwaveStamp'))
    previous=g.math('SelectFloat',A=pressure_distance,B=g.getv('ShockwaveGap'),bPickA=new)
    already=g.math('BooleanAND',A=g.getv('ShockwaveFired'),B=g.math('Not_PreBool',A=new))
    conditions=[g.math('Greater_DoubleDouble',A=strength,B=0),
        g.math('GreaterEqual_DoubleDouble',A=stamp,B=0),
        g.math('GreaterEqual_DoubleDouble',A=age,B=0),
        g.math('LessEqual_DoubleDouble',A=age,B=d.SHOCKWAVE_DURATION),
        g.math('Greater_DoubleDouble',A=distance,B=1),g.math('Not_PreBool',A=already),
        g.math('GreaterEqual_DoubleDouble',A=previous,B=0),g.math('LessEqual_DoubleDouble',A=gap,B=0)]
    crossed=conditions[0]
    for condition in conditions[1:]:crossed=g.math('BooleanAND',A=crossed,B=condition)
    direction=g.math('Normal',A=radial,Tolerance=.0001)
    impulse=g.math('Multiply_VectorFloat',A=direction,B=d.SHOCKWAVE_NUDGE_SPEED)
    # Keep the old stamp/gap until all crossing consumers have executed: getters
    # are pure Blueprint nodes and are re-evaluated for each setter.
    g.setv('ShockwaveVelocity',g.math('SelectVector',A=impulse,B=g.getv('ShockwaveVelocity'),bPickA=crossed))
    g.setv('ShockwaveFired',g.math('BooleanOR',A=already,B=crossed))
    g.setv('ShockwaveGap',gap);g.setv('ShockwaveStamp',stamp)
    velocity=g.getv('ShockwaveVelocity');speed=g.math('VSize',A=velocity)
    dt=g.math('FClamp',Value=g.arg('Delta'),Min=0,Max=.1)
    used=g.math('FMin',A=dt,B=g.math('Divide_DoubleDouble',A=speed,B=d.SHOCKWAVE_NUDGE_DECEL))
    distance_step=g.math('Subtract_DoubleDouble',A=g.math('Multiply_DoubleDouble',A=speed,B=used),
        B=g.math('Multiply_DoubleDouble',A=.5*d.SHOCKWAVE_NUDGE_DECEL,B=g.math('Multiply_DoubleDouble',A=used,B=used)))
    g.setv('ShockwaveOffset',g.math('Multiply_VectorFloat',A=g.math('Normal',A=velocity,Tolerance=.0001),B=distance_step))
    g.setv('ShockwaveVelocity',g.math('VInterpTo_Constant',Current=velocity,Target='0,0,0',DeltaTime=dt,InterpSpeed=d.SHOCKWAVE_NUDGE_DECEL))
    g.finish()
