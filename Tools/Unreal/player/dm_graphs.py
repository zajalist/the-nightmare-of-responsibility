"""Anim lane: the Blueprint side of distance-matched starts and stops in ABP_FoAPlayer, as Hayba graph batches.
  python Tools/Unreal/player/dm_graphs.py functions | update
functions  the anim node functions the Start / Stop Sequence Evaluators call (dm_states.py binds them):
           SetupStart   explicit time 0 when the start becomes relevant
           UpdateStart  AdvanceTimeByDistanceMatching by the capsule's travel this update (play rate clamped 0.75..1.5)
           UpdateStop   DistanceMatchToTarget(StopDistance) while he is still sliding to a stop, then plain time for
                        the settle
update     BlueprintUpdateAnimation: DisplacementSinceLastUpdate = GroundSpeed * dt, StopDistance from
           PredictGroundMovementStopLocation with the pawn's own braking. StartDone is set by the evaluator after
           its first usable stance at0.65s, not by capsule speed."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
from held_tool_graphs import Batch, inspect, find  # noqa: E402

ABP = '/Game/FoA/Characters/Player/ABP_FoAPlayer'
SEQ = '/Script/AnimGraphRuntime.SequenceEvaluatorLibrary:'
DM = '/Script/AnimationLocomotionLibraryRuntime.AnimDistanceMatchingLibrary:'
K = '/Script/Engine.KismetMathLibrary:'


def functions():
    suffix = sys.argv[2] if len(sys.argv) > 2 else ""
    for name in ('SetupStart', 'SetupStop', 'UpdateStart', 'UpdateStop'):
        graph = name + suffix
        nodes, _ = inspect(ABP, graph)
        assert len(nodes) <= 2, f'{name} already built'
        e = find(nodes, graph)
        b = Batch(ABP, graph)
        b.fn('eval', SEQ + 'ConvertToSequenceEvaluatorPure', 250, 200); b.link(e, 'Node', 'eval', 'Node')
        if name == 'SetupStart':
            b.fn('zero', SEQ + 'SetExplicitTime', 600, 0, Time=0.0); b.link('eval', 'SequenceEvaluator', 'zero', 'SequenceEvaluator')
            b.chain(e, 'zero')
            b.set('done','StartDone',900,0);b.pin('done','StartDone','false');b.chain('zero','done')
            b.comment('Start from frame 0', ['eval', 'zero'])
        elif name == 'SetupStop':
            b.get('distance','StopDistance',250,400)
            b.fn('match',DM+'DistanceMatchToTarget',600,0,DistanceCurveName='Distance')
            b.link('eval','SequenceEvaluator','match','SequenceEvaluator');b.link('distance','StopDistance','match','DistanceToTarget')
            b.chain(e,'match')
        elif name == 'UpdateStart':
            b.get('moved', 'DisplacementSinceLastUpdate', 250, 400)
            b.fn('advance', DM + 'AdvanceTimeByDistanceMatching', 600, 0, DistanceCurveName='Distance', PlayRateClamp='(X=0.75,Y=1.5)')
            b.link(e, 'Context', 'advance', 'UpdateContext'); b.link('eval', 'SequenceEvaluator', 'advance', 'SequenceEvaluator')
            b.link('moved', 'DisplacementSinceLastUpdate', 'advance', 'DistanceTraveled')
            b.chain(e, 'advance')
            b.fn('phaseTime',SEQ+'GetAccumulatedTime',900,400);b.link('eval','SequenceEvaluator','phaseTime','SequenceEvaluator')
            b.fn('stance',K+'GreaterEqual_DoubleDouble',1150,400,B=.65);b.link('phaseTime','ReturnValue','stance','A')
            b.set('done','StartDone',1400,0);b.link('stance','ReturnValue','done','StartDone');b.chain('advance','done')
            b.comment('Step with the capsule', ['eval', 'moved', 'advance'])
        else:
            b.get('left', 'StopDistance', 250, 400)
            b.fn('sliding', K + 'Greater_DoubleDouble', 500, 400, B=1.0); b.link('left', 'StopDistance', 'sliding', 'A')
            b.node('which', 'branch', 600, 0); b.link('sliding', 'ReturnValue', 'which', 'Condition')
            b.fn('match', DM + 'DistanceMatchToTarget', 900, -100, DistanceCurveName='Distance')
            b.link('eval', 'SequenceEvaluator', 'match', 'SequenceEvaluator'); b.link('left', 'StopDistance', 'match', 'DistanceToTarget')
            b.fn('settle', SEQ + 'AdvanceTime', 900, 200, PlayRate=1.0)
            b.link(e, 'Context', 'settle', 'UpdateContext'); b.link('eval', 'SequenceEvaluator', 'settle', 'SequenceEvaluator')
            b.chain(e, 'which', 'match'); b.link('which', 'else', 'settle', 'execute')
            b.comment('Land on the stop point', ['eval', 'left', 'sliding', 'which', 'match', 'settle'])
        b.run()


def update():
    nodes, _ = inspect(ABP, 'EventGraph')
    assert not any(n['title'] == 'Set DisplacementSinceLastUpdate' for n in nodes), 'distance update already built'
    e = find(nodes, 'Event BlueprintUpdateAnimation')
    b = Batch(ABP, 'EventGraph')
    b.get('speed', 'GroundSpeed', 6000, 300)
    b.fn('travel', K + 'Multiply_DoubleDouble', 6250, 300)
    b.link('speed', 'GroundSpeed', 'travel', 'A'); b.link(e, 'DeltaTimeX', 'travel', 'B')
    b.set('moved', 'DisplacementSinceLastUpdate', 6500, 0); b.link('travel', 'ReturnValue', 'moved', 'DisplacementSinceLastUpdate')
    b.get('movement', 'MovementComponent', 6000, 650)
    b.get('velocity', 'Velocity', 6000, 500)
    props = ('bUseSeparateBrakingFriction', 'BrakingFriction', 'GroundFriction', 'BrakingFrictionFactor', 'BrakingDecelerationWalking')
    for i, prop in enumerate(props):
        b.get(prop, prop, 6250, 650 + i * 150, '/Script/Engine.CharacterMovementComponent')
        b.link('movement', 'MovementComponent', prop, 'self')
    b.fn('predict', '/Script/AnimationLocomotionLibraryRuntime.AnimCharacterMovementLibrary:PredictGroundMovementStopLocation', 6600, 600)
    b.link('velocity', 'Velocity', 'predict', 'Velocity')
    for prop, pin in zip(props, ('bUseSeparateBrakingFriction', 'BrakingFriction', 'GroundFriction', 'BrakingFrictionFactor', 'BrakingDecelerationWalking')):
        b.link(prop, prop, 'predict', pin)
    b.fn('length', K + 'VSizeXY', 6900, 600); b.link('predict', 'ReturnValue', 'length', 'A')
    b.set('stop', 'StopDistance', 7200, 0); b.link('length', 'ReturnValue', 'stop', 'StopDistance')
    b.link(find(nodes, 'UpdateTurnInPlace'), 'then', 'moved', 'execute')
    b.chain('moved', 'stop')
    b.comment('Match capsule distance', ['speed', 'travel', 'moved', 'movement', 'velocity', *props, 'predict', 'length', 'stop'])
    b.run()


def turn():
    """UpdateTurnInPlace(DeltaSeconds), called from BlueprintUpdateAnimation (dm_states.py turn).
    While he stands (no move, no montage, no battle) a yaw change of the capsule is held off the body as RootYawOffset
    (Rotate Root Bone in the AnimGraph) and a turn clip steps it back: its TurnYaw curve (bake_turn_curves.py) is
    added as it plays, un-blended by TurnYawWeight so blend-outs never hand it back. Moving, a montage, battle or a
    cinematic (FootIKEnabled off) eases the offset out (FInterpTo 8). WantsTurn at |offset| > 50 deg; TurnIndex
    0 L90, 1 R90, 2 L180, 3 R180 (180 from 135 deg), latched for 2.2 s so a turn never swaps clips mid-step.
    The setters run after every reader of their old value (pure nodes re-evaluate at each consumer)."""
    nodes, _ = inspect(ABP, 'UpdateTurnInPlace')
    assert len(nodes) <= 2, 'UpdateTurnInPlace already built'
    e = find(nodes, 'UpdateTurnInPlace')
    b = Batch(ABP, 'UpdateTurnInPlace')
    b.get('char', 'Character', 0, 300)
    b.fn('rot', '/Script/Engine.Actor:K2_GetActorRotation', 250, 300); b.link('char', 'Character', 'rot', 'self')
    b.fn('yaw', K + 'BreakRotator', 500, 300); b.link('rot', 'ReturnValue', 'yaw', 'InRot')
    b.get('lastyaw', 'LastActorYaw', 500, 500)
    b.fn('dyaw0', K + 'Subtract_DoubleDouble', 750, 300); b.link('yaw', 'Yaw', 'dyaw0', 'A'); b.link('lastyaw', 'LastActorYaw', 'dyaw0', 'B')
    b.fn('dyaw', K + 'NormalizeAxis', 1000, 300); b.link('dyaw0', 'ReturnValue', 'dyaw', 'Angle')
    # TurnYaw un-blended by its clip weight (TurnYawWeight is 1 on every turn clip); 0 when no turn is playing
    b.fn('raw', '/Script/Engine.AnimInstance:GetCurveValue', 250, 700, CurveName='TurnYaw')
    b.fn('w', '/Script/Engine.AnimInstance:GetCurveValue', 250, 900, CurveName='TurnYawWeight')
    b.fn('active', K + 'Greater_DoubleDouble', 500, 1000, B=0.01); b.link('w', 'ReturnValue', 'active', 'A')
    b.fn('wsafe', K + 'FMax', 500, 900, B=0.01); b.link('w', 'ReturnValue', 'wsafe', 'A')
    b.fn('unbl', K + 'Divide_DoubleDouble', 750, 750); b.link('raw', 'ReturnValue', 'unbl', 'A'); b.link('wsafe', 'ReturnValue', 'unbl', 'B')
    b.fn('curve', K + 'SelectFloat', 1000, 750, B=0.0); b.link('unbl', 'ReturnValue', 'curve', 'A'); b.link('active', 'ReturnValue', 'curve', 'bPickA')
    b.get('lastturn', 'LastTurnYaw', 1000, 950)
    b.fn('dturn0', K + 'Subtract_DoubleDouble', 1250, 700); b.link('curve', 'ReturnValue', 'dturn0', 'A'); b.link('lastturn', 'LastTurnYaw', 'dturn0', 'B')
    b.fn('dturn', K + 'SelectFloat', 1450, 700, B=0.0); b.link('dturn0', 'ReturnValue', 'dturn', 'A'); b.link('active', 'ReturnValue', 'dturn', 'bPickA')
    b.comment('Read the turns', ['char', 'rot', 'yaw', 'lastyaw', 'dyaw0', 'dyaw', 'raw', 'w', 'active', 'wsafe', 'unbl', 'curve',
                                 'lastturn', 'dturn0', 'dturn'])
    b.get('move', 'ShouldMove', 1250, 900); b.fn('still', K + 'Not_PreBool', 1450, 900); b.link('move', 'ShouldMove', 'still', 'A')
    b.fn('montage', '/Script/Engine.AnimInstance:IsAnyMontagePlaying', 1250, 1050)
    b.fn('free', K + 'Not_PreBool', 1450, 1050); b.link('montage', 'ReturnValue', 'free', 'A')
    b.get('battle', 'IsBattle', 1250, 1200); b.fn('calm', K + 'Not_PreBool', 1450, 1200); b.link('battle', 'IsBattle', 'calm', 'A')
    b.fn('hold1', K + 'BooleanAND', 1650, 950); b.link('still', 'ReturnValue', 'hold1', 'A'); b.link('free', 'ReturnValue', 'hold1', 'B')
    b.fn('hold2', K + 'BooleanAND', 1850, 1000); b.link('hold1', 'ReturnValue', 'hold2', 'A'); b.link('calm', 'ReturnValue', 'hold2', 'B')
    b.get('feet', 'FootIKEnabled', 1650, 1300)  # off while a cinematic owns the body (SetCinematic)
    b.fn('holding', K + 'BooleanAND', 2050, 1050); b.link('hold2', 'ReturnValue', 'holding', 'A'); b.link('feet', 'FootIKEnabled', 'holding', 'B')
    b.get('off', 'RootYawOffset', 1250, 300)
    b.fn('held0', K + 'Subtract_DoubleDouble', 1450, 300); b.link('off', 'RootYawOffset', 'held0', 'A'); b.link('dyaw', 'ReturnValue', 'held0', 'B')
    b.fn('held1', K + 'Add_DoubleDouble', 1650, 300); b.link('held0', 'ReturnValue', 'held1', 'A'); b.link('dturn', 'ReturnValue', 'held1', 'B')
    b.fn('held', K + 'NormalizeAxis', 1850, 300); b.link('held1', 'ReturnValue', 'held', 'Angle')
    # Pawn's native local-control check handles an absent startup/preview controller.
    b.fn('fplocal','/Script/Engine.Pawn:IsLocallyControlled',1250,1550);b.link('char','Character','fplocal','self')
    b.get('fpyaw','bUseControllerRotationYaw',1500,1750,'/Script/Engine.Pawn');b.link('char','Character','fpyaw','self')
    b.fn('fpowned',K+'BooleanAND',1750,1550);b.link('fplocal','ReturnValue','fpowned','A');b.link('fpyaw','bUseControllerRotationYaw','fpowned','B')
    b.fn('fplimit',K+'FClamp',2050,1550,Min=-45,Max=45);b.link('held','ReturnValue','fplimit','Value')
    b.fn('fpease',K+'FInterpTo',2300,1750,Target=0,InterpSpeed=8);b.link('fplimit','ReturnValue','fpease','Current');b.link(e,'DeltaSeconds','fpease','DeltaTime')
    b.fn('fpheld',K+'SelectFloat',2550,1550);b.link('fpease','ReturnValue','fpheld','A');b.link('held','ReturnValue','fpheld','B');b.link('fpowned','ReturnValue','fpheld','bPickA')
    b.fn('ease', K + 'FInterpTo', 1650, 550, Target=0.0, InterpSpeed=8.0)
    b.link('off', 'RootYawOffset', 'ease', 'Current'); b.link(e, 'DeltaSeconds', 'ease', 'DeltaTime')
    b.fn('pick', K + 'SelectFloat', 2100, 400); b.link('fpheld', 'ReturnValue', 'pick', 'A'); b.link('ease', 'ReturnValue', 'pick', 'B')
    b.link('holding', 'ReturnValue', 'pick', 'bPickA')
    b.set('setoff', 'RootYawOffset', 2600, 0); b.link('pick', 'ReturnValue', 'setoff', 'RootYawOffset')
    b.comment('Hold the body still', ['move', 'still', 'montage', 'free', 'battle', 'calm', 'hold1', 'hold2', 'feet', 'holding', 'off',
                                      'held0', 'held1', 'held', 'ease', 'pick', 'setoff'])
    b.fn('mag', K + 'Abs', 2900, 400); b.link('setoff', 'Output_Get', 'mag', 'A')
    b.fn('far', K + 'Greater_DoubleDouble', 3100, 400, B=50.0); b.link('mag', 'ReturnValue', 'far', 'A')
    b.fn('wants', K + 'BooleanAND', 3300, 450); b.link('far', 'ReturnValue', 'wants', 'A'); b.link('holding', 'ReturnValue', 'wants', 'B')
    b.set('setwants', 'WantsTurn', 3500, 0); b.link('wants', 'ReturnValue', 'setwants', 'WantsTurn')
    b.set('setlast', 'LastActorYaw', 3800, 0); b.link('yaw', 'Yaw', 'setlast', 'LastActorYaw')
    b.set('setturn', 'LastTurnYaw', 4100, 0); b.link('curve', 'ReturnValue', 'setturn', 'LastTurnYaw')
    b.fn('now', '/Script/Engine.KismetSystemLibrary:GetGameTimeInSeconds', 3800, 700)
    b.get('latch', 'TurnLatchUntil', 3800, 850)
    b.fn('open', K + 'Greater_DoubleDouble', 4100, 700); b.link('now', 'ReturnValue', 'open', 'A'); b.link('latch', 'TurnLatchUntil', 'open', 'B')
    b.fn('go', K + 'BooleanAND', 4300, 600); b.link('wants', 'ReturnValue', 'go', 'A'); b.link('open', 'ReturnValue', 'go', 'B')
    b.node('which', 'branch', 4400, 0); b.link('go', 'ReturnValue', 'which', 'Condition')
    b.fn('big0', K + 'GreaterEqual_DoubleDouble', 4400, 1000, B=135.0); b.link('mag', 'ReturnValue', 'big0', 'A')
    b.fn('big', K + 'SelectInt', 4650, 1000, A=2, B=0); b.link('big0', 'ReturnValue', 'big', 'bPickA')
    b.fn('right0', K + 'Less_DoubleDouble', 4400, 1200, B=0.0); b.link('setoff', 'Output_Get', 'right0', 'A')
    b.fn('right', K + 'SelectInt', 4650, 1200, A=1, B=0); b.link('right0', 'ReturnValue', 'right', 'bPickA')
    b.fn('idx', K + 'Add_IntInt', 4900, 1100); b.link('big', 'ReturnValue', 'idx', 'A'); b.link('right', 'ReturnValue', 'idx', 'B')
    b.set('setidx', 'TurnIndex', 5100, 0); b.link('idx', 'ReturnValue', 'setidx', 'TurnIndex')
    b.fn('until', K + 'Add_DoubleDouble', 5100, 700, B=2.2); b.link('now', 'ReturnValue', 'until', 'A')
    b.set('setlatch', 'TurnLatchUntil', 5400, 0); b.link('until', 'ReturnValue', 'setlatch', 'TurnLatchUntil')
    b.chain(e, 'setoff', 'setwants', 'setlast', 'setturn', 'which', 'setidx', 'setlatch')
    b.comment('Choose the turn', ['mag', 'far', 'wants', 'setwants', 'setlast', 'setturn', 'now', 'latch', 'open', 'go', 'which',
                                  'big0', 'big', 'right0', 'right', 'idx', 'setidx', 'until', 'setlatch'])
    b.run()


{'functions': functions, 'update': update, 'turn': turn}[sys.argv[1]]()
