"""Lux3D (Aholo) sand objects in Level 2's interview room: the briefcase, the unpaid bills and the crow (text-to-3D
splats from 11-05, never used until now) form out of black sand as the interview opens and crumble when he answers
"I'll be there." (Journey.StartSeparation). Three StaticMeshComponents on BP_L2StopSet, hidden outside the interview.

  python -B build_l2_sand_set.py components     Hayba: add the three components (structural, own lease)
  python Tools/Unreal/ue_remote.py Tools/Unreal/level2/build_l2_sand_set.py FOA_SAND_STEP=templates   (FOA_AREAS=asset:/Game/FoA/Level2/Journey/BP_L2StopSet)
  python -B build_l2_sand_set.py graphs         append the form/hide nodes to PrepareInterview and Restore
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

STOPSET = '/Game/FoA/Level2/Journey/BP_L2StopSet'
SAND = '/Game/FoA/Level2/Journey/Sand'
MATERIAL = '/Game/FoA/VFX/Splats/Instances/MI_Sand_Hourglass'
# name: (mesh, stop-set local location, yaw, uniform scale). The stage camera sits at (170,233,155) looking -X with a
# 58 deg lens; the dialogue panel covers the lower 45 % of the frame, so everything stands tall in the upper half.
OBJECTS = {  # splat fronts face +Y (glTF +Z), so yaw -90 faces the camera; screen x from the stage camera's 58 deg lens
    'SandBills': ('SM_SandBills', (-210., 77., 0.), -100., 3.4),        # 2 m stack, right of the double (screen x 87 %)
    'SandCrow': ('SM_SandCrow', (-160., 359., 0.), -135., 1.),          # 1.6 m crow, left, turned to the desk (16 %)
    'SandBriefcase': ('SM_SandBriefcase', (-40., 187., 88.), -75., .9),  # on the desk beside the page (70 %)
}
FORM_SECONDS, CRUMBLE_SECONDS = 2.4, 1.6


def mesh_path(name):
    return f'{SAND}/{name}/{name}'


def components():
    import build_drive as b
    info = b.call('blueprint_get_info', path=STOPSET)
    have = {c['name'] for c in info.get('components', [])}
    for name in OBJECTS:
        if name not in have:
            b.call('blueprint_add_component', path=STOPSET, component_name=name,
                   component_class_path='/Script/Engine.StaticMeshComponent')
    b.call('blueprint_compile', path=STOPSET, save=True)


def templates():
    import unreal as u
    assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world(), 'PIE running'
    from free_drive_setup import templates as read
    bp, sds, lib, gathered, handles, comps = read(STOPSET)
    for name, (mesh, (x, y, z), yaw, scale) in OBJECTS.items():
        assert name in handles, ('add the component first', name)
        sds.attach_subobject(handles['Root'], handles[name])
        c = comps[name]
        found = [p.split('.')[0] for p in u.EditorAssetLibrary.list_assets(f'{SAND}/{mesh}', recursive=True, include_folder=False)
                 if str(u.EditorAssetLibrary.find_asset_data(p).asset_class_path.asset_name) == 'StaticMesh']
        assert len(found) == 1, (mesh, found)
        c.set_static_mesh(u.load_asset(found[0]))
        c.set_material(0, u.load_asset(MATERIAL))
        c.set_editor_property('relative_location', u.Vector(x, y, z))
        c.set_editor_property('relative_rotation', u.Rotator(yaw=yaw))
        c.set_editor_property('relative_scale3d', u.Vector(scale, scale, scale))
        c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        for prop, value in (('cast_shadow', False), ('visible', False), ('generate_overlap_events', False),
                            ('can_character_step_up_on', u.CanBeCharacterBase.ECB_NO)):
            c.set_editor_property(prop, value)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    assert u.EditorAssetLibrary.save_loaded_asset(bp, False)
    print('sand set templates', {n: comps[n].get_editor_property('static_mesh').get_name() for n in OBJECTS})


def graphs():
    """Append to PrepareInterview (show, form) and Restore (hide), keeping every existing node."""
    import build_drive as b
    from held_tool_graphs import Batch, inspect
    GS = '/Script/Engine.GameplayStatics:'
    PRIM = '/Script/Engine.PrimitiveComponent:'
    SC = '/Script/Engine.SceneComponent:'
    K = '/Script/Engine.KismetMathLibrary:'
    for graph, show in (('PrepareInterview', True), ('Restore', False)):
        nodes, edges = inspect(STOPSET, graph)
        if any(n['title'] == 'Get ' + next(iter(OBJECTS)) for n in nodes):  # this step already ran here
            print(graph, 'already has the sand objects')
            continue
        has_out = {e['from_node'] for e in edges if e['from_pin'] == 'then'}
        last = 'SetViewTargetWithBlend' if show else 'Stop'  # the end of each existing chain
        tails = [n for n in nodes if n['title'] == last and n['node_id'] not in has_out]
        assert len(tails) == 1, (graph, [n['title'] for n in tails])
        tail = tails[0]
        g = Batch(STOPSET, graph)
        prev, x = tail['node_id'], 6000
        for i, name in enumerate(OBJECTS):
            vis, get = f'v{i}', f'g{i}'
            g.get(get, name, x, 400)
            g.fn(vis, SC + 'SetVisibility', x, 200, bNewVisibility=str(show).lower(), bPropagateToChildren='false')
            g.link(get, name, vis, 'self')
            g.link(prev, 'then', vis, 'execute')
            prev, x = vis, x + 320
            if show:
                now, vec, ev = f't{i}', f'm{i}', f'e{i}'
                g.fn(now, GS + 'GetTimeSeconds', x, 560)
                g.fn(vec, K + 'MakeVector4', x, 400, X='1', Z=str(FORM_SECONDS), W='0')
                g.link(now, 'ReturnValue', vec, 'Y')
                g.fn(ev, PRIM + 'SetVectorParameterForCustomPrimitiveData', x, 200, ParameterName='SandEvent')
                g.link(get, name, ev, 'self')
                g.link(vec, 'ReturnValue', ev, 'Value')
                g.link(prev, 'then', ev, 'execute')
                prev, x = ev, x + 320
        g.comment('Lux3D sand objects', [r for o in g.ops if o['op'] == 'add_node' for r in [o['ref']]])
        g.run()


def run(step):
    import build_drive as b  # noqa: F401  (sys.path for editor_lock)
    import editor_lock
    owner = 'level2'
    os.environ.update(FOA_AGENT=owner, HAYBA_AGENT_ID=owner)
    token = editor_lock.acquire(owner, wait_s=1500, ttl=240, areas=[STOPSET])
    os.environ['FOA_LEASE'] = token or editor_lock.hayba_leases(owner)[0][0]
    try:
        assert not b.call('editor_get_state')['pie_running'], 'PIE is running'
        dict(components=components, graphs=graphs)[step]()
    finally:
        editor_lock.release(owner)


if __name__ == '__main__':
    if os.environ.get('FOA_SAND_STEP') == 'templates':
        sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
        templates()
    else:
        for step in sys.argv[1:]:
            run(step)
