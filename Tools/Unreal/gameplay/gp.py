"""Graph helpers for the mech_core builders (editor Python via ue_remote.py). House style per editor-rules.md rule 8:
titled comment boxes with "Show Bubble When Zoomed" + "Color Bubble", one colour per kind of group, left-to-right flow.
    import importlib, sys; sys.path.insert(0, "P:/FoA/Tools/Unreal/gameplay"); import gp; importlib.reload(gp)"""
import unreal

BEL, GE, PIN = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor, unreal.BlueprintGraphPinLibrary
EAL = unreal.EditorAssetLibrary
D = "/Game/FoA/Gameplay"
BPI = D + "/BPI_Interactable.BPI_Interactable_C"
KSL, KML, GS, KTL = ("/Script/Engine." + c for c in ("KismetSystemLibrary", "KismetMathLibrary", "GameplayStatics",
                                                      "KismetTextLibrary"))
KAL = "/Script/Engine.KismetArrayLibrary"
MACROS = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:"
COLORS = {  # muted, one per kind of group, same palette as the player lane
    "event": (0.20, 0.32, 0.55), "logic": (0.30, 0.30, 0.30), "state": (0.42, 0.30, 0.14),
    "data": (0.16, 0.42, 0.40), "fx": (0.38, 0.22, 0.45), "out": (0.22, 0.40, 0.20),
}


def T(kind):
    """Pin type by short name, or a struct asset / class."""
    if isinstance(kind, str):
        return BEL.get_basic_type_by_name(kind)
    if isinstance(kind, unreal.UserDefinedStruct) or isinstance(kind, unreal.ScriptStruct):
        return BEL.get_struct_type(kind)
    if hasattr(kind, "static_struct"):  # native structs such as unreal.Transform
        return BEL.get_struct_type(kind.static_struct())
    return BEL.get_object_reference_type(kind)


def asset(name):
    return unreal.load_asset(f"{D}/{name}")


def gen(name):
    return asset(name).generated_class()


def close(bp):
    """Before structural edits: nothing selected, the asset's editors closed (editor-rules, structural edits)."""
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)


def save(*objs):
    for o in objs:
        assert EAL.save_loaded_asset(o, False), o


def ensure_vars(bp, specs, category):
    """specs: (name, pin type, default string, instance editable)."""
    have = [str(n) for n in BEL.list_member_variable_names(bp, False)]
    ed = GE.get_graph_editor(BEL.find_event_graph(bp))
    for name, t, default, editable in specs:
        if name not in have:
            assert ed.add_member_variable(name, t, default), name
        BEL.set_blueprint_variable_instance_editable(bp, name, editable)
        BEL.set_blueprint_variable_category(bp, name, category)


def ensure_dispatcher(bp, name, params):
    if name not in [str(d) for d in BEL.list_event_dispatchers(bp)]:
        assert BEL.add_event_dispatcher(bp, name), name
        for n, t in params:
            BEL.add_event_dispatcher_parameter(bp, name, n, t)


def sig(inputs=(), outputs=(), pure=False, const=False, locals_=()):
    return dict(inputs=inputs, outputs=outputs, pure=pure, const=const, locals_=locals_)


def declare(bp, sigs, events=()):
    """Create every function graph (and custom events) before any body, then compile, so calls resolve."""
    for name, s in sigs.items():
        if name not in [str(g) for g in BEL.list_graph_names(bp)]:
            G.function(bp, name, **s)
    ev = G(bp)
    for e in events:
        ev.custom(e, 0, -2000)
    BEL.compile_blueprint(bp)


