"""Tiny builder over UE 5.8's BlueprintGraphEditor Python API, for laying out readable Blueprint graphs.
Import from scripts run via Tools/Unreal/ue_remote.py:  exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
Every builder script clears the graph it owns and rebuilds it, so reruns are idempotent.
Compiles go through Hayba (editor-rules, "Blueprint compiles go through Hayba"): scripts only add and wire nodes and
save. Each script prints HAYBA lines at the end; replay them in order (blueprint_compile / ui_compile_widget, then
blueprint_set_defaults for class defaults, then asset_save). Python never compiles and never writes a CDO."""
import unreal

BEL = unreal.BlueprintEditorLibrary
PIN = unreal.BlueprintGraphPinLibrary
GE = unreal.BlueprintGraphEditor

# Comment colours by role, so every graph in the project reads the same way.
C_EVENT = unreal.LinearColor(0.10, 0.20, 0.35, 1)   # entry points (events, dispatch)
C_LOGIC = unreal.LinearColor(0.18, 0.18, 0.18, 1)   # state and flow
C_VISUAL = unreal.LinearColor(0.30, 0.22, 0.10, 1)  # visuals, materials, audio
C_DATA = unreal.LinearColor(0.12, 0.26, 0.16, 1)    # settings, save data


def P(x, y):
    return unreal.IntPoint(int(x), int(y))


def V2(x, y):
    return unreal.Vector2D(float(x), float(y))


_EDITORS = {}  # function-graph editors created this run (lookup by name can miss brand-new graphs)


