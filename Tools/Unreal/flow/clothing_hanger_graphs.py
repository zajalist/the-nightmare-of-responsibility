"""Director-owned extraction hand: existing floor kneel, measured pinch, real hanger.

Called by build_clothing_chase under its lease. No Player or animation asset edits.
An owned narrower capsule fits the kneeling body into the measured 72cm gap.
Return to the original safe standing transform before restoring capsule width.
Actual shoulder/wrist/skin clearance must be measured in the chase proof.
"""
import json
from pathlib import Path
from build_clothing_search import P,C,K,GS,KS,A,ROOM,fresh,finish
from build_clothing_inspection import PLAYER,SC
from clothing_chase_contract import SNAG,PULL_DISTANCE
# level1 (2026-11-17): the kneel stands 26 cm to his left of the snag, so the right hand works and pulls outside his
# right knee; at the snag's own x the hand ran back between his knees (the user's "arm goes behind the leg").
# level1 (2026-11-18): 40 cm, not 26: at 26 the hanger's wire still crossed his right knee and shin (hanger_stance.py).
STANCE_X=SNAG[0]-40.0
MH='/Game/FoA/Characters/Player/ABP_FoAPlayer_MH.ABP_FoAPlayer_MH_C'
SRC='/Game/FoA/Characters/Player/ABP_FoAPlayer.ABP_FoAPlayer_C'
DATA=json.loads(Path(__file__).with_name('clothing_hanger_contact.json').read_text())
HANGER='/Game/FoA/Lux3D/wire_hanger/SM_Lux3D_WireHanger.SM_Lux3D_WireHanger'
def vec(v):return ','.join(map(str,v))
def pawn(b):
    b.fn('pawn',GS+'GetPlayerPawn',0,600,PlayerIndex=0)
    b.node('cast','cast',300,0,class_path=PLAYER);b.link('pawn','ReturnValue','cast','Object')
def pinch(b,x=0):
    b.fn('pinchrot',K+'MakeRotator',x,1200,**DATA['pinch']['rotation_degrees'])
    b.fn('pinch',K+'MakeTransform',x+300,1200,Location=vec(DATA['pinch']['location']),Scale=vec(DATA['pinch']['scale']))
    b.link('pinchrot','ReturnValue','pinch','Rotation')