class G:
    """One graph being built. Every builder clears its own graph first, so reruns are idempotent."""

    def __init__(self, bp, graph="EventGraph", ed=None):
        self.bp = bp
        self.ed = ed or GE.get_graph_editor_by_name(bp, graph)
        self.pending = {}
        assert self.ed, f"{bp.get_name()} has no graph {graph}"
        self.nodes = []

    @classmethod
    def function(cls, bp, name, inputs=(), outputs=(), pure=False, const=False, locals_=()):
        """Create a function graph, or clear an existing one in place. Never remove and recreate a graph with the
        same name in one session: that crashed the editor (access violation in BlueprintEditorLibrary, 18:20)."""
        if name in [str(g) for g in BEL.list_graph_names(bp)]:
            g = cls(bp, name).clear()
            have = [str(PIN.get_pin_name(p)) for p in BEL.list_output_pins(g.entry_node())]
            missing = [n for n, _ in inputs if n not in have]
            assert not missing, f"{name}: existing graph lacks inputs {missing}; rename the function to change it"
        else:
            g = cls(bp, name, GE.create_and_edit_function_graph(bp, name))
            for n, t in inputs:
                g.ed.add_graph_input_parameter(n, t)
            for n, t in outputs:
                g.ed.add_graph_output_parameter(n, t)
        have_locals = list(g.ed.list_local_variable_names())
        for n, t, v in locals_:
            if n not in have_locals:
                g.ed.add_local_variable(n, t, v)
        if pure:
            g.ed.set_is_pure_function(True)
        if const:
            g.ed.set_is_const_function(True)
        return g

    def entry_node(self):
        return PIN.get_owning_node(self.ed.find_graph_entry_pin())

    def clear(self):
        """Remove every node and comment except the entry and the first result node (it carries the outputs)."""
        for c in list(self.ed.list_comment_nodes()):
            self.ed.remove_comment_node(c)
        results = list(self.ed.list_nodes_of_class(unreal.K2Node_FunctionResult))
        # Custom events stay (re-adding a removed name is what crashed the editor); their links are cut instead.
        keep = results[:1] + list(self.ed.list_nodes_of_class(unreal.K2Node_CustomEvent))
        nodes = [n for n in self.ed.list_all_nodes()
                 if not isinstance(n, unreal.K2Node_FunctionEntry) and n not in keep]
        if nodes:
            self.ed.remove_nodes(nodes)
        for n in keep:  # cut its old links so the rebuild wires it fresh
            for p in BEL.list_all_pins(n):
                PIN.break_pin_links(p)
        return self

    def at(self, node, x, y):
        assert node, "node creation failed"
        BEL.set_node_pos(node, unreal.IntPoint(int(x), int(y)))
        self.nodes.append(node)
        return node

    # ---- node makers ----
    def entry(self, x=0, y=0):
        return self.at(PIN.get_owning_node(self.ed.find_graph_entry_pin()), x, y)

    def ret(self, x, y):
        found = list(self.ed.list_nodes_of_class(unreal.K2Node_FunctionResult))
        return self.at(found[0] if found else self.ed.add_return_node(), x, y)

    def ret_new(self, x, y):
        return self.at(self.ed.add_return_node(), x, y)

    def event(self, name, x, y):
        n = BEL.add_event_override(self.bp, name, unreal.IntPoint(int(x), int(y)))
        return self.at(n or self.ed.find_event_node(name) or self.pal(x, y, "Event", name), x, y)

    def custom(self, name, x, y):
        for n in self.ed.list_nodes_of_class(unreal.K2Node_CustomEvent):
            if BEL.get_node_title(n).splitlines()[0].replace(" ", "") == name:
                return self.at(n, x, y)
        return self.at(self.ed.add_custom_event_node(name), x, y)

    def call(self, path, x, y, **values):
        n = self.at(self.ed.add_call_function_node(path), x, y)
        for k, v in values.items():
            self.val(n, k, v)
        return n

    def selfcall(self, func, x, y, owner=None, **values):
        bp = owner or self.bp
        return self.call(f"{bp.generated_class().get_path_name()}:{func}", x, y, **values)

    def macro(self, name, x, y):
        return self.at(self.ed.add_macro_node(MACROS + name), x, y)

    def get(self, var, x, y, cls=""):
        return self.at(self.ed.add_get_member_variable_node(var, cls), x, y)

    def set(self, var, x, y, cls="", value=None):
        n = self.at(self.ed.add_set_member_variable_node(var, cls), x, y)
        if value is not None:
            self.val(n, var, value)
        return n

    def lget(self, var, x, y):
        return self.at(self.ed.add_get_local_variable_node(var), x, y)

    def lset(self, var, x, y, value=None):
        n = self.at(self.ed.add_set_local_variable_node(var), x, y)
        if value is not None:
            self.val(n, var, value)
        return n

    def branch(self, x, y):
        return self.at(self.ed.add_branch_node(), x, y)

    def palette(self, *needles):
        """Exact palette entry containing every needle (spaces ignored, case-insensitive); shortest wins."""
        flat = lambda t: t.replace(" ", "").replace("_", "").lower()  # palette shows "S_Item" as "S Item"
        key = [flat(n) for n in needles]
        hits = [str(a) for a in self.ed.list_available_nodes([]) if all(k in flat(str(a)) for k in key)]
        assert hits, f"no palette node with {needles}"
        if len(hits) > 1:
            print("palette", needles, "->", min(hits, key=len), "of", sorted(hits, key=len)[:4])
        return min(hits, key=len)

    def pal(self, x, y, *needles):
        entry = self.palette(*needles)
        return self.at(self.ed.create_node_from_name(entry, unreal.Vector2D(x, y), []), x, y)

    def msg(self, func, x, y):
        """Interface message node (works on any Actor, no cast)."""
        return self.pal(x, y, "Interactable", func, "Message")

    # ---- pins ----
    @staticmethod
    def pin(node, name, out=None):
        pins = BEL.list_output_pins(node) if out else BEL.list_input_pins(node) if out is False else BEL.list_all_pins(node)
        for p in pins:  # FNames are case-insensitive: Branch pins are "then"/"else"
            if str(PIN.get_pin_name(p)).lower() == name.lower():
                return p
        raise KeyError(f"{BEL.get_node_title(node)} has no pin {name}: {[str(PIN.get_pin_name(p)) for p in BEL.list_all_pins(node)]}")

    @staticmethod
    def out(node):
        """The single data output (ReturnValue, a getter, a Set pass-through...)."""
        for p in BEL.list_output_pins(node):
            if str(PIN.get_pin_name(p)) not in ("then", "execute", "OutputDelegate"):
                return p
        raise KeyError("no data output on " + BEL.get_node_title(node))

    def link(self, a, a_pin, b, b_pin):
        """a_pin None = exec out ('then'); b_pin None = exec in. a_pin '' = a's single data output."""
        src = BEL.find_then_pin(a) if a_pin is None else self.out(a) if a_pin == "" else self.pin(a, a_pin, True)
        dst = BEL.find_execute_pin(b) if b_pin is None else self.pin(b, b_pin, False)
        assert PIN.try_create_connection(src, dst), \
            f"link failed {BEL.get_node_title(a)}.{a_pin} -> {BEL.get_node_title(b)}.{b_pin}"
        if self.pending:
            self.settle(a)
            self.settle(b)

    def chain(self, *nodes):
        for a, b in zip(nodes, nodes[1:]):
            self.link(a, None, b, None)

    def val(self, node, pin, v, defer=True):
        if isinstance(v, bool):
            v = "true" if v else "false"
        v = str(v)
        if v == "None":  # Name pins already default to None; setting it again reports failure
            return
        p = self.pin(node, pin, False)
        ok = PIN.set_pin_value(p, v) or str(PIN.get_pin_value(p)).lower() == v.lower()
        if not ok and defer:
            # UE 5.8 turns +, <, * and friends into promotable operators whose pins stay wildcards until linked;
            # the value lands once a link types the node (see link).
            self.pending.setdefault(node.get_name(), (node, {}))[1][pin] = v
            return
        assert ok, f"{BEL.get_node_title(node)}.{pin} = {v!r} (now {PIN.get_pin_value(p)!r})"

    def settle(self, node):
        entry = self.pending.pop(node.get_name(), None)
        if entry:
            leftover = {k: v for k, v in entry[1].items() if not self._try(entry[0], k, v)}
            if leftover:
                self.pending[node.get_name()] = (entry[0], leftover)

    def _try(self, node, pin, v):
        p = self.pin(node, pin, False)
        return PIN.set_pin_value(p, v) or str(PIN.get_pin_value(p)).lower() == v.lower()

    def unsettled(self):
        return {BEL.get_node_title(n): vals for n, vals in self.pending.values()}

    # ---- exec helpers ----
    @staticmethod
    def impure(node):
        return PIN.is_valid(BEL.find_execute_pin(node))

    def flow(self, *nodes):
        """Exec-chain the nodes that have exec pins, skipping pure ones (impure nodes must be on the exec path,
        or the compiler prunes them and they return None)."""
        ex = [n for n in nodes if self.impure(n) or PIN.is_valid(BEL.find_then_pin(n))]
        for a, b in zip(ex, ex[1:]):
            self.link(a, None, b, None)

    def loop(self, array_node, array_pin, x, y, idx="Index"):
        """Index loop from plain nodes (no macros: script-made macro nodes crashed the editor at 19:30).
        Needs an int local `idx`. Returns (start, branch, element, step): exec into `start`; the body hangs off
        branch "Then" and must end in `step`, which jumps back to the branch; branch "Else" is the exit."""
        start = self.lset(idx, x, y, value=0)
        n_len = self.call(KAL + ":Array_Length", x + 40, y + 200)
        self.link(array_node, array_pin, n_len, "TargetArray")
        more = self.call(KML + ":Less_IntInt", x + 280, y + 200)
        self.link(self.lget(idx, x + 80, y + 300), "", more, "A")
        self.link(n_len, "ReturnValue", more, "B")
        br = self.branch(x + 500, y)
        self.link(start, None, br, None)
        self.link(more, "ReturnValue", br, "Condition")
        elem = self.call(KAL + ":Array_Get", x + 500, y + 200)
        self.link(array_node, array_pin, elem, "TargetArray")
        self.link(self.lget(idx, x + 300, y + 400), "", elem, "Index")
        inc = self.call(KML + ":Add_IntInt", x + 500, y + 520, B=1)
        self.link(self.lget(idx, x + 300, y + 520), "", inc, "A")
        step = self.lset(idx, x + 760, y + 520)
        self.link(inc, "ReturnValue", step, idx)
        self.link(step, None, br, None)  # the back edge
        return start, br, elem, step

    # ---- house comment ----
    def box(self, title, desc, nodes, kind, pad=40):
        """House style: a 2 to 5 word title only (the user's rule: no description sentences on graphs); `desc` stays
        in the builder source as the maintainer's note. Bubble shown when zoomed, tinted like the box."""
        assert not self.pending, f"pin values never landed: {self.unsettled()}"
        c = self.ed.add_comment_to_nodes(title, list(nodes), pad)
        BEL.set_comment_color(c, unreal.LinearColor(*COLORS[kind], 1.0))
        for k, v in (("font_size", 20), ("comment_bubble_visible_in_details_panel", True),
                     ("color_comment_bubble", True)):
            c.set_editor_property(k, v)
        return c

    def errors(self):
        return [BEL.get_node_title(n) for n in self.ed.list_nodes_with_errors()]


