"""Graph helpers for the encounter lane, on top of the UI lane's bp_graph.py (house comment style, Graph class).
Use from a script run via ue_remote.py:  exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py').read())"""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())

KSL, GS, KML = '/Script/Engine.KismetSystemLibrary', '/Script/Engine.GameplayStatics', '/Script/Engine.KismetMathLibrary'
KAL, BML, KTL = '/Script/Engine.KismetArrayLibrary', '/Script/Engine.BlueprintMapLibrary', '/Script/Engine.KismetTextLibrary'
KIL, UWBL = '/Script/Engine.KismetInputLibrary', '/Script/UMG.WidgetBlueprintLibrary'
ENC = '/Game/FoA/Gameplay/Encounter'
MOVE_C = f'{ENC}/PDA_Move.PDA_Move_C'
OPP_C = f'{ENC}/PDA_Opponent.PDA_Opponent_C'
COL = {  # one colour per kind of group, shared by every encounter graph
    'entry': unreal.LinearColor(0.10, 0.20, 0.35, 1), 'turn': unreal.LinearColor(0.18, 0.18, 0.18, 1),
    'input': unreal.LinearColor(0.30, 0.22, 0.10, 1), 'data': unreal.LinearColor(0.12, 0.26, 0.16, 1),
    'outcome': unreal.LinearColor(0.32, 0.12, 0.12, 1), 'stage': unreal.LinearColor(0.22, 0.14, 0.34, 1),
}


def _cat(p):
    """'exec', 'delegate' or the data type, from the pin's display string (EdGraphPinType fields aren't exposed)."""
    t = str(PIN.get_pin_type_display_string(p)).lower()
    return 'exec' if t.startswith('exec') else ('delegate' if 'delegate' in t else t)


def _find(node, name, out):
    """Pin by name; falls back to space-insensitive matching (macro pins: LoopBody vs "Array Element") and to 'then'
    for latent nodes whose exec output shows as Completed."""
    p = (BEL.find_output_pin if out else BEL.find_input_pin)(node, name)
    if PIN.is_valid(p):
        return p
    key = name.lower().replace(' ', '')
    pins = BEL.list_output_pins(node) if out else BEL.list_input_pins(node)
    for p in pins:
        if str(PIN.get_pin_name(p)).lower().replace(' ', '') == key:
            return p
    if out and name == 'Completed':
        p = BEL.find_then_pin(node)
        if PIN.is_valid(p):
            return p
    raise AssertionError(f"no {'output' if out else 'input'} {name} on {BEL.get_node_title(node)}: "
                         f"{[str(PIN.get_pin_name(x)) for x in pins]}")


def pi(node, name):
    return _find(node, name, False)


def po(node, name=None):
    """Output pin by name, or the node's first data output (ReturnValue, a getter, a Set's pass-through)."""
    if name:
        return _find(node, name, True)
    for p in BEL.list_output_pins(node):
        if _cat(p) not in ('exec', 'delegate'):
            return p
    raise AssertionError('no data output on ' + BEL.get_node_title(node))


def wire(a, b):
    assert PIN.try_create_connection(a, b), f"wire {PIN.get_pin_name(a)} -> {PIN.get_pin_name(b)}"


def _exec_pin(node, out):
    """First exec pin on that side; macros (ForEachLoop) name theirs Exec/LoopBody so find_then/execute miss them."""
    p = BEL.find_then_pin(node) if out else BEL.find_execute_pin(node)
    if PIN.is_valid(p):
        return p
    for p in (BEL.list_output_pins(node) if out else BEL.list_input_pins(node)):
        if _cat(p) == 'exec':
            return p
    raise AssertionError(f"no exec {'output' if out else 'input'} on {BEL.get_node_title(node)}")


def go(a, b, a_pin=None):
    """Exec a -> b ('then' unless a_pin names another exec output such as 'else' or 'Completed')."""
    wire(_exec_pin(a, True) if a_pin is None else po(a, a_pin), _exec_pin(b, False))


def chain(*nodes):
    for a, b in zip(nodes, nodes[1:]):
        go(a, b)


def impure(node):
    return node is not None and PIN.is_valid(BEL.find_execute_pin(node))


def seq(*nodes):
    """Exec-chain the impure nodes among these, skipping pure ones and None. Data providers whose purity is unsure
    (Map Keys, GetActorOfClass, Random Array Item...) go in here: off the exec path the compiler prunes impure nodes
    and they return None (editor-rules, maintenance section). Returns the last chained node."""
    live = [n for n in nodes if n is not None and (impure(n) or PIN.is_valid(BEL.find_then_pin(n)))]
    chain(*live)
    return live[-1]


def val(node, pin, v):
    assert PIN.set_pin_value(pi(node, pin), str(v)), f"value {pin}={v!r} on {BEL.get_node_title(node)}"


def feed(node, **pins):
    """Connect data inputs: pin=<output pin> or pin=<node> (its first data output), or set a literal default."""
    for k, v in pins.items():
        if isinstance(v, unreal.BlueprintGraphPin):
            wire(v, pi(node, k))
        elif isinstance(v, unreal.EdGraphNode):
            wire(po(v), pi(node, k))
        else:
            val(node, k, v)
    return node


_PALETTE = {}  # graph path -> palette entries: listing the palette costs seconds, so do it once per graph per run


