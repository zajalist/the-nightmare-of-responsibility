"""Compact reused job-stop sets. Coordinates are centimetres in one isolated runtime stage."""
ROOT='/Game/FoA/Level2/Journey'
BP=ROOT+'/BP_L2StopSet'
ORIGIN=(0,-140000,0)
ACTION_SECONDS=1.4
PREVIEW_SECONDS=1.25
FADE_SECONDS=.3
GROUPS=('Career','Grocery','Office')
CUBE='/Engine/BasicShapes/Cube'
PLANE='/Engine/BasicShapes/Plane'
TABLE='/Game/FoA/Props/wooden_table_02/wooden_table_02_1k/StaticMeshes/wooden_table_02_1k'
CHAIR='/Game/FoA/Props/painted_wooden_chair_01/painted_wooden_chair_01_1k/StaticMeshes/painted_wooden_chair_01_1k'
BED='/Game/FoA/Props/old_bed_frame/old_bed_frame_1k/StaticMeshes/old_bed_frame_1k'
BEDDING='/Game/FoA/Lux3D/bedding_fixed/SM_Lux3D_Bedding'
BEDDING_MAT='/Game/FoA/Lux3D/bedding_fixed/MI_Lux3D_Bedding'
CYLINDER='/Engine/BasicShapes/Cylinder'
PAINT='/Game/FoA/Materials/MI_Trim_Paint'
LAMP='/Game/FoA/Props/desk_lamp_arm_01/desk_lamp_arm_01_1k/StaticMeshes/desk_lamp_arm_01_1k'
JUG='/Game/FoA/Props/jug_01/jug_01_1k/StaticMeshes/jug_01_1k'
CRATE='/Game/FoA/Props/wooden_crate_01/wooden_crate_01_2k/StaticMeshes/wooden_crate_01'
CHEESE='/Game/FoA/Props/CheeseBox_01/CheeseBox_01_1k/StaticMeshes/CheeseBox_01'
POT='/Game/FoA/Props/potted_plant_04/potted_plant_04_1k/StaticMeshes/potted_plant_04_pot'
PLANT='/Game/FoA/Props/potted_plant_04/potted_plant_04_1k/StaticMeshes/potted_plant_04_plant'
PAPER='/Game/FoA/Props/book_encyclopedia_set_01/book_encyclopedia_set_01_2k/Materials/book_encyclopedia_set_01_paper'
WALL='/Game/FoA/Materials/MI_Wall_Plaster'
FLOOR='/Game/FoA/Materials/MI_Floor_OldWood'
METAL='/Game/FoA/Materials/MI_Metal'
DARK='/Game/FoA/Level2/Drive/MI_L2Dark'
GLASS='/Game/FoA/Materials/M_Glass'
MANNY='/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'
SAND=ROOT+'/M_L2MergeShell'
SIT='/Game/FoA/Characters/Player/Anims/UAL/UAL_Sitting_Idle_Loop'
PICKUP='/Game/FoA/Characters/Player/Montages/AM_FoA_PickUp_Table'

