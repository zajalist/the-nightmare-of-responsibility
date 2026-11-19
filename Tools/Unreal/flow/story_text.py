"""Level 1 text, approved 2026-11-09 (docs/design/story/script.md, North American voice). One source for every live patch:
apply_story_text.py writes DT_Interactions, DT_Items and GI_FoA from here, apply_story_director.py writes BP_BeatDirector,
and apply_battle_text.py writes the encounter data. The builders (data_rows.py, encounter_data.py, build_story_moments.py,
build_clothing_*.py) carry the same strings, so a rebuild reproduces them. Plain words: no separators, no middle dots."""

# BP_BeatDirector story moments: beat index -> thought. Beats 2, 5 and 7 play after the headache reaction.
STORY_MOMENTS = {
    1: "Okay. I'm up. That counts.",
    2: "Ow. Not now.",
    3: "I hid the key somewhere safe. Safe from me, I guess.",
    5: "Why is it always worse by the door.",
    6: "Almost. Don't get excited.",
    7: "The door was on that wall. I know it was.",
    9: "I look like I have somewhere to be.",
    10: "Head still hurts. Going anyway.",
}
ENDING = "Day one."  # on the black after WalkedOut, before EndOfLevel

# Other BP_BeatDirector string pins (the clothing search and chase): old text -> new text.
DIRECTOR = {
    "Same ceiling. Same morning. Just get up. One thing at a time.": STORY_MOMENTS[1],
    "Behind my eyes again. Like something is pressing from the other side.": STORY_MOMENTS[2],
    "I put the key somewhere safe. Safe from me, apparently.": STORY_MOMENTS[3],
    "It gets worse when I think about leaving. That's probably nothing.": STORY_MOMENTS[5],
    "The handle, then the door. One thing at a time.": STORY_MOMENTS[6],
    "For a second I couldn't remember which wall the door was on. I was looking right at it.": STORY_MOMENTS[7],
    "They are just clothes. They weren't just clothes a minute ago.": STORY_MOMENTS[9],
    "The headache is still here. I can open the door anyway.": STORY_MOMENTS[10],
    "A thread caught in the splintered wood. It trails towards the papers.": "A thread, caught on the wood. It goes toward the desk.",
    "A button under the papers. Mine. Those marks lead back towards the bed.": "One of its buttons. And drag marks, to the bed.",
    "Too far. I need something to reach it.": "Too far back. I need something long.",
    "Too far. A wire hanger could reach it. There was one by the coat rail.": "Can't reach. The hanger on the coat rail might.",
    "My pockets are full.": "My hands are full.",
}

# DT_Interactions: row name -> Line.
# T7: the fall knocks the coat-rail hanger to the floor; said once he's back in his eyes, if it's still lying there
HANGER_FELL = "The hanger's on the floor now. Of course it is."