class Graph:
    def __init__(self, bp_path, graph="EventGraph"):
        self._pending = []
        self.bp = unreal.load_asset(bp_path)
        assert self.bp, bp_path
        # Crash safety: never mutate a graph that is open in its asset editor.
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(self.bp)
        self.ed = _EDITORS.get((bp_path, graph)) or GE.get_graph_editor_by_name(self.bp, graph)
        if not self.ed:
            found = BEL.find_graph(self.bp, graph)
            self.ed = GE.get_graph_editor(found) if found else None
        assert self.ed, f"{bp_path} has no graph {graph}"

    @classmethod
    def function(cls, bp_path, name, pure=False, inputs=(), outputs=()):
        """Get-or-create a function graph and clear its body (entry/result kept). Re-creating a removed graph gets a
        suffixed name (the old graph object still owns the name), so graphs are reused instead of deleted."""
        import re
        bp = unreal.load_asset(bp_path)
        names = [str(n) for n in BEL.list_graph_names(bp)]
        for n in names:  # stale duplicates from earlier delete-and-recreate runs
            if re.fullmatch(re.escape(name) + r'_\d+', n):
                BEL.remove_function_graph(bp, n)
        if name in names:
            g = cls(bp_path, name)
            keep = set(g.ed.list_nodes_of_class(unreal.K2Node_FunctionEntry)) | set(
                g.ed.list_nodes_of_class(unreal.K2Node_FunctionResult)[:1])
            for c in list(g.ed.list_comment_nodes()):
                g.ed.remove_comment_node(c)
            rest = [n for n in g.ed.list_all_nodes() if n not in keep]
            if rest:
                g.ed.remove_nodes(rest)
            return g
        _EDITORS[(bp_path, name)] = GE.create_and_edit_function_graph(bp, name)
        g = cls(bp_path, name)
        for n, t in inputs:
            g.ed.add_graph_input_parameter(n, t)
        for n, t in outputs:
            g.ed.add_graph_output_parameter(n, t)
        if pure:
            g.ed.set_is_pure_function(True)
        return g

    def clear(self):
        for c in list(self.ed.list_comment_nodes()):
            self.ed.remove_comment_node(c)
        nodes = list(self.ed.list_all_nodes())
        if nodes:
            self.ed.remove_nodes(nodes)
        return self

    def at(self, node, x, y):
        BEL.set_node_pos(node, P(x, y))
        return node

    def event(self, name, x, y):
        return self.at(BEL.add_event_override(self.bp, name, P(x, y)), x, y)

    def custom_event(self, name, x, y):
        return self.at(self.ed.add_custom_event_node(name), x, y)

    def call(self, func_path, x, y, **defaults):
        raw = self.ed.add_call_function_node(func_path)
        if not raw:  # a blueprint's own (just-created) functions resolve through the palette, not by path
            fname = func_path.rsplit(':', 1)[1]
            hits = sorted((n for n in self.ed.list_available_nodes([])
                           if n.rsplit('|', 1)[-1].replace(' ', '') == fname), key=len)
            raw = self.ed.create_node_from_name(hits[0], V2(x, y), []) if hits else None
        assert raw, f"no function {func_path}"
        n = self.at(raw, x, y)
        for i, (k, v) in enumerate(defaults.items()):
            self.default(n, k, v, i)
        return n

    def literal(self, value, x, y):
        """MakeLiteral* node for a constant operand (bool, int, float or Name)."""
        kind = ('Bool' if isinstance(value, bool) else 'Int' if isinstance(value, int) else
                'Double' if isinstance(value, float) else 'Name')
        raw = self.ed.add_call_function_node(f'/Script/Engine.KismetSystemLibrary:MakeLiteral{kind}')
        assert raw, kind
        n = self.at(raw, x, y)
        assert PIN.set_pin_value(self.pin(n, 'Value', 'in'), str(value).lower() if kind == 'Bool' else str(value))
        return n

    def node(self, palette_name, x, y):
        n = self.ed.create_node_from_name(palette_name, V2(x, y), [])
        assert n, palette_name
        return self.at(n, x, y)

    def get(self, var, x, y, class_path=""):
        return self.at(self.ed.add_get_member_variable_node(var, class_path), x, y)

    def set(self, var, x, y, class_path=""):
        return self.at(self.ed.add_set_member_variable_node(var, class_path), x, y)

    def branch(self, x, y):
        return self.at(self.ed.add_branch_node(), x, y)

    def reroute(self, x, y):
        return self.node("|AddRerouteNode...", x, y)

    @staticmethod
    def pin(node, name, direction=None):
        """Pin by name, ignoring spaces/underscores (casts expose 'AsSG Fo ASettings'); direction 'out'/'in' picks
        the side when a node has both (a VariableSet's output is 'Output_Get')."""
        if node.get_class().get_name() == 'K2Node_IfThenElse':
            name = {'True': 'then', 'False': 'else'}.get(name, name)
        norm = lambda t: str(t).replace(' ', '').replace('_', '').lower()  # noqa: E731
        want = norm(name)
        out = unreal.EdGraphPinDirection.EGPD_OUTPUT
        pins = list(BEL.list_all_pins(node))
        hits = [p for p in pins if norm(PIN.get_pin_name(p)) == want]
        if direction:
            side = [p for p in hits if (PIN.get_pin_direction(p) == out) == (direction == 'out')]
            if not side and direction == 'out' and node.get_class().get_name() == 'K2Node_VariableSet':
                side = [p for p in pins if str(PIN.get_pin_name(p)) == 'Output_Get']
            hits = side or hits
        if hits:
            return hits[0]
        names = [str(PIN.get_pin_name(p)) for p in pins]
        raise KeyError(f"{node.get_name()} has no pin {name}; pins: {names}")

    def link(self, a, a_pin, b, b_pin):
        ok = PIN.try_create_connection(self.pin(a, a_pin, 'out'), self.pin(b, b_pin, 'in'))
        assert ok, f"link failed {a.get_name()}.{a_pin} -> {b.get_name()}.{b_pin}"
        for item in [x for x in self._pending if x[0] in (a, b)]:
            if PIN.set_pin_value(self.pin(item[0], item[1], 'in'), str(item[2])):
                self._pending.remove(item)

    def exec_chain(self, *nodes):
        """Wire then->execute left to right through a list of nodes (events use 'then' too)."""
        for a, b in zip(nodes, nodes[1:]):
            self.link(a, "then", b, "execute")

    def default(self, node, pin_name, value, slot=0):
        """Literal on an input pin. Promotable operators (+, /, ==) ignore literals on wildcard pins, so they get an
        explicit MakeLiteral node wired in instead (placed under the operator)."""
        if node.get_class().get_name() == 'K2Node_PromotableOperator':
            pos = BEL.get_node_pos(node)
            lit = self.literal(value, pos.x, pos.y + 144 + slot * 80)
            self.link(lit, 'ReturnValue', node, pin_name)
            return
        ok = PIN.set_pin_value(self.pin(node, pin_name, 'in'), str(value))
        assert ok, f"default failed {node.get_name()}.{pin_name}={value}"

    def comment(self, title, desc, nodes, color=C_LOGIC, padding=32):
        """House style (the user's rule): the box shows only a 2-5 word title, big bubble readable zoomed out.
        desc stays in the build script as the note for readers of the code; it is not written into the graph."""
        assert 2 <= len(title.split()) <= 5, f"comment title must be 2-5 words: {title!r}"
        c = self.ed.add_comment_to_nodes(title, list(nodes), padding)
        BEL.set_comment_color(c, color)
        house_comment_flags(c)
        return c


