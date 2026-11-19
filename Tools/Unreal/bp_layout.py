"""Deterministic auto-layout for Blueprint and Widget Blueprint graphs (editor-rules rule 8, the user's "fix org of all
bps"). Position-only: it moves nodes and refits comment boxes; it never adds, removes or rewires a node, except that it
deletes duplicate comment boxes (same text over the same nodes).

Rules it lays out by:
  - every exec chain runs left to right on one row; a branch's first outcome (True, Then 0) continues the row, the
    others (False, Then 1, early-out Returns) start their own rows below;
  - pure and data nodes sit below-left of the exec node that consumes them, never on the exec row;
  - at least 64 px between nodes, 96 px between exec nodes, everything on the 16 px grid, no overlaps;
  - each comment box is refitted around the nodes it held, with "Show Bubble When Zoomed" and "Color Bubble" on, and
    its text cut to the title; per-node comment bubbles are cleared (the user's title-only rule).

One Blueprint at a time, inside a lease on it, only once it compiles clean (HAYBA_AGENT_ID=<lane>):
    python Tools/Unreal/editor_lock.py acquire <lane> --assets /Game/FoA/Gameplay/BPC_Inventory
    python Tools/Unreal/bp_layout.py --apply /Game/FoA/Gameplay/BPC_Inventory [--dry-run]
    python Tools/Unreal/editor_lock.py release <lane>
--apply reads every graph through the engine's read-only T3D exporter, measures the real node sizes with Hayba
blueprint_measure_nodes, plans, then applies through Hayba only: blueprint_move_nodes, blueprint_remove_nodes
(duplicate boxes), object_set_property (titles, bubble flags, per-node comments), blueprint_fit_comments (real sizes),
blueprint_compile + asset_save (ui_compile_widget for widgets). The plan is saved as Saved/GraphLayout/<asset>.json.
Fallback for an editor without those Hayba tools: ue_remote.py on this script with FOA_BP_ASSETS=<asset> moves the
nodes from Python with estimated sizes, then replay that plan's "calls" with Hayba.
Self-test of the planner, outside the editor:
    python Tools/Unreal/bp_layout.py --selftest

Without blueprint_measure_nodes, node sizes are estimated from the T3D (class, title, pins, default widgets).
shortcut: no reroute knots are added for long data wires (that would rewire); add them if the coordinator allows it.
"""
import math
import os
import importlib
import re
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import graph_layout  # noqa: E402  (title_only is shared with the material tool)
importlib.reload(graph_layout)  # the editor keeps modules between runs

try:
    import unreal
except ImportError:  # the planner and its self-test run in plain Python
    unreal = None

GRID = 16
EXEC_GAP = 96    # between exec nodes on a row
GAP = 64         # every other gap (rule: >= 64)
BAND_GAP = 160   # between the rows of different events / entry points
PAD = 48         # comment padding around its nodes (rule: >= 40)
ROW = 26         # pin row height at 1:1


def snap(v):
    return int(round(v / GRID)) * GRID


def snap_up(v):
    return int(math.ceil(v / GRID - 1e-9)) * GRID


def snap_down(v):
    return int(math.floor(v / GRID + 1e-9)) * GRID


# ---------------------------------------------------------------- T3D parsing
def _split_top(s):
    """Splits 'a=1,b="x,y",c=(d,e)' on top-level commas, honouring quotes and parentheses."""
    out, cur, depth, quote, esc = [], [], 0, False, False
    for ch in s:
        if esc:
            cur.append(ch)
            esc = False
            continue
        if ch == "\\":
            cur.append(ch)
            esc = True
            continue
        if ch == '"':
            quote = not quote
        elif not quote and ch == "(":
            depth += 1
        elif not quote and ch == ")":
            depth -= 1
        if ch == "," and depth == 0 and not quote:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        out.append("".join(cur))
    return [p for p in out if p]


def _unquote(v):
    v = v.strip()
    return v[1:-1] if len(v) >= 2 and v[0] == v[-1] == '"' else v


def _pin(text):
    body = text[text.index("(") + 1:text.rindex(")")]
    kv = {}
    for part in _split_top(body):
        if "=" in part:
            k, v = part.split("=", 1)
            kv[k.strip()] = v.strip()
    links = []
    lt = kv.get("LinkedTo", "")
    if lt.startswith("("):
        links = [tuple(x.split()) for x in _split_top(lt[1:-1]) if len(x.split()) == 2]
    friendly = _unquote(kv.get("PinFriendlyName", ""))
    m = re.search(r'"([^"]*)"\s*\)\s*$', friendly)  # NSLOCTEXT("ns", "key", "Text") -> Text
    return dict(id=kv.get("PinId", ""), name=_unquote(kv.get("PinName", "")),
                label=(m.group(1) if m else friendly) or _unquote(kv.get("PinName", "")),
                out=kv.get("Direction", "") == '"EGPD_Output"' or kv.get("Direction", "") == "EGPD_Output",
                cat=_unquote(kv.get("PinType.PinCategory", "")), sub=_unquote(kv.get("PinType.PinSubCategoryObject", "")),
                hidden=kv.get("bHidden") == "True", advanced=kv.get("bAdvancedView") == "True",
                default=_unquote(kv.get("DefaultValue", "")) or _unquote(kv.get("DefaultObject", "")), links=links)


def parse_t3d(text):
    """{graph name: {node name: {cls, path, props, pins}}} from an engine T3D export (ObjectExporterT3D) of a
    Blueprint. Graphs nest their nodes; every object is declared once with its class, then defined with its
    properties and pins, so both passes merge by their nesting path. Top-level nodes land under graph ""."""
    objs, stack = {}, []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Begin Object"):
            stack.append(re.search(r'Name="([^"]+)"', line).group(1))
            o = objs.setdefault(tuple(stack), {"cls": "", "path": "", "props": {}, "pins": []})
            m = re.search(r"Class=(\S+)", line)
            p = re.search(r"ExportPath=\"[^']*'([^']+)'", line)
            o["cls"] = o["cls"] or (m.group(1).rsplit(".", 1)[-1] if m else "")
            o["path"] = o["path"] or (p.group(1) if p else "")
        elif line.startswith("End Object"):
            stack.pop()
        elif stack:
            o = objs[tuple(stack)]
            if line.startswith("CustomProperties Pin "):
                o["pins"].append(_pin(line))
            elif "=" in line:
                k, v = line.split("=", 1)
                o["props"].setdefault(k, v)
    graphs = {}
    for key, o in objs.items():
        if not o["cls"].startswith(("K2Node_", "EdGraphNode_")):
            continue
        if len(key) == 1:
            graphs.setdefault("", {})[key[0]] = o
        elif objs[key[:-1]]["cls"] == "EdGraph":  # Blueprint graphs; anim and state-machine graphs are skipped
            graphs.setdefault(key[-2], {})[key[-1]] = o
    return graphs


