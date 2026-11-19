"""Anim lane: the held-tool Blueprint graphs, as Hayba graph batches (no editor Python).
  python Tools/Unreal/player/held_tool_graphs.py set_held | target | rotation | door_begin | door_restore
set_held      BP_FoAPlayer.SetHeldTool(Mesh, MeshTransform, bShow): HeldToolGrip on Body at hand_r (ToolGripOffset),
              the tool's tip 16 cm out along the grip axis, closed fingers (GripWeight) while held.
target        SetToolHandTarget also keeps the grip point and weight, and drives HeldToolWeight while a tool is held.
rotation      SetToolHandRotation, tool branch. The door's DeltaWorld is its turn angle about the tool axis; every
              90 deg of turn is one stroke: 70% twists the wrist from -45 to +45 with the tool (no slip), 30% regrips
              (the wrist returns, the tool stays, the fingers ease). The hand is placed from the tool frame through the
              inverse grip offset, so the tool sits in the palm and its tip on the screw.
door_begin    BP_Door.BeginDoorTool hands the screwdriver to the player and hides the door's own ToolMesh for it.
door_restore  BP_Door.RestoreDoorTool takes it back.
Each run is one Hayba transaction, compiled and saved."""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
from hayba_call import call  # noqa: E402

PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer'
DOOR = '/Game/FoA/Gameplay/BP_Door'
SRC_C = '/Game/FoA/Characters/Player/ABP_FoAPlayer.ABP_FoAPlayer_C'
MH_C = '/Game/FoA/Characters/Player/ABP_FoAPlayer_MH.ABP_FoAPlayer_MH_C'
PLAYER_C = PLAYER + '.BP_FoAPlayer_C'
K = '/Script/Engine.KismetMathLibrary:'
SC = '/Script/Engine.SceneComponent:'
GROUP = [0.30, 0.22, 0.10]


class Batch:
    def __init__(self, path, graph):
        self.path, self.graph, self.ops = path, graph, []

    def fn(self, ref, func, x, y, **pins):
        self.ops.append(dict(op='add_node', ref=ref, node_type='call_function', function_name=func, x=x, y=y))
        for p, v in pins.items():
            self.pin(ref, p, v)
        return ref

    def node(self, ref, kind, x, y, **args):
        self.ops.append(dict(op='add_node', ref=ref, node_type=kind, x=x, y=y, **args))
        return ref

    def get(self, ref, var, x, y, cls=None):
        return self.node(ref, 'variable_get', x, y, variable_name=var, **({'class_path': cls} if cls else {}))

    def set(self, ref, var, x, y, cls=None):
        return self.node(ref, 'variable_set', x, y, variable_name=var, **({'class_path': cls} if cls else {}))

    def pin(self, ref, name, value):
        self.ops.append(dict(op='set_pin', node_id=ref, pin_name=name, value=str(value)))

    def link(self, a, ap, b, bp):
        self.ops.append(dict(op='connect', from_node=a, from_pin=ap, to_node=b, to_pin=bp))

    def chain(self, *refs):
        for a, b in zip(refs, refs[1:]):
            self.link(a, 'then', b, 'execute')

    def cut(self, a, ap, b, bp):
        self.ops.append(dict(op='disconnect', node_id=a, pin_name=ap, to_node=b, to_pin=bp))

    def comment(self, title, refs):
        self.ops.append(dict(op='comment', title=title, node_ids=refs, color=GROUP))

    def run(self):
        self.ops.append(dict(op='fit_comments'))
        r = call('blueprint_graph_batch', dict(path=self.path, graph_name=self.graph, ops=self.ops, compile=True, save=True), timeout=120)
        d = r.get('data') or {}
        compiled=d.get('compile') or {}
        compile_ok=(not d.get('compile_error') and compiled.get('ok',True) and compiled.get('compiled',True)
                    and not compiled.get('error_count',0) and not compiled.get('num_errors',0))
        print(self.graph, 'ok' if r.get('ok') and compile_ok else 'FAILED', d.get('applied'), '/', d.get('total'), d.get('compile') or '',
              d.get('compile_error') or '', r.get('error') or '', d.get('error') or '')
        if not r.get('ok'):
            i = d.get('failed_index')
            print('failed op', i, json.dumps(self.ops[i]) if i is not None else '', d.get('hint'))
            made = [v for v in (d.get('refs') or {}).values()]  # roll the partial batch back: its nodes, then its cuts
            if made:
                print('rollback', call('blueprint_remove_nodes', dict(path=self.path, graph_name=self.graph, node_ids=made)).get('ok'))
            for o in self.ops[:i or 0]:
                if o['op'] == 'disconnect':
                    print('relink', call('blueprint_connect_nodes', dict(path=self.path, graph_name=self.graph, from_node=o['node_id'],
                                                                          from_pin=o['pin_name'], to_node=o['to_node'], to_pin=o['to_pin'])).get('ok'))
            sys.exit(1)
        if not compile_ok:  # never leave a Blueprint that fails to compile in memory: undo this batch, recompile
            made = [v for v in (d.get('refs') or {}).values()]
            removed = [o for o in self.ops if o['op'] == 'remove']
            if made:
                print('rollback', call('blueprint_remove_nodes', dict(path=self.path, graph_name=self.graph, node_ids=made)).get('ok'))
            for o in self.ops:
                if o['op'] == 'disconnect':
                    call('blueprint_connect_nodes', dict(path=self.path, graph_name=self.graph, from_node=o['node_id'],
                                                         from_pin=o['pin_name'], to_node=o['to_node'], to_pin=o['to_pin']))
            back = call('blueprint_compile', dict(path=self.path))
            print('recompiled after rollback', (back.get('data') or {}).get('error_count'),
                  '(removed nodes cannot be restored: reload the package if', len(removed), '> 0)')
        assert compile_ok, (
            self.graph,'Blueprint compile failed',compiled,d.get('compile_error'))
        return d