LINES = {
    "000_Bed_None_Look_None": "My boots are under there. The left one.",
    "001_Bed_None_Look_None": "Still warm. It'd be so easy.",
    "002_Bed_None_Use_None": "Five more minutes. No. Absolutely not.",
    "003_CommodeDrawer_None_Look_None": "Sock drawer. Mom rolls them into little balls.",
    "004_CommodeDrawer_Closed_Use_None": "Socks. No shirt.",
    "006_WardrobeDoor_None_Look_None": "Has it always leaned like that?",
    "007_WardrobeDoor_Closed_Use_None": "Hoodie. Hoodie. Where's the good shirt?",
    "009_Desk_None_Look_None": "I used to do homework here. Like, actually do it.",
    "010_Desk_None_Use_None": "Old worksheets. Cold coffee. A screwdriver, for some reason.",
    "011_Boot_L_None_Look_None": "Something's in my boot.",
    "012_Boot_L_Closed_Use_None": "The key. In my boot. Sure. Why not.",
    "013_Boot_L_Searched_Use_None": "Boots on. Still in pajamas, but boots on.",
    "014_Boot_R_None_Look_None": "The other boot.",
    "015_Boot_R_None_Use_None": "Just a boot. Smells like last winter.",
    "017_Screwdriver_None_Look_None": "Why is there a screwdriver on my desk.",
    "018_Screwdriver_Available_Take_None": "A screwdriver. That's basically a plan.",
    "Screwdriver_Spare_Look": "It's back. I didn't put it back.",  # T7, the refilled, spent screwdriver (2026-11-10)
    "021_Hanger_None_Look_None": "A wire hanger.",
    "022_Hanger_Available_Take_None": "Got it.",
    "025_Shirt_None_Look_None": "It's inside out. It wasn't inside out.",
    "026_Shirt_Available_Take_None": "Got you.",
    "029_Door_Locked_Look_None": "Locked. I locked it. Why did I lock it.",
    "030_Door_KeyJammed_Look_None": "Half a key, stuck in the lock. Great.",
    "031_Door_PlateOff_Look_None": "Plate's off. I can see the latch.",
    "032_Door_LatchFree_Look_None": "Latch is free. Just the handle now.",
    "033_Door_HandleOff_Look_None": "No handle. Awesome.",
    "034_Door_Open_Look_None": "It's so bright out there.",
    "035_Door_Locked_Use_Key": "Snapped. Again. I knew it would.",
    "036_Door_Locked_Use_Key": "Come on. Come on. No. It snapped.",
    "037_Door_Locked_Use_Screwdriver": "Not trying the key again. Screwdriver.",
    "038_Door_Locked_Use_Hanger": "Skip the key. Hanger in the gap. There.",
    "039_Door_Locked_Use_Screwdriver": "I could take the lock apart. Or find the key like a normal person.",
    "040_Door_Locked_Use_Hanger": "There's a key. I definitely had a key.",
    "041_Door_Locked_Use_None": "Locked. From the inside. By me.",
    "042_Door_KeyJammed_Use_Screwdriver": "Four screws. Why is it always four screws.",
    "043_Door_KeyJammed_Use_Hanger": "Wiggle it. Wiggle it. There.",
    "044_Door_KeyJammed_Use_KeyStub": "Two halves don't make a key. I checked.",
    "045_Door_KeyJammed_Use_None": "It's not going anywhere.",
    "046_Door_PlateOff_Use_None": "Oh. It just slides.",
    "047_Door_LatchFree_Use_None": "Don't look at the wardrobe. Don't look at the wardrobe.",
    "048_Door_LatchFree_Use_None": "The handle came off. The whole handle.",
    "049_Door_HandleOff_Use_None": "Push. Nothing.",
    "051_Wardrobe_Standing_Look_None": "It's leaning toward the door. Was it always?",
    "052_Wardrobe_Fallen_Look_None": "Right across the door. Of course.",
    "054_Wardrobe_Falling_Notify_Arrived": "I'm fine. I'm fine. I'm fine.",
    "BootWear_Worn_Use": "Boots are on. That's something.",
    "Search_01_Wardrobe_SearchWardrobe_Look_None": "The good shirt was in there. Something dragged it out.",
    "Search_02_Wardrobe_SearchWardrobeChecked_Use_None": "It goes toward the desk.",
    "Search_03_Wardrobe_SearchWardrobeChecked_Look_None": "A thread. From the shirt.",
    "Search_05_Desk_SearchDesk_Look_None": "Something's under the papers.",
    "Search_06_Desk_SearchDeskChecked_Use_None": "Under the bed. Obviously under the bed.",
    "Search_07_Desk_SearchDeskChecked_Look_None": "Under the bed. Great.",
    "Search_09_Bed_SearchBed_Look_None": "The thread goes under the bed.",
    "Search_12_Bed_ClothingSnag_Look_None": "Too far back. I need something long.",
    "Search_13_Bed_ClothingFreed_Use_None": "It's out. It's at the foot of the bed.",
    "Search_14_Bed_ClothingFreed_Look_None": "Just dust now.",
    "Search_15_Desk_SearchWaiting_Look_None": "Start where it was. The wardrobe.",
    "Search_16_Desk_SearchWaiting_Use_None": "Start where it was. The wardrobe.",
    "Search_17_Bed_SearchWaiting_Look_None": "Start where it was. The wardrobe.",
    "Search_18_Bed_SearchWaiting_Use_None": "Start where it was. The wardrobe.",
}
# DT_Interactions: row name -> Prompt.
PROMPTS = {
    "047_Door_LatchFree_Use_None": "Pull the handle",
    "036_Door_Locked_Use_Key": "Use the door key on the lock",  # the item is "Door key" now (inspect view, 2026-11-10)
    "Chase_ChaseFinal_Use": "Grab the shirt",
    "Chase_ChaseOne_Look": "Look at the shirt",
    "Chase_ChaseTwo_Look": "Look at the shirt",
    "Chase_ChaseFinal_Look": "Look at the shirt",
}
# DT_Interactions: row name -> other cells. The T7 clue rows that advance the search commit at once (QA 2026-11-09: the
# reach montage's contact notify owns the commit, so a reach that does not land, e.g. with the chair in the way,
# cancelled the row and stalled the search). The director's inspection shot and line are the feedback.
ROW_FIELDS = {
    "Search_04_Desk_SearchDesk_Use_None": {"Montage": "None"},
    "Search_08_Bed_SearchBed_Use_None": {"Montage": "None"},
    "Search_10_Bed_ClothingSnag_Use_Hanger": {"Montage": "None"},
}
# DT_Items: item -> DisplayName, LookLine (the pickup inspect view's title and line, 2026-11-10).
ITEM_NAMES = {
    "Key": "Door key",
    "KeyStub": "Half a key",
    "Screwdriver": "Screwdriver",
    "Hanger": "Wire hanger",
    "Shirt": "The shirt",
}
ITEM_LOOKS = {
    "Key": "The door key. I hid it from myself, and it worked.",
    "KeyStub": "Half a key. The door kept the rest.",
    "Screwdriver": "Flathead. No idea why it lives on my desk.",
    "Hanger": "Bent out of shape. Same.",
    "Shirt": "Mom ironed it. It's still warm.",
}
# GI_FoA NotebookLines: his own phone notes, shown on the phone and the rollover card.
NOTES = {
    "Knows.KeyInBoot": "Key's in my left boot. Under the bed.",
    "Knows.KeySnaps": "The key snaps. Don't bother with it.",
    "Knows.ScrewdriverInDesk": "Screwdriver on the desk.",
    "Knows.WardrobeFalls": "Don't pull the handle. The wardrobe comes down.",
    "Knows.DoorMoves": "The door moves. Don't trust it.",
    "Knows.ShirtPattern": "The shirt hides the armhole first. Find it, then button.",
    "Knows.ClothingThread": "Thread in the wardrobe, goes to the desk.",
    "Knows.ClothingTrail": "Button under the papers. Marks to the bed.",
    "Knows.ClothingSnag": "Shirt's under the bed. Use the hanger.",
}
# BP_Encounter MoveDetail string pins: old -> new (the player reads "pants", the asset id stays Trousers).
MOVE_DETAIL = {"Complete the trousers if the timing succeeds.": "Complete the pants if the timing succeeds."}