def find_pin_name(node, friendly):
    """User-defined struct pins are named <Friendly>_<n>_<GUID>; find the real name."""
    for p in BEL.list_all_pins(node):
        n = str(PIN.get_pin_name(p))
        if n == friendly or n.startswith(friendly + "_"):
            return n
    raise KeyError(f"{BEL.get_node_title(node)} has no pin like {friendly}")


def cast_out(node):
    """A cast node's typed output ("AsBP Fo APlayer" and friends)."""
    for p in BEL.list_output_pins(node):
        if str(PIN.get_pin_name(p)).startswith("As"):
            return str(PIN.get_pin_name(p))
    raise KeyError("no As* pin on " + BEL.get_node_title(node))


def ret_pin(node):
    """First data output (an interface message's return value)."""
    for p in BEL.list_output_pins(node):
        if str(PIN.get_pin_name(p)) not in ("then", "execute"):
            return str(PIN.get_pin_name(p))
    raise KeyError("no output on " + BEL.get_node_title(node))


def capture(bp, graphs, prefix):
    """Queue graph PNGs (written ~1.5 s after the script returns)."""
    shots = []
    for g in graphs:
        png = f"P:/FoA/Saved/GraphShots/{prefix}_{g}.png"
        unreal.FoAGraphToolsLibrary.capture_graph_png(bp, g, png, True)
        shots.append(png)
    return shots
