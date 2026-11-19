"""Data for DT_Items and DT_Interactions (mech_core). build_types.py FOA_STEP=table writes both tables from here.
Interaction rows: an interactable copies the rows whose Interactable matches its InteractionKey at BeginPlay. The first
row matching (State or None, Verb, Item) wins; a Use with the wrong item falls back to the bare-hand row. Requires names
a GI_FoA knowledge flag that must be set for the row to match, so later-day rows go above the day-one row.
Verbs: Look, Take, Use, and Notify (sent by a Linked actor with its new state as the Item, or "Arrived" when this
actor's own pivot finishes moving). Text is sincere narration: no separators, no middle dots."""

M = "/Game/FoA/Characters/Player/Montages/"
GRAB_FLOOR, GRAB_TABLE = M + "AM_FoA_PickUp_Floor.AM_FoA_PickUp_Floor", M + "AM_FoA_PickUp_Table.AM_FoA_PickUp_Table"
OPEN, RATTLE = M + "AM_FoA_OpenDrawer.AM_FoA_OpenDrawer", M + "AM_FoA_TryLockedHandle.AM_FoA_TryLockedHandle"
KNEEL = M + "AM_FoA_KneelScrewdriver.AM_FoA_KneelScrewdriver"
HANGER_DOOR, HANGER_BED = M + "AM_FoA_HangerDoor.AM_FoA_HangerDoor", M + "AM_FoA_HangerBed.AM_FoA_HangerBed"  # rig lane 2026-11-11
LUX = "/Game/FoA/Lux3D"

# (row, DisplayName, LookLine, Mesh, UsedBecomes). story_text.ITEM_NAMES/ITEM_LOOKS own the text (apply_story_text.py
# patches it in); keep these in step.
ITEMS = [
    ("Key", "Door key", "The door key. I hid it from myself, and it worked.",
     f"{LUX}/door_key/SM_Lux3D_DoorKey.SM_Lux3D_DoorKey", "KeyStub"),
    ("KeyStub", "Half a key", "Half a key. The door kept the rest.",
     f"{LUX}/door_key/SM_Lux3D_DoorKey.SM_Lux3D_DoorKey", "None"),
    ("Screwdriver", "Screwdriver", "Flathead. No idea why it lives on my desk.",
     "/Game/FoA/Props/screwdriver/screwdriver_1k/StaticMeshes/screwdriver_1k.screwdriver_1k", "None"),
    ("Hanger", "Wire hanger", "Bent out of shape. Same.",
     f"{LUX}/wire_hanger/SM_Lux3D_WireHanger.SM_Lux3D_WireHanger", "None"),
    ("Shirt", "The shirt", "Mom ironed it. It's still warm.",
     f"{LUX}/the_shirt_enemy/SM_Lux3D_ShirtEnemy.SM_Lux3D_ShirtEnemy", "None"),
]


def row(key, state, verb, item="None", nxt="None", prompt="", line="", give="None", event="None", montage="",
        requires="None"):
    return {"Interactable": key, "State": state, "Verb": verb, "Item": item, "Requires": requires, "NextState": nxt,
            "Prompt": prompt, "Line": line, "Give": give, "Event": event, "Montage": montage}


def container(key, noun, open_prompt, look, opened_line, event="Searched", montage=OPEN):
    return [row(key, "None", "Look", prompt=f"Look at the {noun}", line=look),
            row(key, "Closed", "Use", nxt="Open", prompt=open_prompt, line=opened_line, event=event, montage=montage),
            row(key, "Open", "Use", nxt="Closed", prompt=f"Close the {noun}", montage=montage)]


def pickup(key, noun, item, look, taken, event="None", montage=GRAB_TABLE):
    """Hidden until its container opens, Available while it is there to take, Taken after."""
    return [row(key, "None", "Look", prompt=f"Look at the {noun}", line=look),
            row(key, "Available", "Take", nxt="Taken", prompt=f"Take the {noun}", line=taken, give=item, event=event,
                montage=montage),
            row(key, "Hidden", "Notify", "Open", nxt="Available"),
            row(key, "Available", "Notify", "Closed", nxt="Hidden")]