def palette(g, *needles, ctx=()):
    norm = lambda t: t.lower().replace(' ', '')  # noqa: E731  palette titles space words out ("Call On Changed")
    key = g.ed.get_graph().get_path_name() if not ctx else None
    entries = _PALETTE.get(key) if key else None
    if entries is None:
        entries = [str(a) for a in g.ed.list_available_nodes(list(ctx))]
        if key:
            _PALETTE[key] = entries
    hits = [a for a in entries if all(norm(n) in norm(a) for n in needles)]
    assert hits, f"no palette node with {needles}"
    return min(hits, key=len)


def make(g, x, y, *needles, ctx=()):
    n = g.ed.create_node_from_name(palette(g, *needles, ctx=ctx), unreal.Vector2D(x, y), list(ctx))
    assert n, needles
    return g.at(n, x, y)


def as_pin(cast):
    """A cast node's typed output ("AsGI FoA" and the like: the exact spacing varies by class name)."""
    return [p for p in BEL.list_output_pins(cast) if str(PIN.get_pin_name(p)).startswith('As')][0]


def fcall(g, path, x, y, **pins):
    return feed(g.call(path, x, y), **pins)


def mget(g, var, x, y, cls_path=''):
    """Member variable getter; with cls_path it reads another class's variable (Target pin)."""
    return g.at(g.ed.add_get_member_variable_node(var, cls_path), x, y)


def field(g, obj, var, cls_path, x, y):
    """obj.var for a data asset (PDA_Move / PDA_Opponent): getter wired to the object pin."""
    n = mget(g, var, x, y, cls_path)
    wire(obj if isinstance(obj, unreal.BlueprintGraphPin) else po(obj), pi(n, 'self'))
    return n


def mset(g, var, x, y, src=None):
    n = g.at(g.ed.add_set_member_variable_node(var, ''), x, y)
    if src is not None:
        feed(n, **{var: src})
    return n


def box(g, title, desc, nodes, kind, pad=40):
    """House comment: a 2-5 word title only (the user's rule: no description sentences on graphs); desc stays here in
    the builder as the note for whoever edits it. One colour per group, bubble readable when zoomed out."""
    c = g.ed.add_comment_to_nodes(title, list(nodes), pad)
    BEL.set_comment_color(c, COL[kind])
    for prop, v in (("font_size", 18), ("comment_bubble_visible_in_details_panel", True), ("color_comment_bubble", True)):
        c.set_editor_property(prop, v)
    return c


def result_node(g):
    return g.ed.list_nodes_of_class(unreal.K2Node_FunctionResult)[0]


def new_function(bp_path, name, inputs=(), outputs=(), pure=False):
    """A function graph, edited in place (editor-rules: never delete and recreate graphs): created with its parameters
    the first time; on later runs its nodes are cleared, keeping the entry and one result node. Returns
    (Graph, entry, result-or-None)."""
    bp = unreal.load_asset(bp_path)
    if name in [str(n) for n in BEL.list_graph_names(bp)]:
        g = Graph(bp_path, name)
        for c in list(g.ed.list_comment_nodes()):
            g.ed.remove_comment_node(c)
        entry = entry_node(g)
        results = list(g.ed.list_nodes_of_class(unreal.K2Node_FunctionResult))
        keep = {entry.get_name()} | ({results[0].get_name()} if results else set())
        g.ed.remove_nodes([n for n in g.ed.list_all_nodes() if n.get_name() not in keep])
    else:
        GE.create_and_edit_function_graph(bp, name)
        g = Graph(bp_path, name)
        for n, t in inputs:
            g.ed.add_graph_input_parameter(n, t, '')
        for n, t in outputs:
            g.ed.add_graph_output_parameter(n, t)
    if pure:
        g.ed.set_is_pure_function(True)
    res = result_node(g) if outputs else None
    return g, entry_node(g), res


def ensure_vars_nc(bp_path, specs):
    """specs: (name, pin_type, default_str, category, instance_editable[, expose_on_spawn]). Adds only missing
    variables (the default applies on creation) and never compiles: compiles go through Hayba blueprint_compile."""
    bp = unreal.load_asset(bp_path)
    ed = GE.get_graph_editor_by_name(bp, 'EventGraph')
    have = [str(n) for n in BEL.list_member_variable_names(bp)]
    for spec in specs:
        name, t, val_, cat, editable = spec[:5]
        if name not in have:
            assert ed.add_member_variable(name, t, val_), f"add var {name}"
        BEL.set_blueprint_variable_category(bp, name, cat)
        BEL.set_blueprint_variable_instance_editable(bp, name, editable)
        BEL.set_blueprint_variable_expose_on_spawn(bp, name, bool(spec[5]) if len(spec) > 5 else False)


def stub_functions(bp_path, sigs):
    """Create every missing function graph with its parameters (empty), so a Hayba compile makes them callable before
    any graph that calls them is filled. sigs: name -> (inputs, outputs, pure)."""
    bp = unreal.load_asset(bp_path)
    have = [str(n) for n in BEL.list_graph_names(bp)]
    for name, (ins, outs, pure) in sigs.items():
        if name not in have:
            new_function(bp_path, name, ins, outs, pure)


def event_key(name):
    return name.replace(' ', '').replace('_', '').lower()


def event_name(node):
    """A custom event's name, normalised by event_key (its title is spaced: 'Intro Step', 'S Intro'); else ''."""
    if isinstance(node, unreal.K2Node_CustomEvent):
        return event_key(BEL.get_node_title(node).splitlines()[0])
    return ''


def stub_events(bp_path, names):
    """Custom events that don't exist yet, parked in a column at the far left of the event graph."""
    g = Graph(bp_path)
    have = {event_name(n) for n in g.ed.list_all_nodes()}
    for i, name in enumerate(names):
        if event_key(name) not in have:
            g.custom_event(name, -2400, i * 200)