# ---------------------------------------------------------------- node size estimate
COMPACT_FUNCS = re.compile(r"^(EqualEqual|NotEqual|Add_|Subtract_|Multiply_|Divide_|Less|Greater|Not_|BooleanAND|"
                           r"BooleanOR|BooleanXOR|Conv_|Percent_|Array_Length|Array_Get|Abs|Max|Min|Clamp|"
                           r"Concat_StrStr|IsValid$)")


def _member(props, key):
    m = re.search(r'MemberName="([^"]+)"', props.get(key, ""))
    return m.group(1) if m else ""


def title_of(nd):
    c, p = nd["cls"], nd["props"]
    if c in ("K2Node_CallFunction", "K2Node_CallArrayFunction", "K2Node_CallParentFunction", "K2Node_Message"):
        return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", _member(p, "FunctionReference") or "Function")
    if c in ("K2Node_VariableGet", "K2Node_VariableSet"):
        return ("Set " if c.endswith("Set") else "") + (_member(p, "VariableReference") or "Var")
    if c == "K2Node_Event":
        return "Event " + _member(p, "EventReference").replace("Receive", "")
    if c == "K2Node_CustomEvent":
        return _unquote(p.get("CustomFunctionName", "Custom Event"))
    if c == "K2Node_FunctionResult":
        return "Return Node"
    if c == "K2Node_MacroInstance":
        m = re.search(r":(\w+)'", p.get("MacroGraphReference", ""))
        return m.group(1) if m else "Macro"
    if c in ("K2Node_DynamicCast", "K2Node_BreakStruct", "K2Node_MakeStruct"):
        m = re.search(r"\.(\w+)'?\"?$", p.get("TargetType", p.get("StructType", "")).strip('"\''))
        return {"K2Node_DynamicCast": "Cast To ", "K2Node_BreakStruct": "Break ", "K2Node_MakeStruct": "Make "}[c] + (
            m.group(1) if m else "")
    return re.sub(r"^K2Node_", "", c)


def _widget_w(pin):
    """Width of the default-value widget an unconnected input shows."""
    if pin["links"] or pin["cat"] in ("exec", "") or pin["out"]:
        return 0
    return {"bool": 28, "object": 168, "class": 168, "softobject": 168, "struct": 176, "byte": 120,
            "enum": 120, "text": 96, "string": 96, "name": 96}.get(pin["cat"], 72)


def estimate(nd):
    """Node box at 1:1: {w, h, top} (top = height of a pinned comment bubble above the node)."""
    c = nd["cls"]
    pins = [q for q in nd["pins"] if not q["hidden"]
            and not (q["advanced"] and "Hidden" in nd["props"].get("AdvancedPinDisplay", ""))]
    ins = [q for q in pins if not q["out"]]
    outs = [q for q in pins if q["out"]]
    has_exec = any(q["cat"] == "exec" for q in pins)
    title = title_of(nd)
    top = 0  # per-node comment bubbles are stripped (the user's title-only rule), so they take no room
    if c == "K2Node_Knot":
        return dict(w=32, h=32, top=0)
    func = _member(nd["props"], "FunctionReference")
    compact = c in ("K2Node_PromotableOperator", "K2Node_CommutativeAssociativeBinaryOperator", "K2Node_GetArrayItem",
                    "K2Node_Self") or (not has_exec and COMPACT_FUNCS.match(func or ""))
    if c == "K2Node_VariableGet" and len(pins) <= 1:  # the plain getter pill
        return dict(w=snap_up(7.5 * len(title) + 72), h=48, top=top)
    if compact:
        rows = max(len(ins), len(outs), 1)
        return dict(w=snap_up(max(112, 7 * len(title) + 64)), h=snap_up(ROW * rows + 24), top=top)
    rows = max(len(ins), len(outs), 1)
    title_h = 32 + (16 if c in ("K2Node_CallFunction", "K2Node_CallArrayFunction") and any(
        q["name"] == "self" for q in ins) else 0)
    in_w = max([7 * len(q["label"]) + _widget_w(q) for q in ins] or [0])
    out_w = max([7 * len(q["label"]) for q in outs] or [0])
    w = max(144, 7.5 * len(title) + 72, in_w + out_w + 88)
    return dict(w=snap_up(w), h=snap_up(title_h + ROW * rows + 16), top=top)


