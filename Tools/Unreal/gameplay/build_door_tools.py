"""Door-owned tool interactions. Declare separately, then build bodies under one BP_Door lease.
Overrides retain their inherited behavior until the complete interaction is wired.
"""
import os
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())

DOOR = '/Game/FoA/Gameplay/BP_Door'
INTERACT = '/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'
ROW = BEL.get_struct_type(unreal.load_asset('/Game/FoA/Gameplay/S_Interaction'))
ACTOR = ptype(unreal.Actor)
REAL, BOOL, NAME = ptype('real'), ptype('bool'), ptype('name')
SIGNATURES = {
    'GetDoorToolMode': (True, [('Row', ROW)], [('Mode', NAME)]),
    'BeginDoorTool': (False, [('Row', ROW)], []),
    'StepDoorTool': (False, [], []),
    'AdvanceDoorTool': (False, [('Turn', REAL), ('DeltaSeconds', REAL)], []),
    'HoldDoorToolPose': (False, [], []),
    'MarkDoorToolReady': (False, [], []),
    'FinishDoorTool': (False, [], []),
    'CancelDoorTool': (False, [], []),
    'RestoreDoorTool': (False, [], []),
    'RefreshDoorTool': (False, [], []),
    'SetDoorToolPresentation': (False, [('Enabled', BOOL)], []),
    'DoorRowWithoutMontage': (True, [('Row', ROW)], [('Result', ROW)]),
}


def declare():
    bp = unreal.load_asset(DOOR)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    ensure_vars(DOOR, [
        ('bToolActive', BOOL, 'false', 'Tool', False),
        ('bToolCommitting', BOOL, 'false', 'Tool', False),
        ('bToolReady', BOOL, 'false', 'Tool', False),
        ('bToolOwnsLocks', BOOL, 'false', 'Tool', False),
        ('bToolReleasing', BOOL, 'false', 'Tool', False),
        ('ToolPreviousControl', ptype(unreal.Rotator), '', 'Tool', False),
        ('bToolPreviousCursor', BOOL, 'false', 'Tool', False),
        ('bToolPreviousLookMode', BOOL, 'false', 'Tool', False),
        ('ToolRow', ROW, '', 'Tool', False),
        ('ToolMode', NAME, 'None', 'Tool', False),
        ('ToolAngle', REAL, '0.0', 'Tool', False),
        ('ToolInputAngle', REAL, '0.0', 'Tool', False),
        ('ToolStepIndex', ptype('int'), '0', 'Tool', False),
        ('ToolLastTime', REAL, '0.0', 'Tool', False),
        ('ToolPreviousView', ACTOR, '', 'Tool', False),
        ('ToolPlayer', ptype(unreal.Character), '', 'Tool', False),
        ('ToolController', ptype(unreal.PlayerController), '', 'Tool', False),
        ('ToolHandTarget', ptype(unreal.Vector), '', 'Tool', False),
        ('ToolMontage', ptype(unreal.AnimMontage), '', 'Tool', False),
        ('ToolKeyMesh', ptype(unreal.StaticMesh), '/Game/FoA/Lux3D/door_key/SM_Lux3D_DoorKey.SM_Lux3D_DoorKey', 'Tool', True),
        ('ToolDriverMesh', ptype(unreal.StaticMesh), '/Game/FoA/Props/screwdriver/screwdriver_1k/StaticMeshes/screwdriver_1k.screwdriver_1k', 'Tool', True),
        ('ToolContactTimes', BEL.get_map_type(NAME, REAL), '', 'Tool', False),
        ('ToolReleaseTimes', BEL.get_map_type(NAME, REAL), '', 'Tool', False),
        ('ToolKeyTransform', ptype(unreal.Transform), '', 'Tool', True),
        ('ToolDriverTransform', ptype(unreal.Transform), '', 'Tool', True),
    ])
    graphs = {str(n) for n in BEL.list_graph_names(bp)}
    for name, (pure, inputs, outputs) in SIGNATURES.items():
        if name not in graphs:
            Graph.function(DOOR, name, pure=pure, inputs=inputs, outputs=outputs)
    for name in ('ApplyRow', 'CancelPendingRow'):
        if name not in graphs:
            graph = BEL.add_function_override(bp, name)
            assert graph, f'Cannot safely override inherited {name}'
            editor = GE.get_graph_editor(graph)
            parents = editor.list_nodes_of_class(unreal.K2Node_CallParentFunction)
            assert len(parents) == 1, f'{name} must retain its inherited call'
    compile_save(DOOR)


if os.environ.get('FOA_PHASE', 'declare') == 'declare':
    declare()
else:
    exec(open('P:/FoA/Tools/Unreal/gameplay/door_tools_body.py', encoding='utf-8').read())
