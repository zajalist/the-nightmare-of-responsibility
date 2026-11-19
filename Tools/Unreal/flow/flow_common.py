"""Shared names for the mech_flow lane (level flow, day rollover, persistence). Loaded by the flow builders:
    exec(open('P:/FoA/Tools/Unreal/flow/flow_common.py').read())
Builds on the UI lane's Blueprint graph helper (Tools/Unreal/ui/bp_graph.py: Graph, ptype, ensure_vars, ...)."""
import gc
import sys

import unreal

# Crash safety (20:29 crash): a failed earlier run must not leave Python wrappers alive into this run's compiles.
sys.last_type = sys.last_value = sys.last_traceback = None
gc.collect()
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())

EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
G = '/Game/FoA/Gameplay'
GI, SG, DIR = G + '/GI_FoA', G + '/SG_FoA', G + '/BP_BeatDirector'
PDA, BEATS = G + '/Beats/PDA_Beat', G + '/Beats'
BPI = G + '/BPI_Interactable'                     # mech_core
DREAM = '/Game/FoA/PostProcess/BP_DreamDirector'  # pp lane (presentation only)
ENC = G + '/Encounter/BP_Encounter'               # mech_encounter
GS, KSL, KML = '/Script/Engine.GameplayStatics', '/Script/Engine.KismetSystemLibrary', '/Script/Engine.KismetMathLibrary'
ARR, SET, MAP = '/Script/Engine.KismetArrayLibrary', '/Script/Engine.BlueprintSetLibrary', '/Script/Engine.BlueprintMapLibrary'
# editor-rules: rescan after an editor relaunch, and deselect before structural Blueprint edits
unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([G, '/Game/FoA/Characters/Player', '/Game/FoA/PostProcess'], True)
unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
STARTING_DAY = 18  # the phone shows 17 crossed-out days on the first morning
C_FLOW = unreal.LinearColor(0.32, 0.22, 0.42, 1)  # beat flow
C_DAY = unreal.LinearColor(0.36, 0.12, 0.10, 1)   # day rollover
C_CAM = unreal.LinearColor(0.10, 0.28, 0.26, 1)   # top-down camera and dream staging
C_DEV = unreal.LinearColor(0.30, 0.30, 0.30, 1)   # debug only


def _find_pin(node, name, want_output):
    """bp_graph's pin lookup (ignores spaces/underscores; a VariableSet's output is Output_Get) with a direction."""
    return Graph.pin(node, name, 'out' if want_output else 'in')


def con(a, b):
    assert PIN.try_create_connection(a, b), f'link failed {PIN.get_pin_name(a)} -> {PIN.get_pin_name(b)}'


def cls_path(path):
    return f"{path}.{path.rsplit('/', 1)[1]}_C"


def exists(path):
    """Right after an editor restart the asset registry may still be loading, so fall back to loading the asset."""
    return EAL.does_asset_exist(path) or unreal.load_asset(path) is not None


def make_bp(path, parent, factory=None):
    name, folder = path.rsplit('/', 1)[1], path.rsplit('/', 1)[0]
    bp = unreal.load_asset(path)
    if not bp:
        fac = factory or unreal.BlueprintFactory()
        if factory is None:
            fac.set_editor_property('parent_class', parent)
        bp = AT.create_asset(name, folder, None, fac)
    assert bp, path
    return bp


def palette(g, *needles, pins=()):
    squash = lambda s: s.replace(' ', '').lower()  # palette names mix "For Each Loop" and "CastToX" spellings
    hits = [str(n) for n in g.ed.list_available_nodes(list(pins)) if all(squash(k) in squash(str(n)) for k in needles)]
    assert hits, f'no palette node with {needles}'
    return min(hits, key=len)


def pnode(g, x, y, *needles, pins=()):
    """Palette node by name fragments (shortest match), e.g. pnode(g, 0, 0, 'ForEachLoop')."""
    n = g.ed.create_node_from_name(palette(g, *needles, pins=pins), V2(x, y), list(pins))
    assert n, needles
    return g.at(n, x, y)


def cast_to(g, cls_name, x, y):
    return pnode(g, x, y, 'CastTo' + cls_name)


def result_node(g):
    nodes = g.ed.list_nodes_of_class(unreal.K2Node_FunctionResult)
    return nodes[0] if nodes else g.ed.add_return_node()


def fn(bp_path, name, inputs=(), outputs=(), pure=False):
    """Function graph with an empty body and its entry at (0, 0). bp_graph reuses existing graphs (deleting and
    re-creating one gives it a suffixed name), so signatures are only set when the graph is first made."""
    g = FGraph.function(bp_path, name, pure=pure, inputs=inputs, outputs=outputs)
    g.at(entry_node(g), 0, 0)
    return g