# ---------------------------------------------------------------- planner (pure Python)
def graph_of(parsed):
    """(nodes, exec_edges, data_edges, comments) from parse_t3d(); edges are (src, src_pin, dst, dst_pin)."""
    nodes, comments, pin_owner = {}, {}, {}
    for name, nd in parsed.items():
        p = nd["props"]
        x0, y0 = int(p.get("NodePosX", 0)), int(p.get("NodePosY", 0))
        if nd["cls"] == "EdGraphNode_Comment":
            raw = _unquote(p.get("NodeComment", "")).replace("\\r\\n", "\n").replace("\\n", "\n")
            comments[name] = dict(x0=x0, y0=y0, w0=int(p.get("NodeWidth", 400)), h0=int(p.get("NodeHeight", 100)),
                                  text=graph_layout.title_only(raw), text0=raw, font=int(p.get("FontSize", 18)),
                                  guid=p.get("NodeGuid", ""), path=nd["path"],
                                  bubbles=p.get("bCommentBubbleVisible_InDetailsPanel") == "True"
                                  and p.get("bColorCommentBubble") == "True")
            continue
        box = estimate(nd)
        execs = [q for q in nd["pins"] if q["cat"] == "exec" and not q["hidden"]]
        nodes[name] = dict(box, x0=x0, y0=y0, exec=bool(execs), title=title_of(nd), guid=p.get("NodeGuid", ""),
                           path=nd["path"], node_comment=bool(_unquote(p.get("NodeComment", ""))),
                           in_ids=[q["id"] for q in nd["pins"] if not q["out"]],
                           out_ids=[q["id"] for q in nd["pins"] if q["out"]])
        for q in nd["pins"]:
            pin_owner[q["id"]] = name
    exec_edges, data_edges = [], []
    for name, nd in parsed.items():
        if name not in nodes:
            continue
        for q in nd["pins"]:
            if not q["out"]:
                continue
            for dst, pid in q["links"]:
                if dst not in nodes or pin_owner.get(pid) != dst:
                    continue
                e = (name, nodes[name]["out_ids"].index(q["id"]), dst, nodes[dst]["in_ids"].index(pid))
                (exec_edges if q["cat"] == "exec" else data_edges).append(e)
    return nodes, sorted(set(exec_edges)), sorted(set(data_edges)), comments


def _pin_y(nd, i):
    return 40 + ROW * i  # title then pin rows; good enough for aligning wires


def holders(nodes, comments):
    """{node: [comment, ...]}: the boxes holding the node's top-left corner as authored, smallest first."""
    out = {}
    for n in nodes:
        hit = sorted((c["w0"] * c["h0"], cid) for cid, c in comments.items()
                     if c["x0"] <= nodes[n]["x0"] < c["x0"] + c["w0"] and c["y0"] <= nodes[n]["y0"] < c["y0"] + c["h0"])
        out[n] = [cid for _, cid in hit]
    return out


def plan(nodes, exec_edges, data_edges, comments):
    """Returns (pos {node: (x, y)}, boxes {comment: (x, y, w, h)}, deleted [comment], warnings [str])."""
    exec_nodes = sorted(n for n in nodes if nodes[n]["exec"])
    succ = {n: [] for n in nodes}
    preds = {n: [] for n in nodes}
    for s, sp, d, dp in exec_edges:
        succ[s].append((sp, nodes[d]["y0"], d))
        preds[d].append(s)
    for n in succ:
        succ[n] = [d for _, _, d in sorted(succ[n])]
    prods = {n: [] for n in nodes}
    cons = {n: [] for n in nodes}
    for s, sp, d, dp in data_edges:
        prods[d].append((dp, s, sp))
        cons[s].append((d, dp))

    # Rows: depth-first along exec wires; the first new successor continues the row, the others open rows below.
    row_of, rows, band_of, back = {}, [], [], set()
    on_path = set()

    def walk(n, r):
        row_of[n] = r
        rows[r].append(n)
        on_path.add(n)
        first = True
        for d in succ[n]:
            if d in on_path:
                back.add((n, d))
            if d in row_of:
                continue
            if first:
                walk(d, r)
                first = False
            else:
                rows.append([])
                band_of.append(band_of[r])
                walk(d, len(rows) - 1)
        on_path.discard(n)

    sys.setrecursionlimit(max(2000, 4 * len(nodes)))
    band = 0
    while True:
        left = [n for n in exec_nodes if n not in row_of]
        if not left:
            break
        roots = [n for n in left if not preds[n]] or left  # entry points first, then cycle-only nodes
        root = min(roots, key=lambda n: (nodes[n]["y0"], nodes[n]["x0"], n))
        rows.append([])
        band_of.append(band)
        walk(root, len(rows) - 1)
        band += 1

    # Pure trees: every pure producer chain hangs below-left of the first exec node that consumes it.
    tree_of, order = {}, []
    for r in rows:
        order += r
    for n in order:
        frontier, tree = [n], []
        while frontier:
            m = frontier.pop(0)
            for _, s, _ in sorted(prods[m]):
                if not nodes[s]["exec"] and s not in tree_of:
                    tree_of[s] = n
                    tree.append(s)
                    frontier.append(s)
        nodes[n]["tree"] = tree
    orphans = sorted(n for n in nodes if not nodes[n]["exec"] and n not in tree_of)

    def tree_layout(root):
        """Columns right to left by data depth from the root; returns ({node: (dx, dy)}, width, height)."""
        depth = {root: 0}
        for m in nodes[root]["tree"]:
            depth[m] = 1 + max(depth.get(c, 0) for c, _ in cons[m] if c in depth or c == root) if [
                c for c, _ in cons[m] if c in depth] else 1
        cols = {}
        for m in nodes[root]["tree"]:
            cols.setdefault(depth[m], []).append(m)
        off, right, height = {}, 0, 0
        for dcol in sorted(cols):
            col = sorted(cols[dcol], key=lambda m: (min([(off.get(c, (0, 0))[1], dp) for c, dp in cons[m]
                                                         if c in off or c == root] or [(0, 0)]), nodes[m]["y0"], m))
            w = max(nodes[m]["w"] for m in col)
            y = 0
            for m in col:
                y += nodes[m]["top"]
                off[m] = (right - w, y)
                y += nodes[m]["h"] + GAP
            height = max(height, y - GAP)
            right -= w + GAP
        return off, -right - GAP if off else 0, height

    trees = {n: tree_layout(n) for n in order}

    # x along each row: after every exec predecessor, and far enough right that this node's pure tree clears the
    # previous tree on the same row.
    x = {}
    indeg = {n: len([p for p in preds[n] if (p, n) not in back]) for n in exec_nodes}
    ready = sorted((n for n in exec_nodes if indeg[n] == 0), key=lambda n: (row_of[n], n))
    tree_right = {}
    done = []
    while ready:
        n = ready.pop(0)
        r = row_of[n]
        tw = trees[n][1]
        cand = [x[p] + nodes[p]["w"] + EXEC_GAP for p in preds[n] if p in x and (p, n) not in back]
        if r in tree_right and tw:
            cand.append(tree_right[r] + GAP + tw + GAP)
        if tw and not cand:
            cand.append(tw + GAP)
        x[n] = snap_up(max(cand)) if cand else 0
        if tw:
            tree_right[r] = x[n] - GAP
        done.append(n)
        for d in succ[n]:
            if d in indeg and (n, d) not in back:
                indeg[d] -= 1
                if indeg[d] == 0:
                    ready.append(d)
        ready.sort(key=lambda m: (row_of[m], m))
    for n in exec_nodes:  # anything left only by a cycle: after its row neighbour
        x.setdefault(n, 0)

    # y: rows stacked; each row is its exec nodes plus the band of pure trees under them.
    pos, y = {}, 0
    for r, row in enumerate(rows):
        if r and band_of[r] != band_of[r - 1]:
            y += BAND_GAP - GAP
        top = max(nodes[n]["top"] for n in row)
        exec_h = max(nodes[n]["h"] for n in row)
        tree_h = max(trees[n][2] for n in row)
        for n in row:
            pos[n] = (x[n], y + top)
            for m, (dx, dy) in trees[n][0].items():
                pos[m] = (x[n] - GAP + dx, y + top + exec_h + GAP + dy)
        y += top + exec_h + (GAP + tree_h if tree_h else 0) + GAP
    # Orphan pure nodes in a row under everything.
    cx = 0
    for m in orphans:
        pos[m] = (cx, y + nodes[m]["top"])
        cx += nodes[m]["w"] + GAP
    if orphans:
        y += max(nodes[m]["h"] + nodes[m]["top"] for m in orphans) + GAP
    pos = {n: (snap(px), snap(py)) for n, (px, py) in pos.items()}

    # Comments: refit each around the nodes it held; a duplicate (same text, same nodes) is deleted.
    member = holders(nodes, comments)
    held = {cid: sorted(n for n in nodes if cid in member[n]) for cid in comments}
    deleted, seen = [], {}
    for cid in sorted(comments, key=lambda c: (-len(held[c]), c)):
        key = (comments[cid]["text"].strip().lower(), tuple(held[cid]))
        if key in seen:
            deleted.append(cid)
        else:
            seen[key] = cid
    boxes, warnings = {}, []
    for cid in sorted(set(comments) - set(deleted)):
        ids = held[cid]
        c = comments[cid]
        if not ids:
            boxes[cid] = (0, snap_up(y), snap_up(c["w0"]), snap_up(c["h0"]))
            y += c["h0"] + GAP
            continue
        x0 = min(pos[n][0] for n in ids)
        y0 = min(pos[n][1] - nodes[n]["top"] for n in ids)
        x1 = max(pos[n][0] + nodes[n]["w"] for n in ids)
        y1 = max(pos[n][1] + nodes[n]["h"] for n in ids)
        title = snap_up(c["font"] * 1.5 * max(1, c["text"].count("\n") + 1) + 16)
        boxes[cid] = (snap_down(x0 - PAD), snap_down(y0 - PAD - title), snap_up(x1 + PAD) - snap_down(x0 - PAD),
                      snap_up(y1 + PAD) - snap_down(y0 - PAD - title))
    warnings += ["warn: exec wire %s->%s loops back" % e for e in sorted(back)]
    return pos, boxes, sorted(deleted), warnings