def build():
    b,e=fresh('StartClothingHanger');pawn(b);b.chain(e,'cast')
    b.fn('home',A+'GetTransform',300,700);b.link('cast','AsBP Fo APlayer','home','self')
    b.set('savehome','ClothingHangerHome',400,0);b.link('home','ReturnValue','savehome','ClothingHangerHome')
    b.get('capsule','CapsuleComponent',300,900,'/Script/Engine.Character');b.link('cast','AsBP Fo APlayer','capsule','self')
    b.fn('radius','/Script/Engine.CapsuleComponent:GetUnscaledCapsuleRadius',600,900);b.link('capsule','CapsuleComponent','radius','self')
    b.set('saveradius','ClothingHangerRadius',500,0);b.link('radius','ReturnValue','saveradius','ClothingHangerRadius')
    b.set('owned','bClothingHangerOwned',600,0);b.pin('owned','bClothingHangerOwned','true')
    b.fn('narrow','/Script/Engine.CapsuleComponent:SetCapsuleRadius',750,0,Radius=28,bUpdateOverlaps=True);b.link('capsule','CapsuleComponent','narrow','self')
    b.fn('stance',A+'K2_TeleportTo',900,0,DestLocation=f'{STANCE_X:.3f},-95,87.15',DestRotation='0,-90,0');b.link('cast','AsBP Fo APlayer','stance','self')
    b.node('placed','branch',1000,0);b.link('stance','ReturnValue','placed','Condition')
    b.fn('room',GS+'GetActorOfClass',1000,2200,ActorClass=ROOM)
    b.get('fill','ClueBedFill',1300,2200,ROOM);b.link('room','ReturnValue','fill','self')
    b.fn('light',SC+'SetVisibility',1100,0,bNewVisibility=True,bPropagateToChildren=False);b.link('fill','ClueBedFill','light','self')
    b.fn('failed',C+':CancelClothingInspection',1000,-350);b.link('placed','else','failed','execute')
    b.get('mesh','Mesh',900,600,PLAYER);b.link('cast','AsBP Fo APlayer','mesh','self')
    b.fn('anim','/Script/Engine.SkeletalMeshComponent:GetAnimInstance',1200,600);b.link('mesh','Mesh','anim','self')
    b.fn('kneel','/Script/Engine.AnimInstance:PlaySlotAnimationAsDynamicMontage',1200,0,
        Asset='/Game/FoA/Characters/Player/Anims/UAL/UAL_Fixing_Kneeling.UAL_Fixing_Kneeling',SlotNodeName='DefaultSlot',
        BlendInTime=.35,BlendOutTime=.35,InPlayRate=1,LoopCount=20,BlendOutTriggerTime=-1,InTimeToStartMontageAt=0)
    b.link('anim','ReturnValue','kneel','self')
    b.set('montage','ClothingHangerMontage',1500,0);b.link('kneel','ReturnValue','montage','ClothingHangerMontage')
    b.fn('meshrot',K+'MakeRotator',1500,900,**DATA['mesh_relative_rotation'])
    b.fn('meshxf',K+'MakeTransform',1800,900,Location=vec(DATA['mesh_relative_location']),Scale='1,1,1');b.link('meshrot','ReturnValue','meshxf','Rotation')
    b.fn('held',PLAYER+':SetHeldTool',1800,0,Mesh=HANGER,bShow='true');b.link('cast','AsBP Fo APlayer','held','self');b.link('meshxf','ReturnValue','held','MeshTransform')
    pinch(b,2100)
    b.get('grip','HeldToolGrip',2100,600,PLAYER);b.link('cast','AsBP Fo APlayer','grip','self')
    b.fn('pinchframe',SC+'K2_SetRelativeTransform',2400,0,bTeleport='true');b.link('grip','HeldToolGrip','pinchframe','self');b.link('pinch','ReturnValue','pinchframe','NewTransform')
    b.node('source','cast',2700,0,class_path=SRC);b.link('anim','ReturnValue','source','Object')
    b.set('keygrip','KeyGrip',3000,0,SRC);b.link('source','AsABP Fo APlayer','keygrip','self');b.pin('keygrip','KeyGrip','true')
    b.set('fingers','GripWeight',3300,0,SRC);b.link('source','AsABP Fo APlayer','fingers','self');b.pin('fingers','GripWeight',1)
    b.chain('cast','savehome','saveradius','owned','narrow','stance','placed','room','light','kneel','montage','held','pinchframe','source','keygrip','fingers')
    finish(b,'Kneel and grip hanger')

    b,e=fresh('UpdateClothingHanger');b.get('owned','bClothingHangerOwned',0,300)
    b.node('guard','branch',300,0);b.link('owned','bClothingHangerOwned','guard','Condition');b.chain(e,'guard');pawn(b);b.chain('guard','cast')
    b.fn('now',GS+'GetTimeSeconds',600,600);b.get('started','ClothingFlightStarted',600,800)
    b.fn('elapsed',K+'Subtract_DoubleDouble',900,600);b.link('now','ReturnValue','elapsed','A');b.link('started','ClothingFlightStarted','elapsed','B')
    b.fn('settle',K+'Subtract_DoubleDouble',1200,600,B=.6);b.link('elapsed','ReturnValue','settle','A')
    b.fn('alpha',K+'Divide_DoubleDouble',1500,600,B=1.2);b.link('settle','ReturnValue','alpha','A')
    b.fn('clamp',K+'FClamp',1800,600,Min=0,Max=1);b.link('alpha','ReturnValue','clamp','Value')
    b.fn('retreat',K+'Multiply_DoubleDouble',2100,600,B=0);b.link('clamp','ReturnValue','retreat','A')
    b.fn('y',K+'Add_DoubleDouble',2400,600,B=-95);b.link('retreat','ReturnValue','y','A')
    b.fn('bodypoint',K+'MakeVector',2700,600,X=round(STANCE_X,3),Z=87.15);b.link('y','ReturnValue','bodypoint','Y')
    b.fn('bodymove',A+'K2_SetActorLocation',600,0,bSweep='true',bTeleport='true');b.link('cast','AsBP Fo APlayer','bodymove','self');b.link('bodypoint','ReturnValue','bodymove','NewLocation')
    b.fn('distance',K+'Multiply_DoubleDouble',2100,900,B=PULL_DISTANCE);b.link('clamp','ReturnValue','distance','A')
    b.fn('hooky',K+'Add_DoubleDouble',2400,900,B=SNAG[1]);b.link('distance','ReturnValue','hooky','A')
    b.fn('flicktime',K+'Subtract_DoubleDouble',2100,1700,B=1.8);b.link('elapsed','ReturnValue','flicktime','A')
    b.fn('flickspeed',K+'Divide_DoubleDouble',2400,1700,B=.18);b.link('flicktime','ReturnValue','flickspeed','A')
    b.fn('flick',K+'FClamp',2700,1700,Min=0,Max=1);b.link('flickspeed','ReturnValue','flick','Value')
    b.fn('flickback',K+'Multiply_DoubleDouble',3000,1700,B=4);b.link('flick','ReturnValue','flickback','A')
    b.fn('handy',K+'Add_DoubleDouble',3300,1700);b.link('hooky','ReturnValue','handy','A');b.link('flickback','ReturnValue','handy','B')
    b.fn('raise',K+'Multiply_DoubleDouble',2100,1900,B=12);b.link('clamp','ReturnValue','raise','A')
    b.fn('flickup',K+'Multiply_DoubleDouble',3000,1900,B=10);b.link('flick','ReturnValue','flickup','A')
    b.fn('raised',K+'Add_DoubleDouble',3300,1900);b.link('raise','ReturnValue','raised','A');b.link('flickup','ReturnValue','raised','B')
    b.fn('handz',K+'Add_DoubleDouble',3600,1900,B=SNAG[2]);b.link('raised','ReturnValue','handz','A')
    b.fn('hook',K+'MakeVector',2700,900,X=SNAG[0]);b.link('handy','ReturnValue','hook','Y');b.link('handz','ReturnValue','hook','Z')
    b.fn('grippoint',K+'Add_VectorVector',3000,900,B=vec(DATA['hook_to_grip_world']));b.link('hook','ReturnValue','grippoint','A')
    b.fn('griprot',K+'MakeRotator',3000,1100,**DATA['grip_world_rotation'])
    b.fn('worldgrip',K+'MakeTransform',3300,900,Scale='1,1,1');b.link('grippoint','ReturnValue','worldgrip','Location');b.link('griprot','ReturnValue','worldgrip','Rotation')
    pinch(b,3300)
    b.fn('inverse',K+'InvertTransform',3900,1200);b.link('pinch','ReturnValue','inverse','T')
    b.fn('hand',K+'ComposeTransforms',4200,900);b.link('inverse','ReturnValue','hand','A');b.link('worldgrip','ReturnValue','hand','B')
    b.fn('parts',K+'BreakTransform',4500,900);b.link('hand','ReturnValue','parts','InTransform')
    b.get('body','Body',900,1500,PLAYER);b.link('cast','AsBP Fo APlayer','body','self')
    b.fn('anim','/Script/Engine.SkeletalMeshComponent:GetAnimInstance',1200,1500);b.link('body','Body','anim','self')
    b.node('retarget','cast',900,0,class_path=MH);b.link('anim','ReturnValue','retarget','Object');b.chain('cast','bodymove','retarget')
    b.set('target','ToolHandTarget',1200,0,MH);b.link('retarget','AsABP Fo APlayer MH','target','self');b.link('parts','Location','target','ToolHandTarget')
    b.fn('pole',K+'Add_VectorVector',4800,900,B='24,20,-5');b.link('parts','Location','pole','A')
    b.set('elbow','ToolElbowTarget',1500,0,MH);b.link('retarget','AsABP Fo APlayer MH','elbow','self');b.link('pole','ReturnValue','elbow','ToolElbowTarget')
    b.set('weight','ToolHandWeight',1800,0,MH);b.link('retarget','AsABP Fo APlayer MH','weight','self');b.pin('weight','ToolHandWeight',1)
    b.set('rotation','HeldToolRotation',2100,0,MH);b.link('retarget','AsABP Fo APlayer MH','rotation','self');b.link('parts','Rotation','rotation','HeldToolRotation')
    b.set('rotateweight','HeldToolWeight',2400,0,MH);b.link('retarget','AsABP Fo APlayer MH','rotateweight','self');b.pin('rotateweight','HeldToolWeight',1)
    b.chain('retarget','target','elbow','weight','rotation','rotateweight')
    b.ops.extend([dict(op='move',node_id=e,x=-400,y=0),dict(op='move',node_id='guard',x=0,y=0)])
    finish(b,'Pull with hanger')

    b,e=fresh('ClearClothingHanger');b.get('owned','bClothingHangerOwned',0,300)
    b.node('guard','branch',300,0);b.link('owned','bClothingHangerOwned','guard','Condition');b.chain(e,'guard');pawn(b);b.chain('guard','cast')
    b.set('off','bClothingHangerOwned',600,0);b.pin('off','bClothingHangerOwned','false')
    b.get('montage','ClothingHangerMontage',600,600)
    b.fn('valid',KS+'IsValid',600,900);b.link('montage','ClothingHangerMontage','valid','Object')
    b.node('hasmontage','branch',750,0);b.link('valid','ReturnValue','hasmontage','Condition')
    b.get('mesh','Mesh',900,700,PLAYER);b.link('cast','AsBP Fo APlayer','mesh','self')
    b.fn('anim','/Script/Engine.SkeletalMeshComponent:GetAnimInstance',900,850);b.link('mesh','Mesh','anim','self')
    # QA B2 (2026-11-10): stop the kneel at once, under the return dip; a 0.35 s blend-out moved his first-person view
    b.fn('stop','/Script/Engine.AnimInstance:Montage_Stop',900,0,InBlendOutTime=0.0);b.link('anim','ReturnValue','stop','self');b.link('montage','ClothingHangerMontage','stop','Montage')
    b.fn('release',PLAYER+':SetToolHandTarget',1200,0,Weight=0);b.link('cast','AsBP Fo APlayer','release','self')
    b.fn('hide',PLAYER+':SetHeldTool',1500,0,bShow='false');b.link('cast','AsBP Fo APlayer','hide','self')
    b.node('source','cast',1800,0,class_path=SRC);b.link('anim','ReturnValue','source','Object')
    b.set('keygrip','KeyGrip',2100,0,SRC);b.link('source','AsABP Fo APlayer','keygrip','self');b.pin('keygrip','KeyGrip','false')
    # QA B2 + T7 proof (2026-11-10): back where he started the unhook when that was the floor (z < 100), else (105,-110),
    # floor that stays standable with the wardrobe down (t7_geometry.json); either way facing the shirt's first landing.
    b.fn('standrot',K+'MakeRotator',2100,1200,Roll=0,Pitch=0,Yaw=139)
    b.fn('fixed',K+'MakeTransform',2300,1100,Location='105,-110,89',Scale='1,1,1');b.link('standrot','ReturnValue','fixed','Rotation')
    b.get('home','ClothingHangerHome',2100,1500);b.fn('homeparts',K+'BreakTransform',2300,1500);b.link('home','ClothingHangerHome','homeparts','InTransform')
    b.fn('homez',K+'BreakVector',2500,1500);b.link('homeparts','Location','homez','InVec')
    b.fn('onfloor',K+'Less_DoubleDouble',2700,1500,B=100.0);b.link('homez','Z','onfloor','A')
    b.fn('chosen',K+'SelectTransform',2900,1300);b.link('home','ClothingHangerHome','chosen','A');b.link('fixed','ReturnValue','chosen','B');b.link('onfloor','ReturnValue','chosen','bPickA')
    b.fn('returnhome',A+'K2_SetActorTransform',2400,0,bSweep=False,bTeleport=True);b.link('cast','AsBP Fo APlayer','returnhome','self')
    b.fn('chosenparts',K+'BreakTransform',3100,1300);b.link('chosen','ReturnValue','chosenparts','InTransform')
    b.fn('landing',K+'MakeVector',3100,1500,X=110.7,Y=-76.4,Z=38.5)
    # level1 (2026-11-17): look from his eyes at the landed shirt (pitch clamped -60..-15); a fixed -25 looked over it
    b.fn('eye',K+'Add_VectorVector',3350,1450,B='0,0,70');b.link('chosenparts','Location','eye','A')
    b.fn('toshirt',K+'FindLookAtRotation',3300,1300);b.link('eye','ReturnValue','toshirt','Start');b.link('landing','ReturnValue','toshirt','Target')
    b.fn('yaw',K+'BreakRotator',3500,1300);b.link('toshirt','ReturnValue','yaw','InRot')
    b.fn('pitch',K+'FClamp',3600,1450,Min=-60,Max=-15);b.link('yaw','Pitch','pitch','Value')
    b.fn('viewrot',K+'MakeRotator',3700,1300,Roll=0);b.link('yaw','Yaw','viewrot','Yaw');b.link('pitch','ReturnValue','viewrot','Pitch')
    # level1: the body faces the shirt too; the first-person view is held within 60 deg of the torso, so a body still
    # facing the bed clamped the turn to the shirt (yaw 31 instead of 107 in PIE)
    b.fn('facerot',K+'MakeRotator',3600,1650,Roll=0,Pitch=0);b.link('yaw','Yaw','facerot','Yaw')
    b.fn('facexf',K+'MakeTransform',3850,1650,Scale='1,1,1');b.link('chosenparts','Location','facexf','Location');b.link('facerot','ReturnValue','facexf','Rotation')
    b.link('facexf','ReturnValue','returnhome','NewTransform')
    b.fn('pc',GS+'GetPlayerController',2500,1700,PlayerIndex=0)
    b.fn('face','/Script/Engine.Controller:SetControlRotation',2550,0);b.link('pc','ReturnValue','face','self');b.link('viewrot','ReturnValue','face','NewRotation')
    b.get('capsule','CapsuleComponent',2400,700,'/Script/Engine.Character');b.link('cast','AsBP Fo APlayer','capsule','self')
    b.get('radius','ClothingHangerRadius',2400,900)
    b.fn('restorewidth','/Script/Engine.CapsuleComponent:SetCapsuleRadius',2700,0,bUpdateOverlaps=True);b.link('capsule','CapsuleComponent','restorewidth','self');b.link('radius','ClothingHangerRadius','restorewidth','Radius')
    b.fn('room',GS+'GetActorOfClass',3000,0,ActorClass=ROOM)
    b.get('fill','ClueBedFill',3000,700,ROOM);b.link('room','ReturnValue','fill','self')
    b.fn('lightoff',SC+'SetVisibility',3300,0,bNewVisibility=False,bPropagateToChildren=False);b.link('fill','ClueBedFill','lightoff','self')
    b.chain('cast','off','hasmontage','stop','release','hide','source','keygrip','returnhome','face','restorewidth');b.link('hasmontage','else','release','execute')
    b.link('source','CastFailed','returnhome','execute')
    b.chain('restorewidth','room','lightoff')
    b.ops.extend([dict(op='move',node_id=e,x=-400,y=0),dict(op='move',node_id='guard',x=0,y=0)])
    for i,ref in enumerate(('hasmontage','stop','release','hide','source','keygrip','returnhome','restorewidth','room','lightoff')):
        b.ops.append(dict(op='move',node_id=ref,x=950+400*i,y=0))
    finish(b,'Restore player and hands')