# name, parent, mesh, centre-on-ground, target xyz dimensions, optional material.
# Fit copies only; source assets and bedroom actor transforms are never changed.
MESHES=[
 ('Floor','Root',CUBE,(80,0,-20),(1000,900,20),FLOOR),
 ('BackWall','Root',CUBE,(575,0,0),(20,900,320),WALL),
 ('FrontWall','Root',CUBE,(-415,0,0),(20,900,320),WALL),
 ('WallLeft','Root',CUBE,(80,-450,0),(1000,20,320),WALL),
 ('WallRight','Root',CUBE,(80,450,0),(1000,20,320),WALL),
 ('Ceiling','Root',CUBE,(80,0,320),(1000,900,15),WALL),
 ('CareerCounter','Career',TABLE,(150,0,0),(110,230,76),None),
 ('CareerGlass','Career',PLANE,(130,0,90),(1,215,155),GLASS),
 ('GlassPostLeft','Career',CUBE,(130,-111,76),(4,4,172),METAL),
 ('GlassPostRight','Career',CUBE,(130,111,76),(4,4,172),METAL),
 ('GlassTop','Career',CUBE,(130,0,244),(4,226,4),METAL),
 ('ServingBoard','Career',CUBE,(128,0,218),(2,222,26),DARK),
 ('TicketTray','Career',CUBE,(73,-52,76),(28,23,3),DARK),
 ('Ticket','Career',CUBE,(71,-52,79),(16,11,.2),PAPER),
 ('WaitingChair0','Career',CHAIR,(-130,190,0),(48,50,90),None),
 ('WaitingChair1','Career',CHAIR,(-130,285,0),(48,50,90),None),
 ('ClerkChair','Career',CHAIR,(290,0,0),(48,50,90),None),
 ('GroceryShelf','Grocery',CUBE,(154,0,0),(66,360,6),METAL),
 ('ShelfTop','Grocery',CUBE,(154,0,174),(66,360,5),METAL),
 ('ShelfMiddle','Grocery',CUBE,(154,0,91),(66,360,4),METAL),
 ('ShelfLeft','Grocery',CUBE,(154,-180,0),(66,4,180),METAL),
 ('ShelfRight','Grocery',CUBE,(154,180,0),(66,4,180),METAL),
 ('ShelfBack','Grocery',CUBE,(188,0,0),(4,360,180),WALL),
 ('AisleBoard','Grocery',CUBE,(154,0,192),(2,360,44),DARK),
 ('JobBoard','Grocery',CUBE,(114,-245,95),(3,100,100),PAINT),
 ('OfficeBed','Office',BED,(-25,175,0),(210,100,58),None),
 ('OfficeBedding','Office',BEDDING,(-25,175,42),(194,94,16),BEDDING_MAT),
 ('OfficeDesk','Office',TABLE,(300,0,0),(120,300,76),None),
 ('OfficeChair','Office',CHAIR,(410,0,0),(48,50,90),None),
 ('OfficePaper','Office',CUBE,(252,-15,76),(30,21,.2),PAPER),
]
# Repeated retail facings at plausible human scale: rice cartons, tea tins,
# oat cartons. Preserve the three named action/label components.
for i,y in enumerate((-105,0,105)):
    shape=CYLINDER if i==1 else CUBE
    size=(26,26,38) if i==1 else (24,38,46)
    MESHES += [('Stock'+str(i),'Grocery',shape,(140,y,95),size,PAINT),
               ('Label'+str(i),'Grocery',CUBE,(116,y,86),(1,58,9),PAPER)]
    for j,offset in enumerate((-37,37)):
        MESHES.append((f'Facing{i}_{j}','Grocery',shape,(147,y+offset,95),(20,24,32),PAINT))
    MESHES.append((f'LowerJug{i}','Grocery',JUG,(146,y,8),(30,30,48),None))
    MESHES.append((f'TopTin{i}','Grocery',CYLINDER,(153,y,179),(25,25,28),METAL))

# Architectural anchors and foreground props belong to each stop, not the shared
# shell. OfficeDressing is hidden wholesale when the separate interview starts.
EXTRA_GROUPS=(('OfficeDressing','Office'),)
MESHES += [
 ('CareerCounterFront','Career',CUBE,(100,0,0),(9,230,70),PAINT),
 ('CareerCounterPlinth','Career',CUBE,(96,0,0),(12,232,12),DARK),
 ('CareerIdentity','Career',CUBE,(540,10,62),(8,720,195),DARK),
 ('CareerNoticeBoard','Career',CUBE,(125,235,116),(5,140,100),DARK),
 ('CareerNoticePaper','Career',CUBE,(121,235,126),(2,119,80),PAPER),
 ('CareerLamp','Career',LAMP,(190,-80,76),(35,28,55),None),
 ('CareerPot','Career',POT,(455,-260,0),(44,44,48),None),
 ('CareerPlant','Career',PLANT,(455,-260,42),(70,70,110),None),
 ('CareerForms','Career',CUBE,(180,60,76),(35,30,3),PAPER),
 ('GroceryCrate','Grocery',CRATE,(118,255,0),(70,70,58),None),
 ('GroceryCheese','Grocery',CHEESE,(115,253,58),(38,38,15),None),
 ('GroceryWallBand','Grocery',CUBE,(555,0,110),(5,840,64),DARK),
 ('GroceryBackRack','Grocery',CUBE,(440,40,0),(70,500,90),PAINT),
 ('GroceryBackTop','Grocery',CUBE,(435,40,90),(84,510,6),METAL),
 ('GroceryBackCrate0','Grocery',CRATE,(430,-100,96),(60,72,44),None),
 ('GroceryBackCrate1','Grocery',CRATE,(430,70,96),(60,72,44),None),
 ('OfficeReceptionFront','OfficeDressing',CUBE,(242,0,0),(12,305,70),DARK),
 ('OfficeReceptionTop','OfficeDressing',CUBE,(300,0,75),(126,310,1),PAINT),
 ('OfficeIdentity','OfficeDressing',CUBE,(550,0,50),(8,650,205),DARK),
 ('OfficeLamp','OfficeDressing',LAMP,(300,-100,76),(36,30,55),None),
 ('OfficePot','OfficeDressing',POT,(470,280,0),(48,48,48),None),
 ('OfficePlant','OfficeDressing',PLANT,(470,280,42),(80,80,125),None),
 ('OfficeRunner','OfficeDressing',CUBE,(50,0,.3),(470,380,.5),DARK),
]
for group in GROUPS:
    for i,y in enumerate((-435,435)):
        MESHES.append((group+'Skirting'+str(i),'OfficeDressing' if group=='Office' else group,CUBE,(80,y,0),(970,8,16),DARK))