def problems(nodes, exec_edges, pos, boxes, held=None):
    """Rule breaks of a plan; entries starting "warn:" are cosmetic, the rest block applying it."""
    out = []
    rect = {n: (x, y - nodes[n]["top"], x + nodes[n]["w"], y + nodes[n]["h"]) for n, (x, y) in pos.items()}
    ids = sorted(rect)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            ra, rb = rect[a], rect[b]
            if ra[0] < rb[2] + GAP and rb[0] < ra[2] + GAP and ra[1] < rb[3] + GAP and rb[1] < ra[3] + GAP:
                out.append("nodes %s and %s closer than %d px" % (a, b, GAP))
        if pos[a][0] % GRID or pos[a][1] % GRID:
            out.append("%s off grid" % a)
    for s, _, d, _ in exec_edges:
        if s in rect and d in rect and not rect[s][2] < rect[d][0]:
            out.append("warn: exec wire %s->%s runs right to left" % (s, d))
    cids = sorted(boxes)
    for i, a in enumerate(cids):
        for b in cids[i + 1:]:
            ra = boxes[a]
            rb = boxes[b]
            if ra[0] < rb[0] + rb[2] and rb[0] < ra[0] + ra[2] and ra[1] < rb[1] + rb[3] and rb[1] < ra[1] + ra[3]:
                out.append("warn: comment boxes %s and %s overlap" % (a, b))
    return out


def hayba_graph_calls(path, graph, parsed_graph, rects=None):
    """Plans one graph and returns (Hayba calls, info), with nothing written from Python. rects: {node guid:
    [x, y, w, h]} from blueprint_measure_nodes, the real rendered sizes (else the estimates are used).
    Calls: blueprint_move_nodes, blueprint_remove_nodes for duplicate comment boxes, object_set_property for titles,
    bubble flags and per-node comment bubbles, then blueprint_fit_comments (real sizes, members as authored)."""
    nodes, ex, da, comments = graph_of(parsed_graph)
    if not nodes:
        return [], None
    for nd in nodes.values():
        r = (rects or {}).get(nd["guid"])
        if r:
            nd["w"], nd["h"] = snap_up(r[2]), snap_up(r[3])
    pos, boxes, deleted, warns = plan(nodes, ex, da, comments)
    issues = problems(nodes, ex, pos, boxes) + warns
    moves = [{"node_id": nodes[n]["guid"], "x": x, "y": y} for n, (x, y) in sorted(pos.items())
             if (x, y) != (nodes[n]["x0"], nodes[n]["y0"])]
    info = {"nodes": len(nodes), "measured": bool(rects), "moved": len(moves), "comments": len(boxes),
            "deleted": deleted, "problems": issues}
    if [i for i in issues if not i.startswith("warn:")]:
        return [], info
    gp = {"path": path, "graph_name": graph}
    calls = [{"name": "blueprint_move_nodes", "args": dict(gp, moves=moves)}] if moves else []
    if deleted:
        calls.append({"name": "blueprint_remove_nodes", "args": dict(gp, node_ids=[comments[c]["guid"] for c in deleted])})
    for c in sorted(boxes):
        props = {} if comments[c]["bubbles"] else {"bCommentBubbleVisible_InDetailsPanel": True,
                                                   "bColorCommentBubble": True}
        if comments[c]["text"] != comments[c]["text0"].split("\n")[0].strip():  # fit_comments keeps the 1st line
            props["NodeComment"] = comments[c]["text"]
        if props and comments[c]["path"]:  # graphs read through Hayba carry no object paths
            calls.append({"name": "object_set_property", "args": {"path": comments[c]["path"], "properties": props}})
    calls += [{"name": "object_set_property", "args": {"path": nodes[n]["path"], "properties": {
        "NodeComment": "", "bCommentBubbleVisible": False, "bCommentBubblePinned": False}}}
        for n in sorted(nodes) if nodes[n]["node_comment"] and nodes[n]["path"]]
    if boxes:
        owner = {n: next((c for c in hs if c in boxes), None) for n, hs in holders(nodes, comments).items()}
        members = {comments[c]["guid"]: [nodes[n]["guid"] for n in sorted(nodes) if owner[n] == c] for c in sorted(boxes)}
        calls.append({"name": "blueprint_fit_comments", "args": dict(gp, padding=PAD, title_only=True, members=members,
                                                                     resolve_overlaps=True)})
    return calls, info