# T7: RefillDrawer leaves the screwdriver back on the desk but spent (LatchFreed ended its job): look only, never taken
# again. Inserted live before the first Screwdriver row by Tools/Unreal/flow/patch_spare_screwdriver.py (rows match in
# table order, so it must come before the wildcard Look row); not part of INTERACTIONS, so no index-named row shifts.
SPARE_ROW = dict(row("Screwdriver", "Spare", "Look", prompt="Look at the screwdriver", line="It's back. I didn't put it back."),
                 Name="Screwdriver_Spare_Look")


SEARCH_ROWS = [
    row("Wardrobe", "SearchWardrobe", "Use", nxt="SearchWardrobeChecked", prompt="Search the fallen wardrobe",
        event="ClothingWardrobeSearched"),
    row("Wardrobe", "SearchWardrobe", "Look", prompt="Inspect the fallen wardrobe",
        line="The good shirt was in there. Something dragged it out."),
    row("Wardrobe", "SearchWardrobeChecked", "Use", prompt="Check the broken wood",
        line="It goes toward the desk."),
    row("Wardrobe", "SearchWardrobeChecked", "Look", prompt="Inspect the broken wood",
        line="A thread. From the shirt."),
    row("Desk", "SearchDesk", "Use", nxt="SearchDeskChecked", prompt="Search among the papers",
        event="ClothingDeskSearched"),  # no reach: clue rows commit at once (story_text.ROW_FIELDS)
    row("Desk", "SearchDesk", "Look", prompt="Inspect the scattered papers",
        line="Something's under the papers."),
    row("Desk", "SearchDeskChecked", "Use", prompt="Check the trail",
        line="Under the bed. Obviously under the bed."),
    row("Desk", "SearchDeskChecked", "Look", prompt="Inspect the disturbed dust",
        line="Under the bed. Great."),
    row("Bed", "SearchBed", "Use", nxt="ClothingSnag", prompt="Search beneath the bed",
        event="ClothingBedSearched"),
    row("Bed", "SearchBed", "Look", prompt="Peer beneath the bed",
        line="The thread goes under the bed."),
    row("Bed", "ClothingSnag", "Use", "Hanger", nxt="ClothingFreed", prompt="Hook the shirt with the wire hanger",
        event="ClothingUnhooked", montage=HANGER_BED),
    row("Bed", "ClothingSnag", "Use", prompt="Reach for the shirt",
        event="ClothingTryUnhook"),
    row("Bed", "ClothingSnag", "Look", prompt="Inspect the shirt",
        line="Too far back. I need something long."),
    row("Bed", "ClothingFreed", "Use", prompt="Check beneath the bed",
        line="It's out. It's at the foot of the bed."),
    row("Bed", "ClothingFreed", "Look", prompt="Look beneath the bed",
        line="Just dust now."),
]
for _key in ("Desk", "Bed"):
    for _verb in ("Look", "Use"):
        SEARCH_ROWS.append(row(_key, "SearchWaiting", _verb, prompt="Inspect the " + _key.lower(),
                               line="Start where it was. The wardrobe."))


CHASE_ROWS=[]
for _state,_event,_prompt in [('ChaseOne','ClothingReachOne','Catch the shirt'),
    ('ChaseTwo','ClothingReachTwo','Reach for the shirt again'),
    ('ChaseFinal','ClothingReachFinal','Grab the shirt')]:
    CHASE_ROWS += [row('Shirt',_state,'Use',nxt='ChaseMoving',prompt=_prompt,event=_event,montage=GRAB_FLOOR),
                   row('Shirt',_state,'Look',prompt='Look at the shirt')]