def words(name):
    """CamelCase function name -> a comment title: 'OnSplashFinished' -> 'On splash finished'."""
    import re
    w = re.findall(r'[A-Z][a-z0-9]*|[a-z0-9]+', name)
    return ' '.join([w[0]] + [x.lower() for x in w[1:]])


def house_comment_flags(c):
    for prop, val in (("comment_bubble_visible_in_details_panel", True), ("color_comment_bubble", True),
                      ("font_size", 18)):
        try:
            c.set_editor_property(prop, val)
        except Exception as e:  # property names differ between comment classes; report, don't hide
            print("comment flag", prop, "not set:", e)


def lint_exec(bp):
    """Impure call nodes with no incoming exec are pruned by the compiler and silently return defaults."""
    bad = []
    for graph in BEL.list_graphs(bp):
        ed = GE.get_graph_editor(graph)
        for n in ed.list_all_nodes() if ed else []:
            if n.get_class().get_name() not in ('K2Node_CallFunction', 'K2Node_DynamicCast', 'K2Node_MacroInstance'):
                continue
            ex = [p for p in BEL.list_all_pins(n) if str(PIN.get_pin_name(p)) == 'execute']
            if ex and not PIN.list_connected_pins(ex[0]):
                bad.append(f"{graph.get_name()}:{n.get_name()}")
    if bad:
        print('UNWIRED_EXEC', bad)


def hayba(name, **args):
    """Queue a Hayba call for the operator to replay after this script ends: one JSON line in FOA_HAYBA_QUEUE when
    hayba_replay sets it (the editor caps a run's printed output, which cut long call lists), else printed."""
    import json
    import os
    q = os.environ.get("FOA_HAYBA_QUEUE")
    if q:
        with open(q, "a", encoding="utf-8") as fh:
            print(json.dumps({"cmd": name, "params": args}), file=fh)
    else:
        print("HAYBA", name, json.dumps(args))