# ---------------------------------------------------------------- self-test (no editor)
def selftest():
    def pin(pid, name, out=False, cat="exec", links=(), cls_default=""):
        d = '"EGPD_Output"' if out else '"EGPD_Input"'
        lt = "LinkedTo=(%s)," % "".join("%s %s," % l for l in links) if links else ""
        return ('CustomProperties Pin (PinId=%s,PinName="%s",PinToolTip="a, \\"quoted\\" (tip)",Direction=%s,'
                'PinType.PinCategory="%s",PinType.PinSubCategory="",%sbHidden=False,)' % (pid, name, d, cat, lt))

    def node(cls, name, x, y, pins, extra=""):
        return ('Begin Object Class=/Script/BlueprintGraph.%s Name="%s" ExportPath="/Script/BlueprintGraph.%s\'/Game/T.T:G.%s\'"\n'
                '   NodePosX=%d\n   NodePosY=%d\n%s   %s\nEnd Object\n' % (cls, name, cls, name, x, y, extra, "\n   ".join(pins)))

    # BPC_Inventory.Combine as in the user's screenshot: entry -> branch; True -> set -> return; False -> early return;
    # a Break SItem + == feeding the branch from under the chain; two stacked duplicate "Combine" comments.
    t3d = (node("K2Node_FunctionEntry", "Entry", 0, 0, [pin("e1", "then", True, links=[("Branch", "b0")]),
                                                        pin("e2", "A", True, "struct", [("Break", "k0")])],
                'FunctionReference=(MemberName="Combine")\n')
           + node("K2Node_BreakStruct", "Break", 200, 300, [pin("k0", "SItem", False, "struct", [("Entry", "e2")]),
                                                           pin("k1", "Id", True, "name", [("Eq", "q0")])])
           + node("K2Node_PromotableOperator", "Eq", 400, 280, [pin("q0", "A", False, "name", [("Break", "k1")]),
                                                               pin("q1", "B", False, "name"),
                                                               pin("q2", "ReturnValue", True, "bool", [("Branch", "b1")])])
           + node("K2Node_IfThenElse", "Branch", 300, 0, [pin("b0", "execute", links=[("Entry", "e1")]),
                                                          pin("b1", "Condition", False, "bool", [("Eq", "q2")]),
                                                          pin("b2", "then", True, links=[("Set", "s0")]),
                                                          pin("b3", "else", True, links=[("Ret2", "r20")])])
           + node("K2Node_VariableSet", "Set", 500, 0, [pin("s0", "execute", links=[("Branch", "b2")]),
                                                         pin("s1", "then", True, links=[("Ret1", "r10")]),
                                                         pin("s2", "Value", False, "int")],
                  'VariableReference=(MemberName="Count")\n   NodeComment="Counts every combine"\n')
           + node("K2Node_FunctionResult", "Ret1", 450, 20, [pin("r10", "execute", links=[("Set", "s1")])])
           + node("K2Node_FunctionResult", "Ret2", 460, 30, [pin("r20", "execute", links=[("Branch", "b3")])])
           + node("K2Node_VariableGet", "Orphan", 900, 900, [pin("o0", "Count", True, "int")])
           + 'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="C1" ExportPath="x\'/Game/T.T:G.C1\'"\n'
             '   NodePosX=-50\n   NodePosY=-80\n   NodeWidth=700\n   NodeHeight=500\n'
             '   NodeComment="Combine\\nMerges two items into one when the recipe matches."\nEnd Object\n'
           + 'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="C2" ExportPath="x\'/Game/T.T:G.C2\'"\n'
             '   NodePosX=-40\n   NodePosY=-70\n   NodeWidth=690\n   NodeHeight=490\n   NodeComment="Combine"\nEnd Object\n')
    # The engine exporter nests nodes in their graph and declares each object (with its class) before defining it.
    nested = parse_t3d('Begin Object Class=/Script/Engine.Blueprint Name="T" ExportPath="x\'/Game/T.T\'"\n'
                       '   Begin Object Class=/Script/Engine.EdGraph Name="Combine" ExportPath="x\'/Game/T.T:Combine\'"\n'
                       '      Begin Object Class=/Script/BlueprintGraph.K2Node_IfThenElse Name="Branch" '
                       'ExportPath="x\'/Game/T.T:Combine.Branch\'"\n      End Object\n   End Object\n'
                       '   Begin Object Name="Combine" ExportPath="x\'/Game/T.T:Combine\'"\n'
                       '      Begin Object Name="Branch" ExportPath="x\'/Game/T.T:Combine.Branch\'"\n'
                       '         NodePosX=48\n         ' + pin("b0", "execute") + '\n      End Object\n'
                       '   End Object\nEnd Object\n')
    assert list(nested) == ["Combine"] and nested["Combine"]["Branch"]["cls"] == "K2Node_IfThenElse", nested
    assert nested["Combine"]["Branch"]["props"]["NodePosX"] == "48" and len(nested["Combine"]["Branch"]["pins"]) == 1
    assert nested["Combine"]["Branch"]["path"] == "/Game/T.T:Combine.Branch"
    parsed = parse_t3d(t3d)[""]
    assert parsed["Branch"]["path"] == "/Game/T.T:G.Branch" and len(parsed["Branch"]["pins"]) == 4, parsed["Branch"]
    assert parsed["Branch"]["pins"][2]["links"] == [("Set", "s0")] and parsed["Branch"]["pins"][2]["out"]
    nodes, ex, da, comments = graph_of(parsed)
    assert ("Branch", 0, "Set", 0) in ex and ("Branch", 1, "Ret2", 0) in ex and ("Eq", 0, "Branch", 1) in da, (ex, da)
    pos, boxes, deleted, warns = plan(nodes, ex, da, comments)
    assert plan(nodes, ex, da, comments)[:3] == (pos, boxes, deleted), "not deterministic"
    bad = [p for p in problems(nodes, ex, pos, boxes) + warns]
    assert not bad, bad
    row = lambda n: pos[n][1]  # noqa: E731
    assert row("Entry") == row("Branch") == row("Set") == row("Ret1"), "main chain on one row"
    assert row("Ret2") > row("Branch") + nodes["Branch"]["h"], "early-out row below with its own Return"
    assert pos["Entry"][0] < pos["Branch"][0] < pos["Set"][0] < pos["Ret1"][0], "left to right"
    assert pos["Ret2"][0] > pos["Branch"][0] + nodes["Branch"]["w"], "early-out right of its branch"
    for p in ("Break", "Eq"):  # pure nodes below-left of their consumer, under the chain
        assert pos[p][1] >= row("Branch") + nodes["Branch"]["h"] + GAP and pos[p][0] + nodes[p]["w"] <= pos["Branch"][0]
    assert deleted == ["C2"] and set(boxes) == {"C1"}, (deleted, boxes)  # same title over the same nodes
    assert comments["C1"]["text"] == "Combine" and "recipe" in comments["C1"]["text0"], "title only"
    assert nodes["Set"]["node_comment"] and not nodes["Branch"]["node_comment"], "per-node comments get stripped"
    bx, by, bw, bh = boxes["C1"]
    for n in ("Entry", "Branch", "Set", "Ret1", "Ret2", "Break", "Eq"):
        assert bx + 40 <= pos[n][0] and pos[n][0] + nodes[n]["w"] <= bx + bw - 40, n
        assert by + 40 <= pos[n][1] and pos[n][1] + nodes[n]["h"] <= by + bh - 40, n
    assert pos["Orphan"][1] > max(pos[n][1] for n in pos if n != "Orphan"), "orphans under everything"
    assert estimate({"cls": "K2Node_Knot", "pins": [], "props": {}})["w"] == 32
    hc, info = hayba_graph_calls("/Game/T", "G", parsed)
    assert [c["name"] for c in hc] == ["blueprint_move_nodes", "blueprint_remove_nodes", "object_set_property",
                                       "object_set_property", "blueprint_fit_comments"], [c["name"] for c in hc]
    assert hc[2]["args"]["properties"] == {"bCommentBubbleVisible_InDetailsPanel": True, "bColorCommentBubble": True}
    assert hc[3]["args"] == {"path": "/Game/T.T:G.Set", "properties": {
        "NodeComment": "", "bCommentBubbleVisible": False, "bCommentBubblePinned": False}}, hc[3]
    assert hc[4]["args"]["padding"] >= 48 and hc[4]["args"]["title_only"] and info["deleted"] == ["C2"]
    calls = hayba_calls("/Game/B", False, [("/Game/B.B:G.C1", {"NodeWidth": 64})])
    assert [c["name"] for c in calls] == ["object_set_property", "blueprint_compile"], calls
    assert [c["name"] for c in hayba_calls("/Game/W", True, [])] == ["ui_compile_widget"]
    print("bp_layout selftest ok")


