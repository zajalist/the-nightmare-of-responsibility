"""Authored chase contract shared by Director builder/proof fixtures.

Every flight is entered by a real interaction contact, not proximity or a timer.
The player walks to the stationary shirt between attempts. Inventory is untouched
until the vase presentation signals ClothingBossFormed.
"""
SNAG=(269.758846282959,-150.86858081817624,4.687624835968017)
PULL_DISTANCE=40.0
EXTRACT_CLEAR=(SNAG[0],SNAG[1]+PULL_DISTANCE,SNAG[2]+12)
LANDINGS=((110.6763772964477,-76.36858081817627,38.48026657104492),
          (-50.,-160.,38.48026657104492),(-55.,-335.,38.48026657104492))  # [2] the bay floor below the windowsill vase (2026-11-09)
# [1] moved 55 cm west onto the moonlit floor patch (2026-11-10, QA B2 readability): the escape-one shot sees the dark
# shirt land against lit boards. level1 (2026-11-18): back 25 cm east (-75 -> -50): at -75 the pick-up bent his camera
# into the west curtain (chase_landing.py)
# The final reach and the rising figure are filmed from inside the bay: the room's ClueViewVase/ClueViewBoss markers
# looked through the closed bay curtain (Saved/StoryShots/bay_views.json: clear traces, no wall, no curtain crossing).
VASE_VIEW,VASE_FOCUS=(-130.,-330.,140.),(-15.,-365.,60.)   # the sill vase and the floor where it lands
BOSS_VIEW,BOSS_FOCUS=(-170.,-315.,170.),(-15.,-345.,85.)   # wider, as the sand figure rises
# QA B2 audit (2026-11-10): the camera takes HIS side of the bay so his body stays out of view: east when he stands at
# x > SIDE_SPLIT_X, else the west views above. Both east points passed the bay_views.json traces.
VASE_VIEW_EAST,BOSS_VIEW_EAST,SIDE_SPLIT_X=(40.,-330.,140.),(40.,-330.,170.),-90.
STAGES={4:'snagged',5:'first_reach',6:'second_reach',7:'final_reach',8:'vase_forming',9:'boss_ready'}
CONTACTS={5:'ClothingReachOne',6:'ClothingReachTwo',7:'ClothingReachFinal'}
STATES={5:'ChaseOne',6:'ChaseTwo',7:'ChaseFinal'}
TIMING=dict(kneel_settle=.6,underbed_pull=1.2,toss=.85,escape=.95,
            vase_shatter=.65,vase_to_boss_shot=.9,boss_callback=3.8)
VASE_CALLBACK='ClothingBossFormed'
VASE_FUNCTION='BreakVaseThenBoss'
# All three stationary landings passed the real scanner/E route. Cinematic
# composition is tracked separately in Saved/Integration/clothing_visual_review.json.
GEOMETRY_VERIFIED=(True,True,True)