def inspect(path, graph):
    d = call('blueprint_inspect_graph', dict(path=path, graph_name=graph))['data']
    nodes, edges = list(d['nodes']), list(d['edges'])
    for kind, param, result in (('nodes', 'offset', nodes), ('edges', 'edge_offset', edges)):
        offset = d.get('page', {}).get(kind, {}).get('next_offset')
        while offset is not None:
            page = call('blueprint_inspect_graph', dict(path=path, graph_name=graph, **{param: offset}))['data']
            result.extend(page[kind])
            offset = page.get('page', {}).get(kind, {}).get('next_offset')
    return nodes, edges


def find(nodes, title):
    hits = [n['node_id'] for n in nodes if n['title'] == title]
    assert len(hits) == 1, (title, hits)
    return hits[0]


def set_held():
    nodes, _ = inspect(PLAYER, 'SetHeldTool')
    assert len(nodes) <= 2, 'SetHeldTool already built'  # entry (+ comment): built once, edit by hand after
    b = Batch(PLAYER, 'SetHeldTool')
    e = find(nodes, 'SetHeldTool')
    b.set('hold', 'bHoldingTool', 300, 0); b.link(e, 'bShow', 'hold', 'bHoldingTool')
    b.get('tool', 'HeldTool', 300, 300); b.get('grip', 'HeldToolGrip', 300, 450); b.get('body', 'Body', 300, 600)
    b.fn('mesh', '/Script/Engine.StaticMeshComponent:SetStaticMesh', 600, 0)
    b.link('tool', 'HeldTool', 'mesh', 'self'); b.link(e, 'Mesh', 'mesh', 'NewMesh')
    b.fn('attach', SC + 'K2_AttachToComponent', 900, 0, SocketName='hand_r', LocationRule='KeepRelative',
         RotationRule='KeepRelative', ScaleRule='KeepRelative')
    b.link('grip', 'HeldToolGrip', 'attach', 'self'); b.link('body', 'Body', 'attach', 'Parent')
    b.get('offset', 'ToolGripOffset', 900, 450)
    b.fn('palm', SC + 'K2_SetRelativeTransform', 1200, 0)
    b.link('grip', 'HeldToolGrip', 'palm', 'self'); b.link('offset', 'ToolGripOffset', 'palm', 'NewTransform')
    b.fn('tip', K + 'MakeTransform', 1200, 450, Location='16,0,0')
    b.fn('fit', K + 'ComposeTransforms', 1500, 450); b.link(e, 'MeshTransform', 'fit', 'A'); b.link('tip', 'ReturnValue', 'fit', 'B')
    b.fn('place', SC + 'K2_SetRelativeTransform', 1500, 0)
    b.link('tool', 'HeldTool', 'place', 'self'); b.link('fit', 'ReturnValue', 'place', 'NewTransform')
    b.fn('show', SC + 'SetVisibility', 1800, 0); b.link('tool', 'HeldTool', 'show', 'self'); b.link(e, 'bShow', 'show', 'bNewVisibility')
    b.chain(e, 'hold', 'mesh', 'attach', 'palm', 'place', 'show')
    b.comment('Put the tool in the palm', ['hold', 'tool', 'grip', 'body', 'mesh', 'attach', 'offset', 'palm', 'tip', 'fit', 'place', 'show'])
    b.get('src', 'Mesh', 2100, 450)
    b.fn('srcanim', '/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 2100, 600); b.link('src', 'Mesh', 'srcanim', 'self')
    b.node('srccast', 'cast', 2400, 0, class_path=SRC_C); b.link('srcanim', 'ReturnValue', 'srccast', 'Object')
    b.fn('closed', K + 'SelectFloat', 2400, 450, A=1.0, B=0.0); b.link(e, 'bShow', 'closed', 'bPickA')
    b.set('fingers', 'GripWeight', 2700, 0, SRC_C)
    b.link('srccast', 'AsABP Fo APlayer', 'fingers', 'self'); b.link('closed', 'ReturnValue', 'fingers', 'GripWeight')
    b.fn('mhanim', '/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 2700, 600); b.link('body', 'Body', 'mhanim', 'self')
    b.node('mhcast', 'cast', 3000, 0, class_path=MH_C); b.link('mhanim', 'ReturnValue', 'mhcast', 'Object')
    b.set('release', 'HeldToolWeight', 3300, 0, MH_C); b.pin('release', 'HeldToolWeight', 0.0)
    b.link('mhcast', 'AsABP Fo APlayer MH', 'release', 'self')
    b.chain('show', 'srccast', 'fingers', 'mhcast', 'release')
    b.comment('Close the fingers', ['src', 'srcanim', 'srccast', 'closed', 'fingers', 'mhanim', 'mhcast', 'release'])
    b.run()


def target():
    nodes, edges = inspect(PLAYER, 'SetToolHandTarget')
    assert not [n for n in nodes if n['title'] == 'Set ToolGripWorld'], 'SetToolHandTarget already extended'
    e = find(nodes, 'SetToolHandTarget'); mhcast = find(nodes, 'Cast To ABP_FoAPlayer_MH')
    last = next(n['node_id'] for n in nodes if n['title'] == 'Set ToolHandWeight'
                and any(x['to_node'] == n['node_id'] and x['from_node'] == find(nodes, 'Cast To ABP_FoAPlayer') for x in edges))
    b = Batch(PLAYER, 'SetToolHandTarget')
    b.cut(e, 'then', mhcast, 'execute')
    b.set('world', 'ToolGripWorld', 150, -350); b.link(e, 'TargetWorld', 'world', 'ToolGripWorld')
    b.fn('clamp', K + 'FClamp', 150, -150, Min=0.0, Max=1.0); b.link(e, 'Weight', 'clamp', 'Value')
    b.set('weight', 'ToolGripWeight', 450, -350); b.link('clamp', 'ReturnValue', 'weight', 'ToolGripWeight')
    b.chain(e, 'world', 'weight'); b.link('weight', 'then', mhcast, 'execute')
    b.get('holding', 'bHoldingTool', 3000, 450); b.get('gripweight', 'ToolGripWeight', 3000, 600)
    b.fn('held', K + 'SelectFloat', 3300, 450, B=0.0)
    b.link('gripweight', 'ToolGripWeight', 'held', 'A'); b.link('holding', 'bHoldingTool', 'held', 'bPickA')
    b.set('heldweight', 'HeldToolWeight', 3600, 0, MH_C)
    b.link(mhcast, 'AsABP Fo APlayer MH', 'heldweight', 'self'); b.link('held', 'ReturnValue', 'heldweight', 'HeldToolWeight')
    b.link(last, 'then', 'heldweight', 'execute')
    b.comment('Keep the grip point', ['world', 'clamp', 'weight'])
    b.comment('Release the held tool', ['holding', 'gripweight', 'held', 'heldweight'])
    b.run()


def rotation():
    nodes, _ = inspect(PLAYER, 'SetToolHandRotation')
    assert not [n for n in nodes if n['title'] == 'Branch'], 'SetToolHandRotation already has its tool branch'
    e = find(nodes, 'SetToolHandRotation'); keycast = find(nodes, 'Cast To ABP_FoAPlayer_MH')
    b = Batch(PLAYER, 'SetToolHandRotation')
    b.cut(e, 'then', keycast, 'execute')
    b.get('holding', 'bHoldingTool', 0, -500)
    b.node('which', 'branch', 300, -400); b.link('holding', 'bHoldingTool', 'which', 'Condition')
    b.link(e, 'then', 'which', 'execute'); b.link('which', 'else', keycast, 'execute')
    # Read the turn: the door's rotation about the tool axis, as an angle that only grows with the turn.
    y0 = 400
    b.fn('fwd', '/Script/Engine.Actor:GetActorForwardVector', 0, y0)
    b.fn('right', '/Script/Engine.Actor:GetActorRightVector', 0, y0 + 150)
    b.fn('spun', K + 'GreaterGreater_VectorRotator', 300, y0 + 300, A='0,0,1'); b.link(e, 'DeltaWorld', 'spun', 'B')
    b.fn('across', K + 'Dot_VectorVector', 600, y0 + 150); b.link('spun', 'ReturnValue', 'across', 'A'); b.link('right', 'ReturnValue', 'across', 'B')
    b.fn('upright', K + 'Dot_VectorVector', 600, y0 + 300, B='0,0,1'); b.link('spun', 'ReturnValue', 'upright', 'A')
    b.fn('angle', K + 'DegAtan2', 900, y0 + 200); b.link('across', 'ReturnValue', 'angle', 'Y'); b.link('upright', 'ReturnValue', 'angle', 'X')
    b.fn('turned', K + 'Subtract_DoubleDouble', 1200, y0 + 200, A=720.0); b.link('angle', 'ReturnValue', 'turned', 'B')
    b.fn('stroke', K + 'Percent_FloatFloat', 1500, y0 + 100, B=90.0); b.link('turned', 'ReturnValue', 'stroke', 'A')
    b.fn('quarter', K + 'Percent_FloatFloat', 1500, y0 + 300, B=360.0); b.link('turned', 'ReturnValue', 'quarter', 'A')
    b.comment('Read the turn', ['holding', 'which', 'fwd', 'right', 'spun', 'across', 'upright', 'angle', 'turned', 'stroke', 'quarter'])
    # Ratchet: u in [0,1) per 90 deg. 0-0.7 twists with the tool, 0.7-1 regrips.
    y1 = y0 + 600
    b.fn('u', K + 'Multiply_DoubleDouble', 1800, y1, B=1.0 / 90.0); b.link('stroke', 'ReturnValue', 'u', 'A')
    b.fn('twistu', K + 'Multiply_DoubleDouble', 2100, y1, B=1.0 / 0.7); b.link('u', 'ReturnValue', 'twistu', 'A')
    b.fn('twistc', K + 'FClamp', 2400, y1, Min=0.0, Max=1.0); b.link('twistu', 'ReturnValue', 'twistc', 'Value')
    b.fn('twiste', K + 'FInterpEaseInOut', 2700, y1, A=0.0, B=1.0, Exponent=2.0); b.link('twistc', 'ReturnValue', 'twiste', 'Alpha')
    b.fn('backu', K + 'Subtract_DoubleDouble', 2100, y1 + 250, B=0.7); b.link('u', 'ReturnValue', 'backu', 'A')
    b.fn('backs', K + 'Multiply_DoubleDouble', 2400, y1 + 250, B=1.0 / 0.3); b.link('backu', 'ReturnValue', 'backs', 'A')
    b.fn('backc', K + 'FClamp', 2700, y1 + 250, Min=0.0, Max=1.0); b.link('backs', 'ReturnValue', 'backc', 'Value')
    b.fn('backe', K + 'FInterpEaseInOut', 3000, y1 + 250, A=0.0, B=1.0, Exponent=2.0); b.link('backc', 'ReturnValue', 'backe', 'Alpha')
    b.fn('net', K + 'Subtract_DoubleDouble', 3300, y1); b.link('twiste', 'ReturnValue', 'net', 'A'); b.link('backe', 'ReturnValue', 'net', 'B')
    b.fn('netdeg', K + 'Multiply_DoubleDouble', 3600, y1, B=90.0); b.link('net', 'ReturnValue', 'netdeg', 'A')
    b.fn('twist', K + 'Subtract_DoubleDouble', 3900, y1, B=45.0); b.link('netdeg', 'ReturnValue', 'twist', 'A')
    # The tool's roll in the palm: the quarter it has reached, +45, plus the slip of the regrip.
    b.fn('base', K + 'Subtract_DoubleDouble', 3300, y1 + 500); b.link('quarter', 'ReturnValue', 'base', 'A'); b.link('stroke', 'ReturnValue', 'base', 'B')
    b.fn('slip', K + 'Multiply_DoubleDouble', 3300, y1 + 650, B=90.0); b.link('backe', 'ReturnValue', 'slip', 'A')
    b.fn('roll0', K + 'Add_DoubleDouble', 3600, y1 + 500, B=45.0); b.link('base', 'ReturnValue', 'roll0', 'A')
    b.fn('roll', K + 'Add_DoubleDouble', 3900, y1 + 500); b.link('roll0', 'ReturnValue', 'roll', 'A'); b.link('slip', 'ReturnValue', 'roll', 'B')
    # The fingers ease mid-regrip: 1 - 1.2 * e * (1 - e).
    b.fn('open1', K + 'Subtract_DoubleDouble', 3300, y1 + 850, A=1.0); b.link('backe', 'ReturnValue', 'open1', 'B')
    b.fn('open2', K + 'Multiply_DoubleDouble', 3600, y1 + 850); b.link('backe', 'ReturnValue', 'open2', 'A'); b.link('open1', 'ReturnValue', 'open2', 'B')
    b.fn('squeeze', K + 'Multiply_DoubleDouble', 3900, y1 + 850, B=-1.2); b.link('open2', 'ReturnValue', 'squeeze', 'A')
    b.fn('closed', K + 'Add_DoubleDouble', 4200, y1 + 850, B=1.0); b.link('squeeze', 'ReturnValue', 'closed', 'A')
    b.comment('Ratchet the wrist', ['u', 'twistu', 'twistc', 'twiste', 'backu', 'backs', 'backc', 'backe', 'net', 'netdeg', 'twist',
                                    'base', 'slip', 'roll0', 'roll', 'open1', 'open2', 'squeeze', 'closed'])
    # Place the hand: the tool frame (axis into the door, rolled by the wrist twist) through the inverse grip offset.
    y2 = -400
    b.fn('twistrot', K + 'MakeRotator', 1800, y2 + 900); b.link('twist', 'ReturnValue', 'twistrot', 'Roll')
    b.fn('up', K + 'MakeVector', 1500, y2 + 800, X=0.0, Y=0.0, Z=1.0)  # MakeRotFromXZ takes its vectors by reference
    b.fn('axis', K + 'MakeRotFromXZ', 1800, y2 + 700); b.link('fwd', 'ReturnValue', 'axis', 'X'); b.link('up', 'ReturnValue', 'axis', 'Z')
    b.fn('frame', K + 'ComposeRotators', 2100, y2 + 750); b.link('twistrot', 'ReturnValue', 'frame', 'A'); b.link('axis', 'ReturnValue', 'frame', 'B')
    b.get('gripworld', 'ToolGripWorld', 2100, y2 + 550)
    b.fn('toolxf', K + 'MakeTransform', 2400, y2 + 550, Scale='1,1,1')
    b.link('gripworld', 'ToolGripWorld', 'toolxf', 'Location'); b.link('frame', 'ReturnValue', 'toolxf', 'Rotation')
    b.get('offset', 'ToolGripOffset', 2400, y2 + 800)
    b.fn('inv', K + 'InvertTransform', 2700, y2 + 800); b.link('offset', 'ToolGripOffset', 'inv', 'T')
    b.fn('handxf', K + 'ComposeTransforms', 3000, y2 + 600); b.link('inv', 'ReturnValue', 'handxf', 'A'); b.link('toolxf', 'ReturnValue', 'handxf', 'B')
    b.fn('hand', K + 'BreakTransform', 3300, y2 + 600); b.link('handxf', 'ReturnValue', 'hand', 'InTransform')
    b.fn('back', K + 'Multiply_VectorFloat', 3300, y2 + 900, B=-30.0); b.link('fwd', 'ReturnValue', 'back', 'A')
    b.fn('out', K + 'Multiply_VectorFloat', 3300, y2 + 1050, B=28.0); b.link('right', 'ReturnValue', 'out', 'A')
    b.fn('pole1', K + 'Add_VectorVector', 3600, y2 + 950); b.link('back', 'ReturnValue', 'pole1', 'A'); b.link('out', 'ReturnValue', 'pole1', 'B')
    b.fn('pole2', K + 'Add_VectorVector', 3900, y2 + 950, B='0,0,-5'); b.link('pole1', 'ReturnValue', 'pole2', 'A')
    b.fn('elbow', K + 'Add_VectorVector', 4200, y2 + 800); b.link('hand', 'Location', 'elbow', 'A'); b.link('pole2', 'ReturnValue', 'elbow', 'B')
    b.comment('Place the hand from the tool', ['twistrot', 'up', 'axis', 'frame', 'gripworld', 'toolxf', 'offset', 'inv', 'handxf', 'hand',
                                              'back', 'out', 'pole1', 'pole2', 'elbow'])
    # Drive the visible body, the tool's roll in the palm, and the source fingers.
    y3 = -400
    b.get('body', 'Body', 4500, y3 + 300)
    b.fn('mhanim', '/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 4500, y3 + 450); b.link('body', 'Body', 'mhanim', 'self')
    b.node('mhcast', 'cast', 4800, y3, class_path=MH_C); b.link('mhanim', 'ReturnValue', 'mhcast', 'Object')
    b.set('settarget', 'ToolHandTarget', 5100, y3, MH_C); b.link('hand', 'Location', 'settarget', 'ToolHandTarget')
    b.set('setelbow', 'ToolElbowTarget', 5400, y3, MH_C); b.link('elbow', 'ReturnValue', 'setelbow', 'ToolElbowTarget')
    b.set('setrot', 'HeldToolRotation', 5700, y3, MH_C); b.link('hand', 'Rotation', 'setrot', 'HeldToolRotation')
    b.get('weight', 'ToolGripWeight', 5700, y3 + 450)
    b.set('setweight', 'HeldToolWeight', 6000, y3, MH_C); b.link('weight', 'ToolGripWeight', 'setweight', 'HeldToolWeight')
    for r in ('settarget', 'setelbow', 'setrot', 'setweight'):
        b.link('mhcast', 'AsABP Fo APlayer MH', r, 'self')
    b.get('grip', 'HeldToolGrip', 6000, y3 + 600)
    b.fn('palm', K + 'BreakTransform', 6000, y3 + 750); b.link('offset', 'ToolGripOffset', 'palm', 'InTransform')
    b.fn('rollrot', K + 'MakeRotator', 6000, y3 + 950); b.link('roll', 'ReturnValue', 'rollrot', 'Roll')
    b.fn('inpalm', K + 'ComposeRotators', 6300, y3 + 850); b.link('rollrot', 'ReturnValue', 'inpalm', 'A'); b.link('palm', 'Rotation', 'inpalm', 'B')
    b.fn('spin', SC + 'K2_SetRelativeRotation', 6300, y3); b.link('grip', 'HeldToolGrip', 'spin', 'self'); b.link('inpalm', 'ReturnValue', 'spin', 'NewRotation')
    b.get('src', 'Mesh', 6600, y3 + 300)
    b.fn('srcanim', '/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 6600, y3 + 450); b.link('src', 'Mesh', 'srcanim', 'self')
    b.node('srccast', 'cast', 6900, y3, class_path=SRC_C); b.link('srcanim', 'ReturnValue', 'srccast', 'Object')
    b.set('fingers', 'GripWeight', 7200, y3, SRC_C); b.link('srccast', 'AsABP Fo APlayer', 'fingers', 'self'); b.link('closed', 'ReturnValue', 'fingers', 'GripWeight')
    b.link('which', 'then', 'mhcast', 'execute')
    b.chain('mhcast', 'settarget', 'setelbow', 'setrot', 'setweight', 'spin', 'srccast', 'fingers')
    b.comment('Drive the hand and the tool', ['body', 'mhanim', 'mhcast', 'settarget', 'setelbow', 'setrot', 'weight', 'setweight', 'grip',
                                              'palm', 'rollrot', 'inpalm', 'spin', 'src', 'srcanim', 'srccast', 'fingers'])
    b.run()


def door_begin():
    nodes, edges = inspect(DOOR, 'BeginDoorTool')
    assert not [n for n in nodes if n['title'] in ('SetHeldTool', 'Set Held Tool')], 'BeginDoorTool already hands the tool over'
    vis, show, iskey = find(nodes, 'SetVisibility'), find(nodes, 'SetDoorToolPresentation'), find(nodes, 'Equal (Name)')
    assert any(x['from_node'] == vis and x['to_node'] == show for x in edges), 'SetVisibility no longer leads to the presentation'
    b = Batch(DOOR, 'BeginDoorTool')
    b.cut(vis, 'then', show, 'execute')
    b.link(iskey, 'ReturnValue', vis, 'bNewVisibility')  # the door shows its own mesh for the key only
    b.node('player', 'variable_get', 4500, -650, variable_name='ToolPlayer')
    b.node('cast', 'cast', 4800, -500, class_path=PLAYER_C); b.link('player', 'ToolPlayer', 'cast', 'Object')
    b.fn('driver', K + 'Not_PreBool', 4800, -800); b.link(iskey, 'ReturnValue', 'driver', 'A')
    b.get('mesh', 'ToolDriverMesh', 5100, -900); b.get('fit', 'ToolDriverTransform', 5100, -750)
    b.fn('hand', PLAYER_C + ':SetHeldTool', 5400, -500)
    b.link('cast', 'AsBP Fo APlayer', 'hand', 'self'); b.link('mesh', 'ToolDriverMesh', 'hand', 'Mesh')
    b.link('fit', 'ToolDriverTransform', 'hand', 'MeshTransform'); b.link('driver', 'ReturnValue', 'hand', 'bShow')
    b.chain(vis, 'cast', 'hand'); b.link('hand', 'then', show, 'execute'); b.link('cast', 'CastFailed', show, 'execute')
    b.comment('Hand him the screwdriver', ['player', 'cast', 'driver', 'mesh', 'fit', 'hand'])
    b.run()


def door_restore():
    nodes, edges = inspect(DOOR, 'RestoreDoorTool')
    assert not [n for n in nodes if n['title'] in ('SetHeldTool', 'Set Held Tool')], 'RestoreDoorTool already takes the tool back'
    hide = [n['node_id'] for n in nodes if n['title'] == 'SetVisibility'
            and any(x['to_node'] == n['node_id'] and x['from_pin'] == 'ToolMesh' for x in edges)]
    assert len(hide) == 1, hide
    hide = hide[0]
    after = [x for x in edges if x['from_node'] == hide and x['from_pin'] == 'then']
    assert len(after) == 1, after
    nxt = after[0]['to_node']
    b = Batch(DOOR, 'RestoreDoorTool')
    b.cut(hide, 'then', nxt, 'execute')
    b.node('player', 'variable_get', 2100, -650, variable_name='ToolPlayer')
    b.node('cast', 'cast', 2400, -500, class_path=PLAYER_C); b.link('player', 'ToolPlayer', 'cast', 'Object')
    b.fn('hand', PLAYER_C + ':SetHeldTool', 2700, -500, bShow='false')
    b.link('cast', 'AsBP Fo APlayer', 'hand', 'self')
    b.chain(hide, 'cast', 'hand'); b.link('hand', 'then', nxt, 'execute'); b.link('cast', 'CastFailed', nxt, 'execute')
    b.comment('Take the screwdriver back', ['player', 'cast', 'hand'])
    b.run()


if __name__ == '__main__':  # importable: dm_graphs.py reuses Batch
    {'set_held': set_held, 'target': target, 'rotation': rotation, 'door_begin': door_begin, 'door_restore': door_restore}[sys.argv[1]]()