# ---------------------------------------------------------------- editor side
def export_t3d(obj):
    """Engine T3D export (UObjectExporterT3D) of an asset into a temp file. Read-only: unlike the clipboard path
    (FoAGraphToolsLibrary.export_nodes_text, banned) it never calls PrepareForCopying on the nodes."""
    import tempfile
    path = os.path.join(tempfile.gettempdir(), "foa_bp_layout.t3d")
    task = unreal.AssetExportTask()
    task.object = obj
    task.exporter = unreal.ObjectExporterT3D()
    task.filename = path
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    if not unreal.Exporter.run_asset_export_task(task):
        raise RuntimeError("bp_layout: T3D export of %s failed" % obj.get_path_name())
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    os.remove(path)
    return text


def hayba_calls(path, widget, comment_props):
    """The Hayba calls that finish a layout: object_set_property per comment box (position, size, bubble flags; the
    sizes are not script-visible), then a Hayba compile, which also saves (this path serves editors whose Hayba has no
    asset_save yet)."""
    calls = [{"name": "object_set_property", "args": {"path": p, "properties": props}} for p, props in comment_props]
    if widget:
        return calls + [{"name": "ui_compile_widget", "args": {"widget_blueprint_path": path, "save_on_success": True}}]
    return calls + [{"name": "blueprint_compile", "args": {"path": path}}]


def _remove(bp, graph, node):
    """Deletes a duplicate comment box, if this engine build's graph editor API can; else the caller reports it."""
    ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, graph)
    for name in ("remove_node", "delete_node", "destroy_node"):
        if hasattr(ed, name):
            getattr(ed, name)(node)
            return True
    return False


