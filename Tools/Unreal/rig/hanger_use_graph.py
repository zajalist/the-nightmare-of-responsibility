"""BP_FoAHangerUse EventGraph (rig lane), one Hayba batch; called by hanger_use_build.py graph.
BeginPlay: take the player, remember PawnStart, StanceT (Stance X, Y at his own height, yaw Stance.Z), BeginGrip(Hanger,
GripPose, HandInAnchor). Tick: while Anim plays Montage, i = clamp(floor(pos / Dt), 0, KeyCount - 2), a = frac;
Hanger = TLerp(KeysA (x) his transform, KeysB, KeysW); Proxy = KeysP, shown until ProxyHideAt; while pos < SlideTime the
pawn eases from PawnStart to StanceT (control yaw with it). When the montage stops: EndGrip, destroy."""
from held_tool_graphs import Batch, inspect, find

K = '/Script/Engine.KismetMathLibrary:'
GS = '/Script/Engine.GameplayStatics:'
AI = '/Script/Engine.AnimInstance:'
SC = '/Script/Engine.SceneComponent:'
ACT = '/Script/Engine.Actor:'


def build(BP, PLAYER_C, pins):
    ARRAY_PIN, INDEX_PIN, ITEM_PIN = pins
    ns, _ = inspect(BP, 'EventGraph')
    begin = find(ns, 'Event BeginPlay')
    tick = find(ns, 'Event Tick')
    b = Batch(BP, 'EventGraph')
    old = [n['node_id'] for n in ns if n['node_id'] not in (begin, tick) and n['title'] != 'Event ActorBeginOverlap']
    if old:
        b.ops.append(dict(op='remove', node_ids=old))

    def item(ref, arr, idx, x, y):
        b.get(ref + 'arr', arr, x, y)
        b.node(ref, 'get_array_item', x + 200, y)
        b.link(ref + 'arr', arr, ref, ARRAY_PIN)
        b.link(idx, 'ReturnValue', ref, INDEX_PIN)

    b.fn('pc', GS + 'GetPlayerCharacter', 200, 300, PlayerIndex=0)
    b.node('cast', 'cast', 300, 0, class_path=PLAYER_C); b.link('pc', 'ReturnValue', 'cast', 'Object'); b.chain(begin, 'cast')
    b.fn('gone', ACT + 'K2_DestroyActor', 600, -300); b.link('cast', 'CastFailed', 'gone', 'execute')
    b.set('setp', 'Player', 600, 0); b.link('cast', 'AsBP Fo APlayer', 'setp', 'Player')
    b.fn('pt', ACT + 'GetTransform', 600, 300); b.link('cast', 'AsBP Fo APlayer', 'pt', 'self')
    b.set('sets', 'PawnStart', 900, 0); b.link('pt', 'ReturnValue', 'sets', 'PawnStart')
    b.get('mesh', 'Mesh', 900, 400, '/Script/Engine.Character'); b.link('cast', 'AsBP Fo APlayer', 'mesh', 'self')
    b.fn('ai', '/Script/Engine.SkeletalMeshComponent:GetAnimInstance', 1100, 400); b.link('mesh', 'Mesh', 'ai', 'self')
    b.set('seta', 'Anim', 1200, 0); b.link('ai', 'ReturnValue', 'seta', 'Anim')
    b.get('st', 'Stance', 1200, 600)
    b.fn('stb', K + 'BreakVector', 1400, 600); b.link('st', 'Stance', 'stb', 'InVec')
    b.fn('ptb', K + 'BreakTransform', 1400, 800); b.link('pt', 'ReturnValue', 'ptb', 'InTransform')
    b.fn('ptl', K + 'BreakVector', 1600, 800); b.link('ptb', 'Location', 'ptl', 'InVec')
    b.fn('sv', K + 'MakeVector', 1800, 600); b.link('stb', 'X', 'sv', 'X'); b.link('stb', 'Y', 'sv', 'Y'); b.link('ptl', 'Z', 'sv', 'Z')
    b.fn('sr', K + 'MakeRotator', 1800, 800, Roll=0, Pitch=0); b.link('stb', 'Z', 'sr', 'Yaw')
    b.fn('stt', K + 'MakeTransform', 2000, 700, Scale='1,1,1'); b.link('sv', 'ReturnValue', 'stt', 'Location'); b.link('sr', 'ReturnValue', 'stt', 'Rotation')
    b.set('setst', 'StanceT', 1500, 0); b.link('stt', 'ReturnValue', 'setst', 'StanceT')
    b.get('hg', 'Hanger', 1700, 300); b.get('pose', 'GripPose', 1700, 400); b.get('hia', 'HandInAnchor', 1700, 500)
    b.fn('grip', PLAYER_C + ':BeginGrip', 1800, 0); b.link('cast', 'AsBP Fo APlayer', 'grip', 'self')
    b.link('hg', 'Hanger', 'grip', 'Anchor'); b.link('pose', 'GripPose', 'grip', 'Pose'); b.link('hia', 'HandInAnchor', 'grip', 'HandInAnchor')
    b.chain('cast', 'setp', 'sets', 'seta', 'setst', 'grip')
    b.comment("Take the player and grip the hanger (BeginGrip is the anim lane's: the hand follows this actor's Hanger)",
              ['pc', 'cast', 'gone', 'setp', 'pt', 'sets', 'mesh', 'ai', 'seta', 'st', 'stb', 'ptb', 'ptl', 'sv', 'sr', 'stt',
               'setst', 'hg', 'pose', 'hia', 'grip'])

    Y = 1600
    b.get('anim', 'Anim', 200, Y + 300); b.get('mon', 'Montage', 200, Y + 400)
    b.fn('valid', '/Script/Engine.KismetSystemLibrary:IsValid', 400, Y + 300); b.link('anim', 'Anim', 'valid', 'Object')
    b.node('vb', 'branch', 400, Y); b.link('valid', 'ReturnValue', 'vb', 'Condition'); b.chain(tick, 'vb')
    b.fn('playing', AI + 'Montage_IsPlaying', 600, Y + 300); b.link('anim', 'Anim', 'playing', 'self'); b.link('mon', 'Montage', 'playing', 'Montage')
    b.node('pb', 'branch', 700, Y); b.link('playing', 'ReturnValue', 'pb', 'Condition'); b.chain('vb', 'pb')
    b.get('pl', 'Player', 900, Y - 300)
    b.fn('end', PLAYER_C + ':EndGrip', 1000, Y - 400); b.link('pl', 'Player', 'end', 'self'); b.link('pb', 'else', 'end', 'execute')
    b.fn('die', ACT + 'K2_DestroyActor', 1300, Y - 400); b.chain('end', 'die'); b.link('vb', 'else', 'die', 'execute')
    b.fn('pos', AI + 'Montage_GetPosition', 900, Y + 300); b.link('anim', 'Anim', 'pos', 'self'); b.link('mon', 'Montage', 'pos', 'Montage')
    b.get('dt', 'Dt', 900, Y + 500)
    b.fn('f', K + 'Divide_DoubleDouble', 1100, Y + 400); b.link('pos', 'ReturnValue', 'f', 'A'); b.link('dt', 'Dt', 'f', 'B')
    b.fn('fl', K + 'FFloor', 1300, Y + 400); b.link('f', 'ReturnValue', 'fl', 'A')
    b.get('kc', 'KeyCount', 1300, Y + 600)
    b.fn('last', K + 'Subtract_IntInt', 1500, Y + 600, B=2); b.link('kc', 'KeyCount', 'last', 'A')
    b.fn('i0', K + 'Clamp', 1500, Y + 400, Min=0); b.link('fl', 'ReturnValue', 'i0', 'Value'); b.link('last', 'ReturnValue', 'i0', 'Max')
    b.fn('i1', K + 'Add_IntInt', 1700, Y + 500, B=1); b.link('i0', 'ReturnValue', 'i1', 'A')
    b.fn('i0f', K + 'Conv_IntToDouble', 1700, Y + 400); b.link('i0', 'ReturnValue', 'i0f', 'InInt')
    b.fn('fr', K + 'Subtract_DoubleDouble', 1900, Y + 400); b.link('f', 'ReturnValue', 'fr', 'A'); b.link('i0f', 'ReturnValue', 'fr', 'B')
    b.fn('al', K + 'FClamp', 2100, Y + 400, Min=0, Max=1); b.link('fr', 'ReturnValue', 'al', 'Value')
    x = 2300
    for arr in ('KeysA', 'KeysB', 'KeysW', 'KeysP'):
        item(arr + '0', arr, 'i0', x, Y + 700)
        item(arr + '1', arr, 'i1', x, Y + 850)
        x += 500
    for ref, arr, fn, y in (('la', 'KeysA', 'TLerp', 400), ('lb', 'KeysB', 'TLerp', 600), ('lw', 'KeysW', 'Lerp', 800), ('lp', 'KeysP', 'TLerp', 1000)):
        b.fn(ref, K + fn, 4300, Y + y)
        b.link(arr + '0', ITEM_PIN, ref, 'A'); b.link(arr + '1', ITEM_PIN, ref, 'B'); b.link('al', 'ReturnValue', ref, 'Alpha')
    b.fn('now', ACT + 'GetTransform', 4300, Y + 200); b.link('pl', 'Player', 'now', 'self')
    b.fn('aw', K + 'ComposeTransforms', 4600, Y + 300); b.link('la', 'ReturnValue', 'aw', 'A'); b.link('now', 'ReturnValue', 'aw', 'B')
    b.fn('hw', K + 'TLerp', 4900, Y + 400); b.link('aw', 'ReturnValue', 'hw', 'A'); b.link('lb', 'ReturnValue', 'hw', 'B'); b.link('lw', 'ReturnValue', 'hw', 'Alpha')
    b.get('hg2', 'Hanger', 4900, Y + 200)
    b.fn('place', SC + 'K2_SetWorldTransform', 1100, Y, bSweep='false', bTeleport='true')
    b.link('hg2', 'Hanger', 'place', 'self'); b.link('hw', 'ReturnValue', 'place', 'NewTransform'); b.link('pb', 'then', 'place', 'execute')
    b.get('px', 'Proxy', 4900, Y + 1000)
    b.fn('pplace', SC + 'K2_SetWorldTransform', 1400, Y, bSweep='false', bTeleport='true')
    b.link('px', 'Proxy', 'pplace', 'self'); b.link('lp', 'ReturnValue', 'pplace', 'NewTransform')
    b.get('hide', 'ProxyHideAt', 4900, Y + 1150)
    b.fn('shown', K + 'Less_DoubleDouble', 5100, Y + 1100); b.link('pos', 'ReturnValue', 'shown', 'A'); b.link('hide', 'ProxyHideAt', 'shown', 'B')
    b.fn('pvis', SC + 'SetVisibility', 1700, Y, bPropagateToChildren='false'); b.link('px', 'Proxy', 'pvis', 'self'); b.link('shown', 'ReturnValue', 'pvis', 'bNewVisibility')
    b.chain('place', 'pplace', 'pvis')
    b.get('slt', 'SlideTime', 5300, Y + 300)
    b.fn('sl', K + 'Divide_DoubleDouble', 5500, Y + 200); b.link('pos', 'ReturnValue', 'sl', 'A'); b.link('slt', 'SlideTime', 'sl', 'B')
    b.fn('slc', K + 'FClamp', 5700, Y + 200, Min=0, Max=1); b.link('sl', 'ReturnValue', 'slc', 'Value')
    b.fn('sm', K + 'FInterpEaseInOut', 5900, Y + 200, A=0, B=1, Exponent=2); b.link('slc', 'ReturnValue', 'sm', 'Alpha')
    b.get('ps', 'PawnStart', 5900, Y + 400); b.get('stt2', 'StanceT', 5900, Y + 500)
    b.fn('sx', K + 'TLerp', 6100, Y + 300); b.link('ps', 'PawnStart', 'sx', 'A'); b.link('stt2', 'StanceT', 'sx', 'B'); b.link('sm', 'ReturnValue', 'sx', 'Alpha')
    b.fn('sxb', K + 'BreakTransform', 6300, Y + 300); b.link('sx', 'ReturnValue', 'sxb', 'InTransform')
    b.fn('slend', K + 'Add_DoubleDouble', 1800, Y - 200, B=0.05); b.link('slt', 'SlideTime', 'slend', 'A')
    b.fn('sliding', K + 'Less_DoubleDouble', 2000, Y - 200); b.link('pos', 'ReturnValue', 'sliding', 'A'); b.link('slend', 'ReturnValue', 'sliding', 'B')
    b.node('sb', 'branch', 2000, Y); b.link('sliding', 'ReturnValue', 'sb', 'Condition'); b.chain('pvis', 'sb')
    b.fn('move', ACT + 'K2_SetActorLocationAndRotation', 2300, Y, bSweep='false', bTeleport='true')
    b.link('pl', 'Player', 'move', 'self'); b.link('sxb', 'Location', 'move', 'NewLocation'); b.link('sxb', 'Rotation', 'move', 'NewRotation')
    b.fn('ctrl', '/Script/Engine.Pawn:GetController', 2300, Y + 200); b.link('pl', 'Player', 'ctrl', 'self')
    b.fn('cr', '/Script/Engine.Controller:GetControlRotation', 2500, Y + 200); b.link('ctrl', 'ReturnValue', 'cr', 'self')
    b.fn('crb', K + 'BreakRotator', 2700, Y + 200); b.link('cr', 'ReturnValue', 'crb', 'InRot')
    b.fn('sxr', K + 'BreakRotator', 2700, Y + 350); b.link('sxb', 'Rotation', 'sxr', 'InRot')
    b.fn('ncr', K + 'MakeRotator', 2900, Y + 250, Roll=0); b.link('crb', 'Pitch', 'ncr', 'Pitch'); b.link('sxr', 'Yaw', 'ncr', 'Yaw')
    b.fn('setcr', '/Script/Engine.Controller:SetControlRotation', 2600, Y); b.link('ctrl', 'ReturnValue', 'setcr', 'self'); b.link('ncr', 'ReturnValue', 'setcr', 'NewRotation')
    b.link('sb', 'then', 'move', 'execute'); b.chain('move', 'setcr')
    b.comment('Follow the montage: the hanger along its keys (carried in his frame, then at the work), the proxy shirt, '
              'and the slide onto the stance while he kneels; when it stops, let go and go',
              ['anim', 'mon', 'valid', 'vb', 'playing', 'pb', 'pl', 'end', 'die', 'pos', 'dt', 'f', 'fl', 'kc', 'last', 'i0',
               'i1', 'i0f', 'fr', 'al', 'place', 'pplace', 'pvis', 'sb', 'move', 'setcr'])
    return b.run()