INTERACTIONS = CHASE_ROWS + SEARCH_ROWS + (
    # ---- the bed (T2: Look at the bed) ----
    [row("Bed", "None", "Look", requires="Knows.KeyInBoot", prompt="Look at the bed",
         line="My boots are under there. The left one.", event="LookedAtBed"),
     row("Bed", "None", "Look", prompt="Look at the bed",
         line="Still warm. It'd be so easy.", event="LookedAtBed"),
     row("Bed", "None", "Use", prompt="Get back into bed", line="Five more minutes. No. Absolutely not.")]
    # ---- searching (T2, T3) ----
    + container("CommodeDrawer", "drawer", "Open the drawer", "Sock drawer. Mom rolls them into little balls.",
                "Socks. No shirt.")
    + container("WardrobeDoor", "wardrobe", "Open the wardrobe", "Has it always leaned like that?",
                "Hoodie. Hoodie. Where's the good shirt?")
    # The desk is a plain table with no drawer, so it is searched in place; the screwdriver lies on it in plain view.
    + [row("Desk", "None", "Look", prompt="Look at the desk", line="I used to do homework here. Like, actually do it."),
       row("Desk", "None", "Use", prompt="Search the desk", event="Searched",
           line="Old worksheets. Cold coffee. A screwdriver, for some reason.")]
    # T3: the left boot hands over the key itself (it sits deep in the boot, out of sight); the key actor just hides.
    + [row("Boot_L", "None", "Look", prompt="Look at the boot", event="Searched",
           line="Something's in my boot."),
       row("Boot_L", "Closed", "Use", nxt="Searched", prompt="Look inside the boot", give="Key", event="KeyTaken",
           line="The key. In my boot. Sure. Why not.", montage=GRAB_FLOOR),
       row("Boot_L", "Searched", "Use", nxt="Worn", prompt="Put on the boots", event="BootsWorn",
           line="Boots on. Still in pajamas, but boots on.", montage=KNEEL),
       row("Boot_L", "Worn", "Use", prompt="Check the boots", line="Boots are on. That's something."),
       row("Boot_R", "None", "Look", prompt="Look at the boot", line="The other boot."),
       row("Boot_R", "None", "Use", prompt="Look inside the boot", event="Searched",
           line="Just a boot. Smells like last winter.", montage=GRAB_FLOOR),
       row("Key", "Hidden", "Notify", "Searched", "Taken")]
    # ---- things to take ----
    + pickup("Screwdriver", "screwdriver", "Screwdriver", "Why is there a screwdriver on my desk.",
             "A screwdriver. That's basically a plan.")
    + pickup("Hanger", "wire hanger", "Hanger", "A wire hanger.",
             "Got it.")
    # T7: hidden until mech_flow stages it (Interact Notify Open); taking it starts the T8 encounter
    + pickup("Shirt", "shirt", "Shirt", "It's inside out. It wasn't inside out.",
             "Got you.", event="ShirtTaken")
    # ---- the door (T2, T4, T5, T6): Locked, KeyJammed, PlateOff, LatchFree, HandleOff, Open ----
    + [row("Door", "Locked", "Look", prompt="Look at the door",
           line="Locked. I locked it. Why did I lock it."),
       row("Door", "KeyJammed", "Look", prompt="Look at the door", line="Half a key, stuck in the lock. Great."),
       row("Door", "PlateOff", "Look", prompt="Look at the door", line="Plate's off. I can see the latch."),
       row("Door", "LatchFree", "Look", prompt="Look at the door", line="Latch is free. Just the handle now."),
       row("Door", "HandleOff", "Look", prompt="Look at the door", line="No handle. Awesome."),
       row("Door", "Open", "Look", prompt="Look at the door", line="It's so bright out there."),
       # T4: the key snaps (Key becomes KeyStub through DT_Items UsedBecomes)
       row("Door", "Locked", "Use", "Key", "KeyJammed", requires="Knows.KeySnaps", prompt="Use the key again",
           line="Snapped. Again. I knew it would.", event="KeySnapped", montage=RATTLE),
       row("Door", "Locked", "Use", "Key", "KeyJammed", prompt="Use the door key on the lock",
           line="Come on. Come on. No. It snapped.", event="KeySnapped", montage=RATTLE),
       # T5 shortcuts once the player knows the key snaps
       row("Door", "Locked", "Use", "Screwdriver", "PlateOff", requires="Knows.KeySnaps",
           prompt="Use the screwdriver on the lock plate", line="Not trying the key again. Screwdriver.", montage=KNEEL),
       row("Door", "Locked", "Use", "Hanger", "LatchFree", requires="Knows.KeySnaps",
           prompt="Use the wire hanger on the door gap", line="Skip the key. Hanger in the gap. There.",
           event="LatchFreed", montage=HANGER_DOOR),
       row("Door", "Locked", "Use", "Screwdriver", "Locked", prompt="Use the screwdriver on the lock plate",
           line="I could take the lock apart. Or find the key like a normal person."),
       row("Door", "Locked", "Use", "Hanger", "Locked", prompt="Use the wire hanger on the door gap",
           line="There's a key. I definitely had a key."),
       row("Door", "Locked", "Use", prompt="Try the handle", line="Locked. From the inside. By me.", montage=RATTLE),
       # T5: route A unscrews the plate, route B hooks the latch
       row("Door", "KeyJammed", "Use", "Screwdriver", "PlateOff", prompt="Use the screwdriver on the lock plate",
           line="Four screws. Why is it always four screws.", montage=KNEEL),
       row("Door", "KeyJammed", "Use", "Hanger", "LatchFree", prompt="Use the wire hanger on the door gap",
           line="Wiggle it. Wiggle it. There.", event="LatchFreed", montage=HANGER_DOOR),
       row("Door", "KeyJammed", "Use", "KeyStub", "KeyJammed", prompt="Use half a key on the lock",
           line="Two halves don't make a key. I checked."),
       row("Door", "KeyJammed", "Use", prompt="Try the handle",
           line="It's not going anywhere.", montage=RATTLE),
       row("Door", "PlateOff", "Use", nxt="LatchFree", prompt="Push the latch back",
           line="Oh. It just slides.", event="LatchFreed",
           montage=RATTLE),
       # T6: the handle comes off; the door tells its Linked wardrobe (Notify HandleOff)
       row("Door", "LatchFree", "Use", nxt="HandleOff", requires="Knows.WardrobeFalls",
           prompt="Pull the handle", line="Don't look at the wardrobe. Don't look at the wardrobe.",
           montage=RATTLE),
       row("Door", "LatchFree", "Use", nxt="HandleOff", prompt="Pull the handle",
           line="The handle came off. The whole handle.", montage=RATTLE),
       row("Door", "HandleOff", "Use", prompt="Push the door", line="Push. Nothing.",
           montage=M + "AM_FoA_PushDoor.AM_FoA_PushDoor"),
       # T10: the flow lane opens the door with Interact(Notify, Open)
       row("Door", "None", "Notify", "Open", "Open"),
       ]
    # ---- the wardrobe topples across the doorway (T6) ----
    + [row("Wardrobe", "Standing", "Look", prompt="Look at the wardrobe",
           line="It's leaning toward the door. Was it always?"),
       row("Wardrobe", "Fallen", "Look", prompt="Look at the wardrobe", line="Right across the door. Of course."),
       row("Wardrobe", "Standing", "Notify", "HandleOff", "Falling", event="WardrobeFalling"),
       row("Wardrobe", "Falling", "Notify", "Arrived", "Fallen", event="WardrobeLanded",
           line="I'm fine. I'm fine. I'm fine.")]
)