def layout_blueprint(asset, dry_run=False, only=None):
    """Lays out every Blueprint graph of one Blueprint or Widget Blueprint. Python only moves nodes (set_node_pos on
    closed graphs) and deletes duplicate comment boxes; it never compiles. Replay summary["calls"] with hayba_invoke
    right after this script ends: they refit the comment boxes, compile and save. A graph whose plan breaks a rule
    is left as it is. only: graph names to restrict to. The plan is written to Saved/GraphLayout/<asset name>.json."""
    import json
    if isinstance(asset, str):
        asset = unreal.load_asset(asset)
    if asset is None:
        return {"error": "asset not found"}
    path = asset.get_path_name().split(".")[0]
    if not dry_run:
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(asset)
    reuse = os.environ.get("FOA_BP_T3D")  # a fresh FOA_BP_EXPORT dump made under the same lease: skip the slow export
    if reuse and os.path.exists(reuse):
        with open(reuse, encoding="utf-8", errors="replace") as fh:
            parsed = parse_t3d(fh.read())
    else:
        parsed = parse_t3d(export_t3d(asset))
    summary, comment_props, changed = {"asset": path, "graphs": {}}, [], False
    for g in sorted(k for k in parsed if k and (not only or k in only)):
        nodes, ex, da, comments = graph_of(parsed[g])
        if not nodes:
            continue
        pos, boxes, deleted, warns = plan(nodes, ex, da, comments)
        issues = problems(nodes, ex, pos, boxes) + warns
        blocked = [i for i in issues if not i.startswith("warn:")]
        moved = [n for n, p in pos.items() if p != (nodes[n]["x0"], nodes[n]["y0"])]
        info = {"nodes": len(nodes), "moved": len(moved), "comments": len(boxes), "deleted": deleted, "problems": issues}
        summary["graphs"][g] = info
        if blocked:
            continue
        for cid, (x, y, w, h) in sorted(boxes.items()):
            props = {"NodePosX": x, "NodePosY": y, "NodeWidth": w, "NodeHeight": h,
                     "bCommentBubbleVisible_InDetailsPanel": True, "bColorCommentBubble": True}
            if comments[cid]["text"] != comments[cid]["text0"]:  # the user's rule: the title, nothing else
                props["NodeComment"] = comments[cid]["text"]
            comment_props.append((parsed[g][cid]["path"], props))
        comment_props += [(parsed[g][n]["path"], {"NodeComment": "", "bCommentBubbleVisible": False,
                                                  "bCommentBubblePinned": False})
                          for n in sorted(nodes) if nodes[n]["node_comment"]]  # no per-node comment bubbles
        changed = changed or bool(moved or boxes or deleted)
        if dry_run:
            continue
        for n in moved:
            unreal.BlueprintEditorLibrary.set_node_pos(unreal.find_object(None, parsed[g][n]["path"]),
                                                       unreal.IntPoint(*pos[n]))
        for cid in deleted:
            if not _remove(asset, g, unreal.find_object(None, parsed[g][cid]["path"])):
                info.setdefault("delete_pending", []).append(cid)
    summary["calls"] = hayba_calls(path, isinstance(asset, unreal.WidgetBlueprint), comment_props) if changed else []
    out_dir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "GraphLayout/"
    os.makedirs(out_dir, exist_ok=True)
    summary["plan_file"] = out_dir + asset.get_name() + ".json"
    with open(summary["plan_file"], "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    return summary


SAVED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Saved", "GraphLayout")


class IncompleteGraphSnapshot(RuntimeError):
    """The transport omitted graph data; no layout may be applied from it."""


def require_complete_snapshot(value, counts=()):
    def truncated(item):
        if isinstance(item, dict):
            return bool(item.get("_truncated")) or any(truncated(v) for v in item.values())
        return isinstance(item, list) and any(truncated(v) for v in item)

    if truncated(value):
        raise IncompleteGraphSnapshot("Native graph snapshot was truncated")
    for field, count in counts:
        received = len(value[field]) if isinstance(value.get(field), list) else None
        if received is None or value.get(count) != received:
            raise IncompleteGraphSnapshot("Incomplete native %s: received %s, expected %s" %
                                          (field, received, value.get(count)))


def from_hayba(inspect, measure):
    """parse_t3d()-shaped nodes for graph_of() from blueprint_inspect_graph (pins, edges) and blueprint_measure_nodes
    (real positions and sizes). Keyed by node GUID; no object paths, so comment flags are left as they are."""
    rect = {n["node_id"]: n for n in measure.get("nodes", [])}
    parsed = {}
    for nd in inspect.get("nodes", []):
        gid = nd["node_id"]
        m = rect.get(gid, {})
        r = m.get("rect") or [0, 0, 0, 0]
        props = {"NodePosX": str(r[0]), "NodePosY": str(r[1]), "NodeGuid": gid}
        if m.get("comment"):
            props.update(NodeWidth=str(r[2]), NodeHeight=str(r[3]), NodeComment=nd.get("title", ""),
                         bCommentBubbleVisible_InDetailsPanel="True", bColorCommentBubble="True")
        pins = [dict(id="%s.%s.%s" % (gid, p["name"], p["direction"]), name=p["name"], label=p["name"],
                     out=p["direction"] == "output", cat=p.get("type", ""), sub="", hidden=False, advanced=False,
                     default="", links=[]) for p in nd.get("pins", [])]
        parsed[gid] = {"cls": "EdGraphNode_Comment" if m.get("comment") else "K2Node", "path": "", "props": props,
                       "pins": pins}
    for e in inspect.get("edges", []):
        src = parsed.get(e["from_node"])
        for p in (src or {}).get("pins", []):
            if p["out"] and p["name"] == e["from_pin"]:
                p["links"].append((e["to_node"], "%s.%s.input" % (e["to_node"], e["to_pin"])))
    return parsed


def drive(path, dry_run=False, graph_names=None):
    """Outside the editor, inside your lease on `path`: read every graph through Hayba (blueprint_get_info,
    blueprint_inspect_graph, blueprint_measure_nodes: real node sizes), plan, and replay the plan through Hayba on one
    connection, stopping at the first failure. Nothing is written from Python and nothing is exported.
    Returns the summary, also saved as Saved/GraphLayout/<name>.json.
    graph_names restricts inspection and edits to exact names; None keeps all graphs.
    A missing explicitly requested graph fails before any layout is applied."""
    import json
    import hayba_call as hc
    name = path.rsplit("/", 1)[1]
    os.makedirs(SAVED, exist_ok=True)

    def data(cmd, params):
        try:
            r = hc.call(cmd, params, timeout=300)
        except OSError as err:  # a busy editor times out: report it, never half-apply
            raise RuntimeError("%s: editor did not answer (%s)" % (cmd, err))
        if not r.get("ok"):
            raise RuntimeError("%s failed: %s" % (cmd, r.get("error", r)))
        return r.get("data", r)

    summary, calls = {"asset": path, "graphs": {}}, []
    try:
        info = data("blueprint_get_info", {"path": path})
        if graph_names is None:
            require_complete_snapshot(info)
            graphs = ["EventGraph"] + [g for g in info.get("functions", []) if g != "EventGraph"]
        else:
            if isinstance(graph_names, str):
                raise RuntimeError("graph_names must be a collection of exact graph names")
            graphs = list(dict.fromkeys(graph_names))
            if any(not isinstance(g, str) or not g for g in graphs):
                raise RuntimeError("graph_names contains an invalid name")
            summary["requested_graphs"] = graphs
        for g in graphs:
            try:
                ins = data("blueprint_inspect_graph", {"path": path, "graph_name": g})
            except RuntimeError:
                if graph_names is not None:
                    raise
                continue  # e.g. a Blueprint without an event graph
            # Native inspection pages nodes and edges independently. Layout needs
            # every page, including comment boxes beyond the first 50 nodes.
            for kind, param in (("nodes", "offset"), ("edges", "edge_offset")):
                offset = ins.get("page", {}).get(kind, {}).get("next_offset")
                while offset is not None:
                    page = data("blueprint_inspect_graph", {"path": path, "graph_name": g, param: offset})
                    require_complete_snapshot(page)
                    ins[kind].extend(page[kind])
                    offset = page.get("page", {}).get(kind, {}).get("next_offset")
            require_complete_snapshot(ins, (("nodes", "node_count"), ("edges", "edge_count")))
            meas = data("blueprint_measure_nodes", {"path": path, "graph_name": g})
            page_info = meas.get("page", {})
            offset = page_info.get("nodes", page_info).get("next_offset")
            while offset is not None:
                page = data("blueprint_measure_nodes", {"path": path, "graph_name": g, "offset": offset})
                require_complete_snapshot(page)
                meas["nodes"].extend(page["nodes"])
                page_info = page.get("page", {})
                offset = page_info.get("nodes", page_info).get("next_offset")
            require_complete_snapshot(meas, (("nodes", "node_count"),))
            if {n["node_id"] for n in ins["nodes"]} != {n["node_id"] for n in meas["nodes"]}:
                raise IncompleteGraphSnapshot("Native inspection and measurement contain different nodes")
            parsed = from_hayba(ins, meas)
            rects = {n["node_id"]: n["rect"] for n in meas.get("nodes", []) if not n.get("comment")}
            gc, ginfo = hayba_graph_calls(path, g, parsed, rects)
            if ginfo:
                summary["graphs"][g] = dict(ginfo, measured=bool(meas.get("measured")))
                calls += gc
    except IncompleteGraphSnapshot as err:
        return dict(summary, error=str(err), incomplete_snapshot=True)
    except RuntimeError as err:
        return dict(summary, error=str(err))
    if calls:
        if "WidgetBlueprint" in str(info.get("parent_class", "")) or name.startswith("WBP_"):
            calls.append({"name": "ui_compile_widget", "args": {"widget_blueprint_path": path, "save_on_success": True}})
        else:
            calls += [{"name": "blueprint_compile", "args": {"path": path}},
                      {"name": "asset_save", "args": {"asset_paths": [path]}}]
    summary["calls"] = calls
    if calls and not dry_run:
        with hc.connect(timeout=600) as sock:
            for i, c in enumerate(calls):
                r = hc.send(sock, c["name"], c["args"])
                if not r.get("ok"):
                    summary["failed"] = {"index": i, "call": c["name"], "error": r.get("error", r)}
                    break
                if c["name"] == "blueprint_compile":
                    summary["compile"] = r.get("data", r)
        summary["applied"] = "failed" not in summary
    with open(os.path.join(SAVED, name + ".json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    return summary


def main():
    if unreal is None:
        if "--apply" in sys.argv:  # python Tools/Unreal/bp_layout.py --apply /Game/FoA/X/BP_Y [--dry-run]
            s = drive(sys.argv[sys.argv.index("--apply") + 1], "--dry-run" in sys.argv)
            print("bp_layout", {k: (len(v) if k == "calls" else v) for k, v in s.items() if k != "graphs"})
            for g, info in s.get("graphs", {}).items():
                print("  %-24s %s" % (g, info))
            return sys.exit(1 if s.get("error") or s.get("failed") else 0)
        return selftest()
    if "--selftest" in sys.argv:
        return selftest()
    if os.environ.get("FOA_BP_EXPORT"):  # read-only: the engine T3D of the Blueprint, for drive()
        a = unreal.load_asset(os.environ["FOA_BP_EXPORT"])
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(a)
        text = export_t3d(a)
        os.makedirs(SAVED, exist_ok=True)
        with open(os.path.join(SAVED, a.get_name() + ".t3d"), "w", encoding="utf-8") as fh:
            fh.write(text)
        print("bp_layout exported", a.get_name(), len(text))
        return
    dry = "--dry-run" in os.environ.get("FOA_FLAGS", "").split()
    only = [g for g in os.environ.get("FOA_BP_GRAPHS", "").split(",") if g]
    dirty = {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    for p in [p.strip() for p in os.environ.get("FOA_BP_ASSETS", "").split(",") if p.strip()]:
        a = unreal.load_asset(p)
        if a is not None and a.get_outermost().get_name() in dirty:  # another lane's unsaved work
            print("bp_layout", {"asset": p, "skipped": "unsaved changes in the editor"})
            continue
        s = layout_blueprint(a if a is not None else p, dry_run=dry, only=only)
        del a
        print("bp_layout", s.get("asset"), {k: (len(v) if k == "calls" else v) for k, v in s.items()
                                            if k not in ("asset", "graphs")})
        for g, info in s.get("graphs", {}).items():
            print("  %-24s %s" % (g, info))


if __name__ == "__main__":
    main()