def compile_save(bp_path, defaults=None):
    """Lint, compile in-process, and save only a clean compile; a failed compile is NOT saved and raises (11-10: the old
    save-before-compile step wrote a broken BP_ViewFill to disk). The Hayba compile / defaults / save lines are still
    queued after it, so hayba_replay.py callers work as before (and replay also skips the save of a failed compile)."""
    bp = unreal.load_asset(bp_path)
    lint_exec(bp)
    widget = isinstance(bp, unreal.WidgetBlueprint)
    BEL.compile_blueprint(bp)
    status = bp.get_editor_property("status")
    if status not in (unreal.BlueprintStatus.BS_UP_TO_DATE, unreal.BlueprintStatus.BS_UP_TO_DATE_WITH_WARNINGS):
        print("NOT SAVED: compile failed", bp_path, status)
        raise RuntimeError(f"compile failed, not saved: {bp_path} ({status})")
    ok = unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    print("compiled and saved", bp_path, ok)
    if widget:
        hayba("ui_compile_widget", widget_blueprint_path=bp_path)
    else:
        hayba("blueprint_compile", path=bp_path)
    for k, v in (defaults or {}).items():  # one property per line: the run's output truncates long lines (~300 chars)
        hayba("blueprint_set_defaults", path=bp_path, properties={k: v})
    hayba("asset_save", asset_paths=[bp_path])


def var_flags(bp_path, name, category=None, instance_editable=True, expose_on_spawn=False, tooltip=None):
    bp = unreal.load_asset(bp_path)
    BEL.set_blueprint_variable_instance_editable(bp, name, instance_editable)
    BEL.set_blueprint_variable_expose_on_spawn(bp, name, expose_on_spawn)
    if category:
        BEL.set_blueprint_variable_category(bp, name, category)


# ---- shared helpers for the UI lane's builders ----
def ptype(kind):
    """Pin types by short name: bool/real/int/name/text, or a UClass/UScriptStruct for refs and structs."""
    if isinstance(kind, str):
        return BEL.get_basic_type_by_name(kind)
    if hasattr(kind, 'static_struct'):
        return BEL.get_struct_type(kind.static_struct())
    return BEL.get_object_reference_type(kind)


def class_ref(cls):
    return BEL.get_class_reference_type(cls)


def ensure_vars(bp_path, specs):
    """specs: (name, pin_type, default_str, category, instance_editable[, expose_on_spawn]). Adds only missing vars."""
    bp = unreal.load_asset(bp_path)
    ed = GE.get_graph_editor_by_name(bp, 'EventGraph')
    have = [str(n) for n in BEL.list_member_variable_names(bp)]
    for spec in specs:
        name, t, val, cat, editable = spec[:5]
        if name not in have:
            assert ed.add_member_variable(name, t, val), f"add var {name}"
        BEL.set_blueprint_variable_category(bp, name, cat)
        BEL.set_blueprint_variable_instance_editable(bp, name, editable)
        BEL.set_blueprint_variable_expose_on_spawn(bp, name, bool(spec[5]) if len(spec) > 5 else False)


def entry_node(g):
    return PIN.get_owning_node(g.ed.find_graph_entry_pin())


RETIRED = {'UpdateSand'}  # functions removed for good (tick-era); everything else is reused, never deleted


def drop_function(bp_path, name):
    """Removes suffixed duplicates of `name`, and `name` itself only if it is retired."""
    import re
    bp = unreal.load_asset(bp_path)
    for n in [str(x) for x in BEL.list_graph_names(bp)]:
        if re.fullmatch(re.escape(name) + r'_\d+', n) or (n == name and name in RETIRED):
            BEL.remove_function_graph(bp, n)


def override_graph(bp_path, name):
    """An EXISTING function-override graph (OnKeyDown, ...) emptied for a rebuild, or None. Never creates one:
    BlueprintEditorLibrary.add_function_override on Widget Blueprints crashed the editor (18:53; editor-rules)."""
    bp = unreal.load_asset(bp_path)
    if name not in [str(n) for n in BEL.list_graph_names(bp)]:
        print('MISSING override', name, 'on', bp_path, '- add it in the editor (Override menu); not created from script')
        return None
    g = Graph(bp_path, name)
    e = entry_node(g)
    keep = g.ed.list_nodes_of_class(unreal.K2Node_FunctionResult)[:1]  # one result node; rebuilds add their own extras
    for n in list(g.ed.list_all_nodes()):
        if n != e and n not in keep:
            g.ed.remove_nodes([n])
    return g