def plain(v):
    """Exported FText (INVTEXT("x"), NSLOCTEXT("ns", "key", "x"), LOCTEXT) or a plain string -> the display string."""
    import re
    v = str(v)
    if v.startswith(('INVTEXT(', 'NSLOCTEXT(', 'LOCTEXT(')):
        v = re.findall(r'"((?:[^"\\]|\\.)*)"', v)[-1]
        return re.sub(r'\\(.)', r'\1', v)
    return v


BANNED = ("·", "•", "|", "/", "—", "–", "dream", "Dream", "Mum", "trousers")


def check():
    texts = (list(STORY_MOMENTS.values()) + [ENDING] + list(DIRECTOR.values()) + list(LINES.values())
             + list(PROMPTS.values()) + list(ITEM_LOOKS.values()) + list(ITEM_NAMES.values()) + list(NOTES.values()) + list(MOVE_DETAIL.values()))
    bad = [t for t in texts if any(b in t for b in BANNED) or not 0 < len(t) < 140]
    assert not bad, bad
    assert plain('NSLOCTEXT("DT [F1]", "Key_LookLine", "the door\\\'s now.")') == "the door's now."
    assert plain('INVTEXT("Say \\"hi\\"")') == 'Say "hi"' and plain('plain') == 'plain'
    return len(texts)


if __name__ == "__main__":
    print("story text ok", check())
