"""Called by install_debug_frontend: F9 opens diagnostics, F6 advances one playtest step.
Progress switches to a separate debug slot on the first skip, preserving the current knowledge and notebook.
The normal interaction and cinematic completion paths still own their locks and timers.
"""


def install_debug_shortcuts(part="all"):
    director = '/Game/FoA/Gameplay/BP_BeatDirector'
    dc = director + '.BP_BeatDirector_C'
    base = '/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'
    inv = '/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'
    inter = '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'
    gi = '/Game/FoA/Gameplay/GI_FoA.GI_FoA_C'
    gs, ks, math = '/Script/Engine.GameplayStatics:', '/Script/Engine.KismetSystemLibrary:', '/Script/Engine.KismetMathLibrary:'
    events = {0: 'PhoneWakeUp', 1: 'FirstSteps', 2: 'Searched', 3: 'KeyTaken',
              4: 'KeySnapped', 5: 'LatchFreed', 8: 'EncounterWon', 9: 'PayoffEnded', 10: 'WalkedOut'}
    clues = {1: ('ClothingWardrobeSearched', 'SearchWardrobe', 'SearchWardrobeChecked'),
             2: ('ClothingDeskSearched', 'SearchDesk', 'SearchDeskChecked'),
             3: ('ClothingBedSearched', 'SearchBed', 'ClothingSnag'),
             4: ('ClothingUnhooked', 'SearchBed', 'ClothingFreed'),
             5: ('ClothingReachOne', None, None), 6: ('ClothingReachTwo', None, None),
             7: ('ClothingReachFinal', None, None)}
    assert set(events) | {6, 7} == set(range(11))
    assert set(clues) == set(range(1, 8)) and 'ShirtTaken' not in events.values()

    if part != "frontend":
        g = Graph.function(director, 'DebugNextStep'); entry = entry_node(g)
        blocked = g.call(ks + 'PrintString', 1700, -500,
                         InString='Finish the current animation, then press F6 again.', Duration=2.)
        previous, previous_pin = entry, 'then'
        for i, flag in enumerate(('bRollingOver', 'bWardrobeTransition', 'bBattleIntroPlaying')):
            value = g.get(flag, i * 350, 250); gate = g.branch(i * 350, 0)
            g.link(previous, previous_pin, gate, 'execute'); g.link(value, flag, gate, 'Condition')
            g.link(gate, 'True', blocked, 'execute'); previous, previous_pin = gate, 'False'
        pc = g.call(gs + 'GetPlayerController', 1000, 300, PlayerIndex=0)
        move = g.call('/Script/Engine.Controller:IsMoveInputIgnored', 1300, 300); g.link(pc, 'ReturnValue', move, 'self')
        beat = g.get('BeatIndex', 1000, 500); battle = g.call(math + 'EqualEqual_IntInt', 1300, 500, B=8)
        g.link(beat, 'BeatIndex', battle, 'A')
        free = g.call(math + 'Not_PreBool', 1550, 300); g.link(move, 'ReturnValue', free, 'A')
        allowed = g.call(math + 'BooleanOR', 1800, 300)
        g.link(free, 'ReturnValue', allowed, 'A'); g.link(battle, 'ReturnValue', allowed, 'B')
        ready = g.branch(1800, 0); g.link(allowed, 'ReturnValue', ready, 'Condition')
        g.link(previous, previous_pin, ready, 'execute'); g.link(ready, 'False', blocked, 'execute')
        context = g.call(dc + ':GetFoAGI', 2100, 400)
        known = g.get('Knowledge', 2350, 400, gi); lines = g.get('Notebook', 2350, 600, gi)
        for node in (known, lines): g.link(context, 'GI', node, 'self')
        isolate = g.call(gi + ':SetProofProgressContext', 2600, 0, Slot='FoA_QA_DebugSkip')
        g.link(context, 'GI', isolate, 'self'); g.link(known, 'Knowledge', isolate, 'Known'); g.link(lines, 'Notebook', isolate, 'Lines')
        g.exec_chain(ready, isolate)
        bed = g.get('SearchBed', 2100, 850); actor_inter = g.call(base + ':GetInteractor', 2350, 850)
        g.link(bed, 'SearchBed', actor_inter, 'self'); bag = g.get('Inventory', 2600, 850, inter)
        g.link(actor_inter, 'Interactor', bag, 'self')
        previous, previous_pin = isolate, 'then'

        def state(var, value, x, y):
            actor = g.get(var, x, y + 250)
            node = g.call(base + ':SetState', x + 300, y, NewState=value, bInstant=True)
            g.link(actor, var, node, 'self')
            return node

        def add(item, x, y):
            node = g.call(inv + ':Add', x, y, Item=item); g.link(bag, 'Inventory', node, 'self')
            return node

        for index in range(11):
            x, y = 3100, index * 600
            equals = g.call(math + 'EqualEqual_IntInt', x, y + 200, B=index); g.link(beat, 'BeatIndex', equals, 'A')
            gate = g.branch(x + 300, y); g.link(equals, 'ReturnValue', gate, 'Condition')
            g.link(previous, previous_pin, gate, 'execute'); previous, previous_pin = gate, 'False'
            tail = gate
            if index == 3:
                node = add('Key', x + 600, y); g.exec_chain(tail, node); tail = node
                door = g.call(gs + 'GetActorOfClass', x + 900, y, ActorClass='/Game/FoA/Gameplay/BP_Door.BP_Door_C')
                boot = g.get('BootProgressionSource', x + 1200, y + 250, '/Game/FoA/Gameplay/BP_Door.BP_Door_C')
                g.link(door, 'ReturnValue', boot, 'self')
                searched = g.call(base + ':SetState', x + 1500, y, NewState='Searched', bInstant=True)
                g.link(boot, 'BootProgressionSource', searched, 'self'); g.exec_chain(tail, door, searched); tail = searched
            if index in (4, 5):
                door = g.call(gs + 'GetActorOfClass', x + 600, y, ActorClass='/Game/FoA/Gameplay/BP_Door.BP_Door_C')
                node = g.call(base + ':SetState', x + 900, y, NewState='KeyJammed' if index == 4 else 'LatchFree', bInstant=True)
                g.link(door, 'ReturnValue', node, 'self'); g.exec_chain(tail, door, node); tail = node
            if index == 6:
                wardrobe = g.get('SearchWardrobe', x + 600, y + 250)
                node = g.call(base + ':Interact', x + 900, y, Verb='Notify', HeldItem='HandleOff')
                g.link(wardrobe, 'SearchWardrobe', node, 'self'); g.exec_chain(tail, node)
            elif index == 7:
                stage = g.get('ClothingSearchStage', x + 600, y + 250); last, pin = tail, 'True'
                for step, (event, var, value) in clues.items():
                    sx = x + 600 + (step - 1) * 1000
                    eq = g.call(math + 'EqualEqual_IntInt', sx, y + 250, B=step); g.link(stage, 'ClothingSearchStage', eq, 'A')
                    branch = g.branch(sx, y); g.link(eq, 'ReturnValue', branch, 'Condition')
                    g.link(last, pin, branch, 'execute'); last, pin = branch, 'False'; end = branch
                    if step == 4:
                        node = add('Hanger', sx + 250, y); g.exec_chain(end, node); end = node
                    if var:
                        node = state(var, value, sx + 400, y); g.exec_chain(end, node); end = node
                    report = g.call(dc + ':ReportEvent', sx + 850, y, Event=event); g.exec_chain(end, report)
            else:
                if index == 8:
                    encounter = g.call(gs + 'GetActorOfClass', x + 600, y,
                                       ActorClass='/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C')
                    end = g.call('/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C:EndEncounter', x + 900, y)
                    g.link(encounter, 'ReturnValue', end, 'self'); g.exec_chain(tail, encounter, end); tail = end
                report = g.call(dc + ':ReportEvent', x + 1300, y, Event=events[index]); g.exec_chain(tail, report)
        g.comment('Advance one playtest step', '', g.ed.list_all_nodes())
        compile_save(director)

    if part == "director":
        return

    ensure_vars(F, [('bDebugStepHeld', ptype('bool'), 'false', 'Debug', False)])
    g = Graph.function(F, 'DebugNextStep'); entry = entry_node(g)
    distribution = g.call(ks + 'IsPackagedForDistribution', 0, 250); shipping = g.branch(300, 0)
    g.link(distribution, 'ReturnValue', shipping, 'Condition'); g.exec_chain(entry, shipping)
    panel = g.get('DebugPanel', 300, 250); valid = g.call(ks + 'IsValid', 600, 250); g.link(panel, 'DebugPanel', valid, 'Object')
    playing = g.get('bInGameplay', 600, 450); both = g.call(math + 'BooleanAND', 900, 250)
    g.link(valid, 'ReturnValue', both, 'A'); g.link(playing, 'bInGameplay', both, 'B')
    gate = g.branch(1200, 0); g.link(both, 'ReturnValue', gate, 'Condition'); g.link(shipping, 'False', gate, 'execute')
    target = g.call(gs + 'GetActorOfClass', 1500, 0, ActorClass=dc)
    advance = g.call(dc + ':DebugNextStep', 1800, 0); g.link(target, 'ReturnValue', advance, 'self'); g.exec_chain(gate, target, advance)
    g.comment('Skip only with diagnostics', '', g.ed.list_all_nodes())
    g = Graph(F)
    keys = [n for n in g.ed.list_all_nodes() if n.get_class().get_name() == 'K2Node_InputKey' and str(BEL.get_node_title(n)) == 'F6']
    if not keys:
        names = [n for n in g.ed.list_available_nodes([]) if n.startswith('Input|') and n.rsplit('|', 1)[-1] == 'F6']
        assert names, 'F6 input unavailable'
        key = g.node(names[0], 0, 3000); key.set_editor_property('consume_input', True)
        advance = g.call(C(F) + ':DebugNextStep', 350, 3000); g.link(key, 'Pressed', advance, 'execute')
        g.comment('Next playtest step', '', [key, advance])

    g = Graph(F)
    key = next(n for n in g.ed.list_all_nodes() if n.get_class().get_name() == 'K2Node_InputKey' and str(BEL.get_node_title(n)) == 'F6')
    pressed = g.pin(key, 'Pressed', 'out')
    linked = list(PIN.list_connected_pins(pressed))
    if not any(PIN.get_owning_node(p).get_class().get_name() == 'K2Node_IfThenElse' for p in linked):
        gate = g.branch(250, 3000); held = g.get('bDebugStepHeld', 0, 3200)
        down = g.set('bDebugStepHeld', 500, 3000); g.default(down, 'bDebugStepHeld', True)
        up = g.set('bDebugStepHeld', 250, 3400); g.default(up, 'bDebugStepHeld', False)
        PIN.break_pin_links(pressed)
        g.link(key, 'Pressed', gate, 'execute'); g.link(held, 'bDebugStepHeld', gate, 'Condition')
        g.link(gate, 'False', down, 'execute'); g.link(key, 'Released', up, 'execute')
        for pin in linked: assert PIN.try_create_connection(g.pin(down, 'then', 'out'), pin)
        g.comment('One step per press', '', [gate, held, down, up])


import os
install_debug_shortcuts(os.environ.get("FOA_DEBUG_PART", "all"))