def self_call(bp_path, func):
    """Function path for calling one of this blueprint's own functions."""
    name = bp_path.rsplit('/', 1)[1]
    return f"{bp_path}.{name}_C:{func}"


def bind_event(g, source, source_pin, dispatcher, event_name, x, y):
    """'Bind Event to <dispatcher>' on source.source_pin, wired to a new custom event. Returns (bind_node, event)."""
    pin = g.pin(source, source_pin)
    want = 'bindeventto' + dispatcher.lower()
    names = [n for n in g.ed.list_available_nodes([pin]) if n.lower().replace(' ', '').endswith(want)]
    if not names:  # 5.8 hides some (other blueprints' dispatchers) under a pin context; the context-free list has them
        names = [n for n in g.ed.list_available_nodes([]) if n.lower().replace(' ', '').endswith(want)]
    assert names, f"no bind node for {dispatcher}"
    bind = g.ed.create_node_from_name(names[0], V2(x, y), [pin]) or g.ed.create_node_from_name(names[0], V2(x, y), [])
    g.at(bind, x, y)
    if not PIN.list_connected_pins(g.pin(bind, 'self')):
        g.link(source, source_pin, bind, 'self')
    ev = g.custom_event(event_name, x + 64, y + 192)
    g.link(ev, 'OutputDelegate', bind, 'Delegate')
    return bind, ev


def host_lookup(g, host_class_path, x, y):
    """Construct-time lookup of the BP_FoAFrontEnd in the level -> Host (one manager per level)."""
    find = g.call('/Script/Engine.GameplayStatics:GetActorOfClass', x, y + 160)
    g.default(find, 'ActorClass', host_class_path)
    names = [n for n in g.ed.list_available_nodes([]) if n.endswith('CastToBP_FoAFrontEnd')]
    cast = g.ed.create_node_from_name(names[0], V2(x + 352, y), [])
    g.at(cast, x + 352, y)
    seth = g.set('Host', x + 672, y)
    g.link(find, 'ReturnValue', cast, 'Object')
    g.link(find, 'then', cast, 'execute')   # GetActorOfClass is impure: unwired exec gets it pruned (returns None)
    g.link(cast, 'then', seth, 'execute')
    g.link(cast, 'AsBP_FoAFrontEnd', seth, 'Host')
    return find, cast, seth


def bind_function(g, source, source_pin, dispatcher, function_name, x, y):
    """'Bind Event to <dispatcher>' fed by a Create Event node pointing at an existing function with the
    delegate's signature (needed when the delegate has parameters, e.g. Slider.OnValueChanged(Value))."""
    pin = g.pin(source, source_pin)
    want = 'bindeventto' + dispatcher.lower()
    names = [n for n in g.ed.list_available_nodes([pin]) if n.lower().replace(' ', '').endswith(want)]
    if not names:  # 5.8 hides some (other blueprints' dispatchers) under a pin context; the context-free list has them
        names = [n for n in g.ed.list_available_nodes([]) if n.lower().replace(' ', '').endswith(want)]
    assert names, f"no bind node for {dispatcher}"
    bind = g.at(g.ed.create_node_from_name(names[0], V2(x, y), [pin]) or g.ed.create_node_from_name(names[0], V2(x, y), []), x, y)
    if not PIN.list_connected_pins(g.pin(bind, 'self')):
        g.link(source, source_pin, bind, 'self')
    dpin = g.pin(bind, 'Delegate')
    makers = [n for n in g.ed.list_available_nodes([dpin]) if n.replace(' ', '').lower().endswith('createevent')]
    assert makers, 'no Create Event node'
    mk = g.at(g.ed.create_node_from_name(makers[0], V2(x - 32, y + 192), [dpin]), x - 32, y + 192)
    if not PIN.list_connected_pins(dpin):
        g.link(mk, 'OutputDelegate', bind, 'Delegate')
    BEL.set_create_delegate_function(mk, function_name)
    return bind, mk
