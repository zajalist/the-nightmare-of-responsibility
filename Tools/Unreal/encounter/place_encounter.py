"""Finds where the T8 BP_Encounter goes in L_Tutorial_Bedroom where the whole staging fits: the garment line
(5 slots x SlotSpacing), the Nightmare's mark and the battle camera all inside the room and clear of furniture.
  $env:FOA_AGENT='mech_encounter'; python Tools/Unreal/ue_remote.py Tools/Unreal/encounter/place_encounter.py
Prints PLACE {x, y, yaw}; spawn it with Hayba actor_spawn (label Encounter_T8) and save with level_save."""
import json
import math

import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
CLS = '/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C'
LABEL = 'Encounter_T8'
ROOM = (-350.0, 350.0, -280.0, 280.0)  # interior with a 25 cm margin (editor-rules room outline, bay excluded)
LOCAL = [(0.0, y, 'slot') for y in (-220.0, -110.0, 0.0, 110.0, 220.0)] + [(-260.0, 0.0, 'hero'), (-480.0, 0.0, 'cam'),
                                                                         (-130.0, 0.0, 'between')]


def furniture():
    boxes = []
    for a in EAS.get_all_level_actors():
        folder = str(a.get_folder_path())
        if not (folder.startswith('Room/Furniture') or folder.startswith('Interactables') or
                a.get_actor_label().startswith(('Bed', 'Desk', 'Chair', 'Wardrobe', 'Commode', 'Nightstand'))):
            continue
        o, e = a.get_actor_bounds(True)
        if e.z < 5 or e.x > 400 or e.y > 400:  # rugs and room-sized helpers don't block
            continue
        boxes.append((a.get_actor_label(), o.x - e.x - 30, o.x + e.x + 30, o.y - e.y - 30, o.y + e.y + 30))
    return boxes


def clearance(x, y, boxes):
    if not (ROOM[0] <= x <= ROOM[1] and ROOM[2] <= y <= ROOM[3]):
        return -1.0
    d = min(x - ROOM[0], ROOM[1] - x, y - ROOM[2], ROOM[3] - y)
    for _, x0, x1, y0, y1 in boxes:
        if x0 <= x <= x1 and y0 <= y <= y1:
            return -1.0
        d = min(d, math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1)))
    return d


def main():
    boxes = furniture()
    print('blocking:', [b[0] for b in boxes])
    best = None
    for yaw in (0, 90, 180, 270):
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        for x in range(-200, 201, 25):
            for y in range(-180, 181, 25):
                pts = [(x + lx * c - ly * s, y + lx * s + ly * c) for lx, ly, _ in LOCAL]
                score = min(clearance(px, py, boxes) for px, py in pts)
                if score >= 0 and (best is None or score > best[0]):
                    best = (score, x, y, yaw)
    assert best, 'no placement keeps the staging clear of furniture'
    score, x, y, yaw = best
    existing = [a.get_actor_label() for a in EAS.get_all_level_actors() if a.get_actor_label() == LABEL]
    # read-only: spawning and saving go through Hayba (actor_spawn, level_save), the user's Hayba-first rule
    print('PLACE ' + json.dumps({'x': x, 'y': y, 'yaw': yaw, 'clearance': round(score), 'exists': bool(existing)}))

main()
