"""mech_flow step 1: data and class shells. Run inside the editor (idempotent, edits in place):
    python Tools/Unreal/ue_remote.py Tools/Unreal/flow/build_flow_data.py
Creates SG_FoA (save slot data), PDA_Beat + DA_Beat_T0..T10 (one data asset per beat; editor Python can't author
UserDefinedStruct/Enum members, so beats are PrimaryDataAsset rows and beat ids are Names), GI_FoA variables,
BP_BeatDirector variables, dispatchers and components. Graphs are built by build_gi.py and build_director.py.
Structural only (crash safety, 20:29/20:37): each Blueprint compiles here only when something was added or migrated, and
no class defaults are written here; build_gi.py and build_director.py write them after their own last compile."""
exec(open('P:/FoA/Tools/Unreal/flow/flow_common.py').read())

T = {k: ptype(k) for k in ('name', 'text', 'int', 'bool', 'real', 'string')}
def ARRAY(t):  # plain functions, not bound Unreal methods kept at module level (the PythonScriptPlugin GC bug)
    return BEL.get_array_type(t)


def SETOF(t):
    return BEL.get_set_type(t)

# Objective lines are player-facing: plain sentences, no separators. Tasks: 0 Wake up, 1 Get dressed, 2 Leave the house.
ROWS = [  # id, objective, advance on, learns (the one flag, on completion), also learn on fail, tick task on completion, show phone, tier
    ('T0', 'Wake up.', ['PhoneWakeUp'], 'None', False, 0, True, 0),  # completing T0 ticks Wake up (2026-11-10)
    ('T1', 'Take a few steps.', ['FirstSteps'], 'None', False, -1, False, 0),
    ('T2', 'Find something to wear.', ['Searched', 'LookedAtBed'], 'None', False, -1, False, 0),  # bare until T8
    ('T3', 'Find the key.', ['KeyTaken'], 'Knows.KeyInBoot', False, -1, False, 0),
    ('T4', 'Unlock the door.', ['KeySnapped'], 'Knows.KeySnaps', False, -1, False, 0),
    ('T5', 'Open the lock another way.', ['LatchFreed'], 'Knows.ScrewdriverInDesk', False, -1, False, 0),
    ('T6', 'Open the door.', ['WardrobeLanded'], 'Knows.WardrobeFalls', False, -1, False, 0),
    ('T7', 'Find the missing shirt.', ['ShirtTaken'], 'Knows.DoorMoves', True, -1, False, 1),
    ('T8', 'Put on the shirt.', ['EncounterWon'], 'Knows.ShirtPattern', True, 1, False, 2),
    ('T9', '', ['PayoffEnded'], 'None', False, -1, False, 2),  # dressed was ticked at T8 ("You're dressed.")
    ('T10', 'Leave the house.', ['WalkedOut'], 'None', False, 2, True, 0),
]
COMPONENTS = (  # name, class, parent (None = the actor's root)
    ('Root', unreal.SceneComponent, None), ('TopDownCamera', unreal.CameraComponent, 'Root'),
    ('MovedDoorSpot', unreal.ArrowComponent, 'Root'), ('UnderDoorLight', unreal.RectLightComponent, 'MovedDoorSpot'),
    ('NightMare', unreal.StaticMeshComponent, 'Root'), ('NightmareT1', unreal.ArrowComponent, 'Root'),
    ('NightmareT7', unreal.ArrowComponent, 'Root'), ('NightmareT8', unreal.ArrowComponent, 'Root'),
    ('NightmareRide', unreal.ArrowComponent, 'NightMare'))


def add_vars(path, specs):
    """specs: (name, pin_type, category, instance_editable). Adds missing variables only; True if anything was added.
    No compile and no wrapper kept here: the caller compiles once."""
    bp = unreal.load_asset(path)
    have = [str(n) for n in BEL.list_member_variable_names(bp, False)]
    added = False
    for name, t, cat, editable in specs:
        if name not in have:
            assert BEL.add_member_variable(bp, name, t), f'add {name}'
            BEL.set_blueprint_variable_category(bp, name, cat)
            BEL.set_blueprint_variable_instance_editable(bp, name, editable)
            added = True
    return added


def save_data():
    make_bp(SG, unreal.SaveGame)
    if add_vars(SG, [('DayCount', T['int'], 'Progress', False), ('Knowledge', SETOF(T['name']), 'Progress', False),
                     ('Notebook', ARRAY(T['text']), 'Progress', False)]):
        compile_bp(SG)  # SG_FoA's own defaults never matter: GI_FoA fills every field before saving