def gi_ref(g, x, y):
    """GetGameInstance -> Cast to GI_FoA (impure cast; wire its exec)."""
    gi = g.call(f'{GS}:GetGameInstance', x, y + 160)
    c = cast_to(g, 'GI_FoA', x + 288, y)
    g.link(gi, 'ReturnValue', c, 'Object')
    return gi, c


def compile_bp(path):
    """Compile with no stale wrappers around: callers must not hold CDO or component-template wrappers here."""
    gc.collect()
    BEL.compile_blueprint(unreal.load_asset(path))


def save(*paths):
    for p in paths:
        if isinstance(unreal.load_asset(p), unreal.Blueprint):
            compile_bp(p)
        print('saved', p, EAL.save_loaded_asset(unreal.load_asset(p), False))


LIFT = 40  # room for the one-line title above the top row of nodes


class FGraph(Graph):
    """bp_graph.Graph whose comment boxes carry only a short title (the user's rule: 2 to 5 words, no description
    sentences) and grow upward by LIFT, so the title never sits on the first row of nodes."""

    def literal(self, value, x, y):  # literals bp_graph adds under promotable operators join the next comment box
        n = super().literal(value, x, y)
        self.__dict__.setdefault('_lits', []).append(n)
        return n

    def comment(self, title, desc, nodes, color=C_LOGIC, padding=32):
        """desc is kept in the builder source as the developer note; the graph shows the title alone."""
        assert 2 <= len(title.split()) <= 5, f'comment title must be 2 to 5 words: {title!r}'
        nodes = list(nodes) + [n for n in self.__dict__.pop('_lits', []) if n not in nodes]
        c = self.ed.add_comment_to_nodes(title, nodes, padding)
        try:  # comment nodes aren't K2 nodes: read their own rectangle, then re-create it lifted
            x, y = c.get_editor_property('node_pos_x'), c.get_editor_property('node_pos_y')
            w, h = c.get_editor_property('node_width'), c.get_editor_property('node_height')
            self.ed.remove_comment_node(c)
            c = self.ed.add_comment_node(title, V2(x, y - LIFT), V2(w, h + LIFT))
        except Exception:  # rectangle not readable: keep the padded box
            pass
        BEL.set_comment_color(c, color)
        house_comment_flags(c)
        return c


def report(bp_path):
    """Compiler errors and warnings per graph (after save(), which compiled), so a build never passes silently."""
    bp = unreal.load_asset(bp_path)
    for name in BEL.list_graph_names(bp):
        ed = GE.get_graph_editor_by_name(bp, str(name))
        if not ed:
            continue
        for kind, nodes in (('ERROR', ed.list_nodes_with_errors()), ('WARNING', ed.list_nodes_with_warnings())):
            for n in nodes:
                print(kind, bp_path.rsplit('/', 1)[1], name, BEL.get_node_title(n))


# ---- Class defaults (crash safety, 20:29 and 20:37 crashes): Python touching a Blueprint's CDO or instances and then
# compiling that Blueprint again in the same editor session crashed the editor. So each builder compiles first, then
# writes defaults, then saves WITHOUT compiling, and nothing compiles that Blueprint again in the session.
NOTEBOOK = {  # knowledge flag -> its phone notebook line (the notebook lists lines in the order they were learned)
    'Knows.ClothingThread': 'Thread in the wardrobe, goes to the desk.',
    'Knows.ClothingTrail': 'Button under the papers. Marks to the bed.',
    'Knows.ClothingSnag': "Shirt's under the bed. Use the hanger.",
    'Knows.KeyInBoot': "Key's in my left boot. Under the bed.",
    'Knows.KeySnaps': "The key snaps. Don't bother with it.",
    'Knows.ScrewdriverInDesk': 'Screwdriver on the desk.',
    'Knows.WardrobeFalls': "Don't pull the handle. The wardrobe comes down.",
    'Knows.DoorMoves': "The door moves. Don't trust it.",
    'Knows.ShirtPattern': 'The shirt hides the armhole first. Find it, then button.',
}
PHONE_TASKS = ('Wake up', 'Get dressed', 'Leave the house', 'Find a job')
BEAT_IDS = [f'T{i}' for i in range(11)]


def set_defaults(path, values):
    """Class defaults, written after this run's last compile of the Blueprint; the CDO wrapper is dropped at once."""
    cdo = unreal.get_default_object(unreal.load_asset(path).generated_class())
    for k, v in values.items():
        cdo.set_editor_property(k, v)
    del cdo


def save_nocompile(*paths):
    gc.collect()
    for p in paths:
        print('saved (no compile)', p, EAL.save_loaded_asset(unreal.load_asset(p), False))


def subobjects(bp):
    sds, lib = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem), unreal.SubobjectDataBlueprintFunctionLibrary
    hs = sds.k2_gather_subobject_data_for_blueprint(bp)
    return sds, lib, hs, {str(lib.get_variable_name(lib.get_data(h))): h for h in hs}
