"""House graph style for the player lane's Blueprint and AnimBlueprint graphs (editor-rules.md rule 8):
one titled comment box per functional group with "Show Bubble When Zoomed" + "Color Bubble" on, a one-line description
in Details, one colour per group, left-to-right flow, nodes on a grid so boxes stay snug and never overlap."""
import unreal

BEL = unreal.BlueprintEditorLibrary
PIN = unreal.BlueprintGraphPinLibrary
COLORS = {  # one colour per kind of group, muted so the monochrome project still reads calmly
    "input": unreal.LinearColor(0.20, 0.32, 0.55, 1.0),
    "state": unreal.LinearColor(0.42, 0.30, 0.14, 1.0),
    "camera": unreal.LinearColor(0.16, 0.42, 0.40, 1.0),
    "look": unreal.LinearColor(0.38, 0.22, 0.45, 1.0),
    "anim": unreal.LinearColor(0.22, 0.40, 0.20, 1.0),
    "util": unreal.LinearColor(0.30, 0.30, 0.30, 1.0),
}


def at(node, x, y):
    BEL.set_node_pos(node, unreal.IntPoint(int(x), int(y)))
    return node


def pin_in(node, name):
    p = BEL.find_input_pin(node, name)
    assert PIN.is_valid(p), f"no input pin '{name}' on {BEL.get_node_title(node)}: {[str(PIN.get_pin_name(x)) for x in BEL.list_input_pins(node)]}"
    return p


def pin_out(node, name):
    p = BEL.find_output_pin(node, name)
    assert PIN.is_valid(p), f"no output pin '{name}' on {BEL.get_node_title(node)}: {[str(PIN.get_pin_name(x)) for x in BEL.list_output_pins(node)]}"
    return p


def link(a, a_pin, b, b_pin):
    """a_pin/b_pin: pin name, or None for the exec 'then' -> 'execute' pair (or a node's single data pin)."""
    src = BEL.find_then_pin(a) if a_pin is None else pin_out(a, a_pin)
    dst = BEL.find_execute_pin(b) if b_pin is None else pin_in(b, b_pin)
    assert PIN.try_create_connection(src, dst), f"link failed {BEL.get_node_title(a)}.{a_pin} -> {BEL.get_node_title(b)}.{b_pin}"


def value(node, pin, v):
    assert PIN.set_pin_value(pin_in(node, pin), str(v)), f"bad value {v!r} for {pin}"


def box(ed, title, _details, nodes, kind, padding=40):
    """Snug comment around `nodes` with a short title only (the user's rule: no description text on graphs; the
    second argument is kept for the callers and ignored), bubble shown when zoomed out and tinted like the box."""
    assert len(title.split()) <= 5, f"title too long: {title}"
    c = ed.add_comment_to_nodes(title, nodes, padding)
    BEL.set_comment_color(c, COLORS[kind])
    for prop, v in (("font_size", 20), ("comment_bubble_visible_in_details_panel", True), ("color_comment_bubble", True)):
        c.set_editor_property(prop, v)
    return c


def function_graph(bp, name, params=()):
    """Edit-in-place function graph (editor-rules: never delete and recreate graphs): reuse it if present, clearing
    every node except the entry/result and its comments; add only missing input params; create it only if absent."""
    bge = unreal.BlueprintGraphEditor
    if name in [str(g) for g in BEL.list_graph_names(bp)]:
        ed = bge.get_graph_editor_by_name(bp, name)
        for n in ed.list_all_nodes():
            if n.get_class().get_name() not in ("K2Node_FunctionEntry", "K2Node_FunctionResult"):
                ed.remove_nodes([n])
        for c in list(ed.list_comment_nodes()):
            ed.remove_comment_node(c)
    else:
        ed = bge.create_and_edit_function_graph(bp, name)
        assert str(ed.get_graph().get_name()) == name, f"graph name taken: {ed.get_graph().get_name()}"
    entry = PIN.get_owning_node(ed.find_graph_entry_pin())
    have = {str(PIN.get_pin_name(p)) for p in BEL.list_output_pins(entry)}
    for pname, ptype in params:
        if pname not in have:
            ed.add_graph_input_parameter(pname, ptype)
    return ed, entry


def self_call(ed, fname, x, y):
    """Call one of this Blueprint's own functions. They come from the palette, and only after a Hayba compile has put
    them on the generated class (the by-path call API can't resolve Blueprint functions)."""
    hits = [str(a) for a in ed.list_available_nodes([]) if str(a).split("|")[-1].replace(" ", "") == fname]
    assert hits, f"no palette entry for own function {fname}: compile the Blueprint with Hayba first"
    n = ed.create_node_from_name(min(hits, key=len), unreal.Vector2D(x, y), [])
    assert BEL.get_node_title(n), f"empty node for {fname}"
    return at(n, x, y)


def ensure_variable(bp, name, pin_type, default=""):
    """Member variable with its default in the variable description (no CDO write: editor-rules 20:42)."""
    if name not in set(BEL.list_member_variable_names(bp, False)):
        ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "EventGraph")
        assert ed.add_member_variable(name, pin_type, default), f"could not add {name}"