def check():
    """No separators or middle dots in player-facing text (UI rule), and every Requires is a known flag."""
    flags = {"None", "Knows.KeyInBoot", "Knows.KeySnaps", "Knows.ScrewdriverInDesk", "Knows.WardrobeFalls",
             "Knows.DoorMoves", "Knows.ShirtPattern"}
    texts = [r["Prompt"] for r in INTERACTIONS] + [r["Line"] for r in INTERACTIONS] + [t for i in ITEMS for t in i[1:3]]
    bad = [t for t in texts if any(c in t for c in "·•|/—–")]
    assert not bad, bad
    assert all(r["Requires"] in flags for r in INTERACTIONS)
    # State rows must win before the ordinary furniture's wildcard rows.
    assert INTERACTIONS[:len(CHASE_ROWS)+len(SEARCH_ROWS)] == CHASE_ROWS+SEARCH_ROWS
    assert {r['Event'] for r in SEARCH_ROWS if r['Event'] != 'None'} == {
        'ClothingWardrobeSearched', 'ClothingDeskSearched', 'ClothingBedSearched', 'ClothingUnhooked', 'ClothingTryUnhook'}
    snag = [r for r in SEARCH_ROWS if r['State'] == 'ClothingSnag' and r['Verb'] == 'Use']
    assert next(r for r in snag if r['Item'] == 'Hanger')['Event'] == 'ClothingUnhooked'
    assert next(r for r in snag if r['Item'] == 'None')['Event'] == 'ClothingTryUnhook'
    assert not any(r['Give'] == 'Shirt' for r in SEARCH_ROWS)
    assert not any(r['Give'] != 'None' for r in CHASE_ROWS)
    return len(INTERACTIONS)


if __name__ == "__main__":
    print("rows ok", check())