def beats():
    make_bp(PDA, unreal.PrimaryDataAsset)
    changed = add_vars(PDA, [('Id', T['name'], 'Beat', True), ('Objective', T['text'], 'Beat', True),
                             ('AdvanceOn', ARRAY(T['name']), 'Beat', True), ('Learns', T['name'], 'Beat', True),
                             ('bLearnOnFail', T['bool'], 'Beat', True), ('TickTask', T['int'], 'Beat', True),
                             ('bShowPhone', T['bool'], 'Beat', True), ('Tier', T['int'], 'Beat', True)])
    if 'Array' in BEL.get_member_variable_type(unreal.load_asset(PDA), 'Learns').export_text():  # ContainerType=Array
        BEL.change_member_variable_type(unreal.load_asset(PDA), 'Learns', T['name'])  # one flag per beat: no graph loops
        changed = True
    if changed:
        compile_bp(PDA)
    for rid, obj, adv, learns, on_fail, task, phone, tier in ROWS:
        path = f'{BEATS}/DA_Beat_{rid}'
        da = unreal.load_asset(path)
        if not da:
            fac = unreal.DataAssetFactory()
            fac.set_editor_property('data_asset_class', unreal.load_class(None, cls_path(PDA)))
            da = AT.create_asset(f'DA_Beat_{rid}', BEATS, None, fac)
        for k, v in (('Id', rid), ('Objective', obj), ('AdvanceOn', adv), ('Learns', learns), ('bLearnOnFail', on_fail),
                     ('TickTask', task), ('bShowPhone', phone), ('Tier', tier)):
            da.set_editor_property(k, v)
        EAL.save_loaded_asset(da, False)
        del da


def game_instance():
    make_bp(GI, unreal.GameInstance)
    if add_vars(GI, [('DayCount', T['int'], 'Progress', False), ('Knowledge', SETOF(T['name']), 'Progress', False),
                     ('InteractionStage', T['int'], 'Interaction', False),
                     ('NotebookLines', BEL.get_map_type(T['name'], T['text']), 'Phone', False),
                     ('SaveSlot', T['string'], 'Progress', False), ('Notebook', ARRAY(T['text']), 'Phone', False)]):
        compile_bp(GI)  # its class defaults are written by build_gi.py, after its last compile


def director():
    make_bp(DIR, unreal.Actor)
    pda = ptype(unreal.load_class(None, cls_path(PDA)))
    actor, xform = ptype(unreal.Actor), BEL.get_struct_type(unreal.Transform.static_struct())
    changed = add_vars(DIR, [
        ('Beats', ARRAY(pda), 'Beats', True), ('PhoneTasks', ARRAY(T['text']), 'Beats', True),
        ('WakeUpStart', actor, 'Day', True), ('RolloverSeconds', T['real'], 'Day', True),
        ('bAlarmClockFail', T['bool'], 'Day', True), ('AlarmClockSeconds', T['real'], 'Day', True),
        ('NightMareMesh', BEL.get_struct_type(unreal.SoftObjectPath.static_struct()), 'Day', True),
        ('DoorFrame', actor, 'Wrong wall', True), ('Door', actor, 'Wrong wall', True),
        ('RefillActor', actor, 'Wrong wall', True), ('Ceiling', actor, 'Wrong wall', True),
        ('ShirtActor', actor, 'Wrong wall', True),  # mech_core's hidden Shirt pickup, revealed at T7
        ('TopDownBlend', T['real'], 'Wrong wall', True), ('TopDownHold', T['real'], 'Wrong wall', True),
        ('TopDownHoldKnown', T['real'], 'Wrong wall', True),
        ('BeatIndex', T['int'], 'State', False), ('Beat', pda, 'State', False),
        ('TasksTicked', ARRAY(T['bool']), 'State', False), ('FrameHome', xform, 'State', False),
        ('DoorHome', xform, 'State', False),
        ('bRollingOver', T['bool'], 'State', False), ('bTopDown', T['bool'], 'State', False)])
    bp = unreal.load_asset(DIR)
    ged = GE.get_graph_editor_by_name(bp, 'EventGraph')
    for old in ('DoorActors', 'RefillActors', 'HideWhenTopDown', 'DoorHomes'):  # one-time migration to single refs
        if old in [str(n) for n in BEL.list_member_variable_names(bp, False)]:
            ged.remove_member_variable(old)
            changed = True
    have = [str(d) for d in BEL.list_event_dispatchers(bp)]
    for name, params in (('OnBeatChanged', (('Beat', T['name']), ('Objective', T['text']), ('ShowPhone', T['bool']))),
                         ('OnPhoneChanged', ())):
        if name not in have:
            BEL.add_event_dispatcher(bp, name)
            for pn, pt in params:
                BEL.add_event_dispatcher_parameter(bp, name, pn, pt)
            changed = True
    del ged
    changed = add_components(bp) or changed
    del bp
    if changed:
        compile_bp(DIR)  # class defaults and component values: build_director.py events step


def add_components(bp):
    """Adds missing components only; True if any was added. A plain Root comes first: the first scene component added
    may replace DefaultSceneRoot, and that must not be the camera."""
    sds, lib, hs, by_name = subobjects(bp)
    added = False
    for name, cls, parent in COMPONENTS:
        if name not in by_name:
            ph = hs[0] if parent is None else by_name[parent]
            h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=ph, new_class=cls, blueprint_context=bp))
            assert not str(fail), fail
            sds.rename_subobject(h, name)
            by_name[name] = h
            added = True
    return added


save_data()
beats()
game_instance()
director()
save_nocompile(SG, PDA, GI, DIR)  # compiled above only where something changed