# TextRender signs are physical objects, not HUD decoration. Camera-facing -X.
SIGNS=[
 ('Serving','Career','NOW SERVING 17',(125,0,231),12),
 ('TicketNumber','Ticket','18',(-.55,0,0),3),
 ('AddressNotice','Career','LOCAL VACANCIES\n\nAll-Night Grocery\nOffice tower',(119,235,168),10),
 ('Aisle9A','Grocery','09',(150,-132,214),26),
 ('Aisle9B','Grocery','PANTRY',(150,42,214),20),
 ('JobNotice','Grocery','Stocking.\nSorting.\nInventory.',(110,-245,145),12),
 ('OfficeNoLift','OfficeDressing','RECEPTION',(544,0,226),27),
 ('CareerTitle','Career','EMPLOYMENT SERVICES',(534,10,230),26),
 ('CareerSubtitle','Career','Applications and advice',(534,10,195),12),
 ('OfficeDirection','OfficeDressing','Office tower lobby',(544,0,188),13),
 ('GroceryTitle','Grocery','ALL-NIGHT GROCERY',(550,0,145),23),
]
STOCK_NAMES=('Rice','Tea','Oats')
for i,(name,y) in enumerate(zip(STOCK_NAMES,(-105,0,105))):
    SIGNS.append(('LabelText'+str(i),'Label'+str(i),name,(-.55,0,0),5))
    SIGNS.append(('StockText'+str(i),'Grocery',name,(126,y,120),8))
WHITE_SIGNS={'Serving','Aisle9A','Aisle9B','OfficeNoLift','OfficeDirection','CareerTitle','CareerSubtitle','GroceryTitle'}
STAFF=('Clerk','Supervisor','Receptionist')
FIGURES=[('Waiting0','Career',(-130,190,0),-90),('Waiting1','Career',(-130,285,0),-90),
         ('Clerk','Career',(245,0,0),180),('Receptionist','Office',(390,15,0),180),
         ('Supervisor','Grocery',(265,-335,0),180)]
ENTRY=((15,-52,88),(25,0,88),(-25,60,88))
ENTRY_YAW=(0,0,90)
SEATED=(-25,112,98)
SEATED_YAW=-90
ENCOUNTER=(300,0,0)
CAMERAS={
 0:((-285,-335,188),(-6,34,0)),
 1:((-115,-215,155),(-10,42,0)),
 2:((280,-290,182),(-12,137,0)),
 3:((-295,-320,178),(-5,42,0)),
}
# Per-stop establishing shots share the same action state, with deliberate
# face-height framing instead of the same empty room seen three times.
STOP_CAMERAS={0:((-250,-280,176),(-4,31,0)),
              1:((-245,-325,178),(-5,25,0)),
              2:((-280,-310,177),(-4,35,0))}
# The old shared writing shot was behind the grocery rack, filling the frame
# with its back. Keep writing views on the customer side of each fixture.
WRITER_CAMERAS={0:((-155,-280,178),(-5,39,0)),
                1:((-170,-285,176),(-7,40,0)),
                2:CAMERAS[2]}
CAMERA_FOV=60
# L2 uses manual exposure with physical-camera exposure disabled (near EV0).
# Tens of lumens match the existing player QA lighting; real-room thousands
# overexpose this pipeline. Preserve the three pools without changing shared PP.
LIGHTS=(
 ('Key',(-220,-230,275),(-48,42,0),32),
 ('Fill',(0,310,265),(-48,-90,0),18),
 ('CounterFill',(40,-100,225),(-18,17,0),25),
)
LABEL_ROLL=(-18,14,-11)
LABEL_DELAY=.35
LABEL_SPACING=.2
LABEL_BLEND=.35


def label_roll(index,age):
    alpha=max(0.,min(1.,(age-LABEL_DELAY-LABEL_SPACING*index)/LABEL_BLEND))
    return LABEL_ROLL[index]*(1-alpha)
