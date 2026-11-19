"""Deterministic auto-layout for material and material-function graphs, in the house style of editor-rules.md rule 8:
comment groups kept together as boxed blocks, stacked in a column on the left, feeding a short combine chain, then the
output on the right. Purely positional: it moves nodes and moves/resizes comment boxes, nothing else.

Python only READS material graphs (editor-rules, "Material graphs: Hayba C++ tools only"), so this tool plans and Hayba
applies. Per asset, inside one editor-lock hold:
  1. $env:FOA_AGENT='<lane>'; python Tools/Unreal/editor_lock.py acquire <lane> --ttl 600
  2. python Tools/Unreal/ue_remote.py Tools/Unreal/graph_layout.py FOA_LAYOUT_ASSETS=/Game/FoA/Materials/M_X [--dry-run]
     closes the asset's editor and writes Saved/GraphLayout/M_X.json; --dry-run also prints every planned move and
     leaves the editor open. Assets with unsaved changes (a lane mid-build) and post-process materials are skipped.
  3. Replay the plan's "calls" in order with Hayba, hayba_invoke(name, args): material_set_node per moved node,
     material_set_comment per moved or resized box, object_set_property for comment bubble flags that are off,
     then material_validate and material_compile (which saves).
  4. python Tools/Unreal/editor_lock.py release <lane>
From a build script running in the editor, as its last step (then do step 3 with the returned calls):
    import sys, importlib; sys.path.append("P:/FoA/Tools/Unreal"); import graph_layout; importlib.reload(graph_layout)
    plan = graph_layout.layout_material("/Game/FoA/Materials/M_X")   # path or asset; plan["calls"], plan["plan_file"]
Self-test of the layout core, outside the editor:
    python Tools/Unreal/graph_layout.py --selftest

Node sizes are estimated (UE exposes no node sizes to Python) from type, title, pins and previews, calibrated on 1:1
captures of M_LightShaft and MF_LS_ObjectRandomTime, rounded up. Desc bubbles above nodes count as part of the node.
Comment "Show Bubble When Zoomed" / "Color Bubble" are turned on through Hayba object_set_property in step 3.
shortcut: nested comment boxes are laid out as separate blocks; add nesting if a graph ever uses it.
"""
import math
import os
import sys

try:
    import unreal
except ImportError:  # the layout core and its self-test run in plain Python
    unreal = None

GRID = 16
COL_GAP = 128        # between node columns inside a block (rule: >= 96)
ROW_GAP = 64         # between nodes in a column (rule: >= 48)
BLOCK_GAP = 96       # between stacked group blocks (rule: >= 64); room for the zoomed-out title bubble
BLOCK_COL_GAP = 192  # between block columns, where the wires into the combine chain run
PAD = 48             # comment box padding around its nodes (rule: >= 48)
ROW = 30             # pin row height at 1:1
SWEEPS = 4           # alternating ordering/placement sweeps per block


def snap(v):
    return int(round(v / GRID)) * GRID


def snap_up(v):
    return int(math.ceil(v / GRID - 1e-9)) * GRID


def snap_down(v):
    return int(math.floor(v / GRID + 1e-9)) * GRID


# ---------------------------------------------------------------- node size estimate (calibrated on 1:1 captures)
# Extra pin rows beyond max(inputs, outputs), and minimum widths, for nodes whose body shows more than its pins.
ROWS = {"TextureSample": 6, "TextureSampleParameter2D": 6, "TextureSampleParameterCube": 6,
        "TextureSampleParameter2DArray": 6, "VectorParameter": 6, "Constant2Vector": 4, "Constant3Vector": 5,
        "Constant4Vector": 6, "VertexColor": 5, "SceneTexture": 3, "BreakMaterialAttributes": 26,
        "WorldPosition": 4, "ScreenPosition": 2, "ComponentMask": 2, "StaticSwitchParameter": 3}  # 4 = XYZ/XY/Z + arrow
MIN_W = {"Constant3Vector": 272, "Constant4Vector": 336, "Panner": 240, "VectorParameter": 208, "Root": 176}
# Classes whose preview is expanded by default (engine constructors); T3D only lists bCollapsed when it differs.
PREVIEW = {"TextureSample", "TextureSampleParameter2D", "TextureObject", "TextureObjectParameter",
           "FunctionInput", "FunctionOutput", "DepthFade", "Custom"}
ARROW = {"TextureCoordinate", "DepthFade", "Panner", "TextureSample", "TextureSampleParameter2D"}


def estimate(cls, title, ins=(), outs=("",), desc="", two_line=False, preview=None):
    """Node box at 1:1: {w, h, top (desc bubble above the node), title_h, bubble_w}.
    ins: [(label, connected)], outs: [label]. Generous by design; checked against measured sizes in selftest()."""
    if cls in ("Reroute", "NamedRerouteUsage") and not ins:
        pass
    if cls == "Reroute":
        return dict(w=32, h=32, top=0, title_h=0, bubble_w=0)
    title_h = 48 if two_line else 32
    rows = max(len(ins), len(outs), 1, ROWS.get(cls, 0))
    in_w = max([7 * len(n) + (0 if c else 56) for n, c in ins] or [0])
    out_w = max([7 * len(n) for n in outs] or [0])
    w = max(96, MIN_W.get(cls, 0), 7.5 * len(title) + 64, in_w + out_w + 96)
    h = title_h + ROW * rows + 8
    if preview if preview is not None else cls in PREVIEW:
        h += 112
    elif cls in ARROW:
        h += 24
    lines = [ln for ln in desc.split("\n") if ln] if desc else []
    top = 28 * len(lines) + 8 if lines else 0
    bubble_w = max([6.8 * len(ln) + 40 for ln in lines] or [0])
    return dict(w=snap_up(w), h=snap_up(h), top=snap_up(top), title_h=title_h, bubble_w=snap_up(bubble_w))


def title_only(text):
    """A comment box's text cut to its title (the user's rule: 2-5 words, nothing else): the first line, and if that
    runs past five words, the part before its first separator, then at most five words."""
    import re
    line = next((ln.strip() for ln in (text or "").splitlines() if ln.strip()), "")
    if len(re.findall(r"[^\W_]+", line)) > 5:
        line = re.split(r"\s*(?::|\s[-–—]\s|\(|\.\s)", line, maxsplit=1)[0]
    out = []
    for tok in line.split():  # at most five real words; separators like "-" don't count
        if len(re.findall(r"[^\W_]+", " ".join(out + [tok]))) > 5:
            break
        out.append(tok)
    return " ".join(out).rstrip(".,;:-")


def title_height(text, font, width):
    """Comment title bar height: its text wraps at the box width."""
    char_w, line_h = font * 0.55, font * 1.5
    per_line = max(1, int((width - 24) / char_w))
    lines = sum(max(1, math.ceil(len(ln) / per_line)) for ln in (text or " ").split("\n"))
    return snap_up(lines * line_h + 16)


# ---------------------------------------------------------------- layout core (pure Python)
def _depth(ids, succ):
    """Longest path from each id to a node without successors (0 there). Back edges of a cycle are ignored."""
    depth, stack = {}, set()

    def visit(n):
        if n in depth:
            return depth[n]
        stack.add(n)
        best = 0
        for m in succ[n]:
            if m not in stack:
                best = max(best, 1 + visit(m))
        stack.discard(n)
        depth[n] = best
        return best

    for n in sorted(ids):
        visit(n)
    return depth


def _pin_y(nd, i):
    return nd["title_h"] + ROW * (i + 0.5)


def _segments(edges, nodes, x, y):
    return [(s, d, x[s] + nodes[s]["w"], y[s] + _pin_y(nodes[s], o), x[d], y[d] + _pin_y(nodes[d], i))
            for s, d, i, o in edges if s in x and d in x]


def crossings(edges, nodes, x, y):
    """Wire crossings, wires drawn as straight segments from output pin to input pin."""
    segs = _segments(edges, nodes, x, y)

    def orient(ax, ay, bx, by, cx, cy):
        v = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        return (v > 0) - (v < 0)

    count = 0
    for i, (s1, d1, ax, ay, bx, by) in enumerate(segs):
        for s2, d2, cx, cy, dx, dy in segs[i + 1:]:
            if {s1, d1} & {s2, d2}:
                continue
            if (orient(ax, ay, bx, by, cx, cy) * orient(ax, ay, bx, by, dx, dy) < 0
                    and orient(cx, cy, dx, dy, ax, ay) * orient(cx, cy, dx, dy, bx, by) < 0):
                count += 1
    return count


def _stack(column, want, y, nodes, gap):
    """Keeps the column's order, pushes nodes down until they clear each other, then recentres the column on `want`."""
    bottom = None
    for n in column:
        t = want[n]
        if bottom is not None:
            t = max(t, bottom + gap + nodes[n]["top"])
        y[n] = t
        bottom = t + nodes[n]["h"]
    shift = snap(sum(want[n] - y[n] for n in column) / len(column))
    for n in column:
        y[n] += shift


def _sweeps(cols, y, nodes, prods, cons, passes, score):
    """Barycentric sweeps: each column is re-ordered by, and moved towards, the pin heights of its already placed
    neighbours (consumers when going right to left, producers left to right). Keeps the pass with fewest crossings."""
    best = None
    for direction in passes:
        seq = cols if direction == "R2L" else cols[::-1]
        links = cons if direction == "R2L" else prods
        for column in seq:
            want = {}
            for n in column:
                t = [y[m] + _pin_y(nodes[m], mi) - _pin_y(nodes[n], ni) for m, mi, ni in links[n] if m in y]
                want[n] = snap(sum(t) / len(t)) if t else y[n]
            column.sort(key=lambda n: (want[n], y[n]))
            _stack(column, want, y, nodes, ROW_GAP)
        c = score()
        if best is None or c <= best[0]:
            best = (c, dict(y), [list(col) for col in cols])
    y.update(best[1])
    for col, order in zip(cols, best[2]):
        col[:] = order


def _links(members, edges):
    """prods[n] = [(producer, its out pin, n's in pin)], cons[n] = [(consumer, its in pin, n's out pin)]."""
    prods = {m: [] for m in members}
    cons = {m: [] for m in members}
    for s, d, i, o in edges:
        if d in prods:
            prods[d].append((s, o, i))
        if s in cons:
            cons[s].append((d, i, o))
    return prods, cons


def _layout_block(members, nodes, edges, params_left):
    """Lays out one block in local coordinates. Returns (x, y, cols) with cols[0] the rightmost column."""
    inner = [e for e in edges if e[0] in members and e[1] in members and e[0] != e[1]]
    succ = {m: sorted({d for s, d, _, _ in inner if s == m}) for m in members}
    col = _depth(members, succ)
    last = max(col.values())
    if params_left and last > 0:
        fed = {d for _, d, _, _ in inner}
        for m in members:
            if nodes[m]["kind"] == "param" and m not in fed:  # a FunctionInput's Preview pin can be wired
                col[m] = last
    cols = [sorted((m for m in members if col[m] == c), key=lambda m: (nodes[m]["y0"], nodes[m]["x0"], m))
            for c in range(last + 1)]
    cols = [c for c in cols if c]
    x, left = {}, None
    for c in cols:
        # Desc bubbles run right from their node, so a column's overhang widens the gap on its right.
        overhang = max(nodes[m]["bubble_w"] - nodes[m]["w"] for m in c)
        right = 0 if left is None else left - max(COL_GAP, snap_up(overhang) + 2 * GRID)
        for m in c:
            x[m] = right - nodes[m]["w"]
        left = min(x[m] for m in c)
    y = {}
    for c in cols:
        _stack(c, {m: 0 for m in c}, y, nodes, ROW_GAP)
    prods, cons = _links(members, inner)
    _sweeps(cols, y, nodes, prods, cons, ["R2L", "L2R"] * (SWEEPS // 2), lambda: crossings(inner, nodes, x, y))
    return x, y, cols


def _bounds(ids, nodes, x, y):
    return (min(x[n] for n in ids), min(y[n] - nodes[n]["top"] for n in ids),
            max(x[n] + nodes[n]["w"] for n in ids), max(y[n] + nodes[n]["h"] for n in ids))


def _box(block, nodes, comments, x, y):
    """Block rectangle (x0, y0, x1, y1): the comment box for a group, the bare node bounds otherwise."""
    x0, y0, x1, y1 = _bounds(block["members"], nodes, x, y)
    if block["cid"] is None:
        return x0, y0, x1, y1
    c = comments[block["cid"]]
    bx0, bx1 = snap_down(x0 - PAD), snap_up(x1 + PAD)
    return bx0, snap_down(y0 - PAD - title_height(c["text"], c["font"], bx1 - bx0)), bx1, snap_up(y1 + PAD)


def plan(nodes, edges, comments, anchor=None):
    """nodes: {id: {w, h, top, title_h, bubble_w, kind ('param'|'sink'|'node'), x0, y0}} (sizes from estimate()).
    edges: [(src, dst, dst_input_index, src_output_index)]; data flows src -> dst, drawn left to right.
    comments: {cid: {x0, y0, w0, h0, text, font}}; a node belongs to the smallest box holding its top-left corner.
    anchor: node id that keeps its original position (the material output); default: the first sink.
    Returns (pos {id: (x, y)}, boxes {cid: (x, y, w, h)}), all on the 16 px grid."""
    ids = sorted(nodes)
    for nd in nodes.values():
        for k in ("w", "h", "top", "bubble_w"):
            nd[k] = snap_up(nd[k])
    group = {}
    for n in ids:
        holders = [(c["w0"] * c["h0"], cid) for cid, c in comments.items()
                   if c["x0"] <= nodes[n]["x0"] < c["x0"] + c["w0"] and c["y0"] <= nodes[n]["y0"] < c["y0"] + c["h0"]]
        group[n] = min(holders)[1] if holders else None

    # Blocks: one per comment group, one per connected component of the ungrouped nodes (the combine chain).
    parent = {n: n for n in ids if group[n] is None}

    def find(n):
        while parent[n] != n:
            n = parent[n]
        return n

    for s, d, _, _ in edges:
        if s in parent and d in parent:
            a, b = sorted((find(s), find(d)))
            parent[b] = a
    blocks = {}
    for n in ids:
        key = ("g", group[n]) if group[n] is not None else ("f", find(n))
        blocks.setdefault(key, {"members": [], "cid": group[n]})["members"].append(n)
    block_of = {n: k for k, b in blocks.items() for n in b["members"]}
    bsucc = {k: sorted({block_of[d] for s, d, _, _ in edges if block_of[s] == k and block_of[d] != k}) for k in blocks}
    bcol = _depth(list(blocks), bsucc)

    for k, b in blocks.items():
        b["sink"] = any(nodes[m]["kind"] == "sink" for m in b["members"])
        b["x"], b["y"], b["cols"] = _layout_block(b["members"], nodes, edges, b["cid"] is not None and not b["sink"])
        b["rect"] = _box(b, nodes, comments, b["x"], b["y"])
        bubble_right = max(b["x"][m] + nodes[m]["bubble_w"] for m in b["members"])
        b["overhang"] = max(0, bubble_right - b["rect"][2])

    # Block columns right to left; blocks right-aligned in their column.
    gx, gy = {}, {}
    ncols = max(bcol.values()) + 1
    left = None
    for c in range(ncols):
        col = [k for k in sorted(blocks) if bcol[k] == c]
        overhang = max(blocks[k]["overhang"] for k in col)
        right = 0 if left is None else left - max(BLOCK_COL_GAP, snap_up(overhang) + 2 * GRID)
        for k in col:
            blocks[k]["dx"] = right - blocks[k]["rect"][2]
        left = min(blocks[k]["dx"] + blocks[k]["rect"][0] for k in col)

        # Vertical: column 0 keeps the authored order; others go where their consumers' pins are.
        want, key = {}, {}
        for k in col:
            b = blocks[k]
            t, cx = [], []
            for s, d, i, o in edges:
                if block_of.get(s) == k and d in gy:
                    t.append(gy[d] + _pin_y(nodes[d], i) - b["y"][s] - _pin_y(nodes[s], o))
                    cx.append(gx[d])
            mean_y0 = sum(nodes[m]["y0"] for m in b["members"]) / len(b["members"])
            want[k] = snap(sum(t) / len(t)) if t else 0
            key[k] = (want[k], sum(cx) / len(cx) if cx else 0, mean_y0, k)
        col.sort(key=lambda k: key[k])
        bottom = None
        for k in col:
            b = blocks[k]
            dy = want[k] if bottom is None else max(want[k], bottom + BLOCK_GAP - b["rect"][1])
            b["dy"] = dy
            bottom = dy + b["rect"][3]
        shift = snap(sum(want[k] - blocks[k]["dy"] for k in col) / len(col)) if c else 0
        for k in col:
            b = blocks[k]
            b["dy"] += shift
            for m in b["members"]:
                gx[m], gy[m] = b["x"][m] + b["dx"], b["y"][m] + b["dy"]

    # Output-side blocks: pull the combine chain next to the groups that feed it (left to right sweeps).
    col0 = sorted((k for k in blocks if bcol[k] == 0), key=lambda k: blocks[k]["dy"] + blocks[k]["rect"][1])
    for k in col0:
        b = blocks[k]
        mem = set(b["members"])
        touching = [e for e in edges if (e[0] in mem or e[1] in mem) and e[0] != e[1]]
        if any(e[0] not in mem for e in touching):
            prods, cons = _links(b["members"], touching)
            _sweeps(b["cols"], gy, nodes, prods, cons, ["L2R", "R2L", "L2R"], lambda: crossings(touching, nodes, gx, gy))
    bottom = None
    for k in col0:  # re-stack in case the sweeps made output-side blocks overlap
        b = blocks[k]
        r = _box(b, nodes, comments, gx, gy)
        if bottom is not None and r[1] < bottom + BLOCK_GAP:
            for m in b["members"]:
                gy[m] += snap_up(bottom + BLOCK_GAP - r[1])
            r = _box(b, nodes, comments, gx, gy)
        bottom = r[3]

    boxes = {}
    for b in blocks.values():
        if b["cid"] is not None:
            r = _box(b, nodes, comments, gx, gy)
            boxes[b["cid"]] = [r[0], r[1], r[2] - r[0], r[3] - r[1]]
    # Empty comment boxes keep their size and line up under the graph.
    x0, _, _, y1 = _bounds(ids, nodes, gx, gy) if ids else (0, 0, 0, 0)
    y1 = max([y1] + [r[1] + r[3] for r in boxes.values()])
    cursor = x0
    for cid in sorted(set(comments) - set(boxes)):
        c = comments[cid]
        boxes[cid] = [cursor, snap_up(y1 + BLOCK_GAP), snap_up(c["w0"]), snap_up(c["h0"])]
        cursor += snap_up(c["w0"]) + BLOCK_GAP

    if anchor is None:
        sinks = sorted((nodes[n]["y0"], n) for n in ids if nodes[n]["kind"] == "sink")
        anchor = sinks[0][1] if sinks else None
    tx = snap(nodes[anchor]["x0"] - gx[anchor]) if anchor in gx else 0
    ty = snap(nodes[anchor]["y0"] - gy[anchor]) if anchor in gy else 0
    pos = {n: (gx[n] + tx, gy[n] + ty) for n in ids}
    for r in boxes.values():
        r[0] += tx
        r[1] += ty
    return pos, {cid: tuple(r) for cid, r in boxes.items()}


def problems(nodes, edges, comments, pos, boxes):
    """Every rule the layout breaks; empty when it is clean. Entries starting "warn:" are cosmetic, the rest block
    layout_material() from applying the plan."""
    out = []
    rect = {n: (x, y - nodes[n]["top"], x + nodes[n]["w"], y + nodes[n]["h"]) for n, (x, y) in pos.items()}

    def hit(a, b, gap_x=0, gap_y=0):
        return a[0] < b[2] + gap_x and b[0] < a[2] + gap_x and a[1] < b[3] + gap_y and b[1] < a[3] + gap_y

    ids = sorted(pos)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if hit(rect[a], rect[b], 0, 48):
                out.append(f"nodes {a} and {b} closer than 48 px vertically / overlap")
        bub = (rect[a][0], rect[a][1], rect[a][0] + nodes[a]["bubble_w"], pos[a][1])
        for b in ids:
            if b != a and nodes[a]["bubble_w"] and hit(bub, rect[b]):
                out.append(f"desc bubble of {a} covers {b}")
    for n, (x, y) in pos.items():
        if x % GRID or y % GRID:
            out.append(f"{n} off grid ({x},{y})")
    for s, d, _, _ in edges:
        if s != d and s in pos and d in pos and not rect[s][2] < rect[d][0]:
            out.append(f"warn: wire {s}->{d} runs right to left (a cycle between blocks)")
    member = {}
    for n in ids:
        holders = [(c["w0"] * c["h0"], cid) for cid, c in comments.items()
                   if c["x0"] <= nodes[n]["x0"] < c["x0"] + c["w0"] and c["y0"] <= nodes[n]["y0"] < c["y0"] + c["h0"]]
        member[n] = min(holders)[1] if holders else None
    brect = {cid: (r[0], r[1], r[0] + r[2], r[1] + r[3]) for cid, r in boxes.items()}
    cids = sorted(brect)
    for i, a in enumerate(cids):
        if any(v % GRID for v in boxes[a]):
            out.append(f"box {a} off grid {boxes[a]}")
        for b in cids[i + 1:]:
            if hit(brect[a], brect[b], 0, 64):
                out.append(f"boxes {a} and {b} overlap or sit closer than 64 px")
    for n in ids:
        for cid, r in brect.items():
            if member[n] == cid:
                if not (r[0] + PAD <= rect[n][0] and rect[n][2] <= r[2] - PAD and r[1] + PAD <= rect[n][1]
                        and rect[n][3] <= r[3] - PAD):
                    out.append(f"box {cid} does not hold {n} with {PAD} px padding")
            elif hit(r, rect[n]):
                out.append(f"box {cid} covers non-member {n}")
    return out


# ---------------------------------------------------------------- self-test (no editor)
def selftest():
    def node(kind="node", y0=0, x0=0, w=128, h=96, top=0, bubble_w=0, title_h=32):
        return dict(kind=kind, x0=x0, y0=y0, w=w, h=h, top=top, bubble_w=bubble_w, title_h=title_h)

    # Measured node sizes at 1:1 (M_LightShaft, MF_LS_ObjectRandomTime): the estimate must cover them, not balloon.
    for (w, h), est in (
            ((108, 85), estimate("Multiply", "Multiply", [("A", True), ("B", True)])),
            ((92, 57), estimate("Floor", "Floor", [("", True)])),
            ((206, 238), estimate("TextureSample", "Texture Sample", [("UVs", True), ("Tex", False),
                                  ("Apply View MipBias", False)], ["RGB", "R", "G", "B", "A", "RGBA"], preview=False)),
            ((269, 262), estimate("MaterialFunctionCall", "Fresnel_Function", [(n, False) for n in (
                "Normal Vector (V3)", "Camera Vector (V3)", "Invert Fresnel (SB)", "Power (S)", "Use Cheap contrast (SB)",
                "Cheap contrast dark (S)", "Cheap contrast bright (S)", "Clamp Fresnel Dot Product (SB)")], ["Result"])),
            ((172, 72), estimate("ScalarParameter", "Intensity", [], ["Default Value"], two_line=True)),
            ((193, 217), estimate("VectorParameter", "Color", [], ["RGBA"], two_line=True)),
            ((175, 163), estimate("FunctionInput", "Input Time (Scalar)", [("Preview", False)])),
            ((254, 185), estimate("Constant3Vector", "0.731,0.519,0.937", [], ["", "R", "G", "B"])),
            ((217, 125), estimate("Panner", "Panner", [("Coordinate", True), ("Time", True), ("Speed", False)])),
            ((155, 630), estimate("Root", "M_LightShaft", [(f"pin{i:02}xxxxxxxxxx", True) for i in range(20)], [])),
    ):
        assert w <= est["w"] <= 1.8 * w + 32 and h <= est["h"] <= 1.6 * h + 64, ((w, h), est)
    long_desc = estimate("Multiply", "Multiply", [("A", True)], desc="x" * 120)
    assert long_desc["top"] >= 32 and long_desc["bubble_w"] >= 800, long_desc

    def check(nodes, edges, comments, anchor=None):
        pos, boxes = plan({k: dict(v) for k, v in nodes.items()}, edges, comments, anchor)
        again = plan({k: dict(v) for k, v in nodes.items()}, edges, comments, anchor)
        assert (pos, boxes) == again, "layout is not deterministic"
        sized = {k: dict(v) for k, v in nodes.items()}
        for nd in sized.values():
            for k in ("w", "h", "top", "bubble_w"):
                nd[k] = snap_up(nd[k])
        bad = problems(sized, edges, comments, pos, boxes)
        assert not bad, "\n".join(bad)
        assert set(pos) == set(nodes) and set(boxes) == set(comments)
        return pos, boxes

    # 1. The reference shape: five groups feed a multiply chain into the output; one group feeds another group.
    C = lambda x, y, w, h, t="Group": dict(x0=x, y0=y, w0=w, h0=h, text=t, font=18)  # noqa: E731
    nodes = {"ROOT": node("sink", 0, 2000, 176, 640)}
    comments = {"cTex": C(0, 0, 900, 400, "Texture"), "cGrad": C(0, 500, 900, 300, "Gradient Falloff"),
                "cDF": C(0, 900, 900, 200, "Depth Fade"), "cCDF": C(0, 1200, 900, 200, "CameraDepthFade"),
                "cFr": C(0, 1500, 900, 300, "Fresnel"), "cRnd": C(-1000, 0, 500, 300, "Object Position Random"),
                "cEmpty": C(5000, 5000, 300, 200, "Unused box")}
    edges = []
    groups = [("Tex", 0, 4), ("Grad", 500, 3), ("DF", 900, 2), ("CDF", 1200, 2), ("Fr", 1500, 4), ("Rnd", 0, 3)]
    for g, y0, n in groups:
        base = -1000 if g == "Rnd" else 0
        for i in range(n):
            kind = "param" if i == 0 or (g == "Fr" and i == 1) else "node"
            nodes[f"{g}{i}"] = node(kind, y0 + 20 + 30 * i, base + 10 + 100 * i, 160 + 20 * i, 96 + 40 * (i % 2),
                                    top=40 if (g, i) == ("Fr", n - 1) else 0,
                                    bubble_w=1200 if (g, i) == ("Fr", n - 1) else 0)
        for i in range(n - 1):
            edges.append((f"{g}{i}", f"{g}{n - 1}" if i else f"{g}{i + 1}", i % 2, 0))
    edges.append(("Rnd2", "Tex1", 1, 0))
    chain = ["Tex3", "Grad2", "DF1", "CDF1", "Fr3"]
    prev = chain[0]
    for i, src in enumerate(chain[1:]):
        nodes[f"Mul{i}"] = node("node", 100 * i, 1200 + 100 * i)
        edges += [(prev, f"Mul{i}", 0, 0), (src, f"Mul{i}", 1, 0)]
        prev = f"Mul{i}"
    nodes["Intensity"] = node("param", 50, 1800, 160, 80, title_h=48)
    nodes["MulI"] = node("node", 60, 1900)
    edges += [(prev, "MulI", 0, 0), ("Intensity", "MulI", 1, 0), ("MulI", "ROOT", 5, 0)]
    nodes["Dead"] = node("node", 3000, 3000)  # unconnected, ungrouped
    pos, boxes = check(nodes, edges, comments, "ROOT")
    assert pos["ROOT"] == (2000, 0), pos["ROOT"]
    stack = ["cTex", "cGrad", "cDF", "cCDF", "cFr"]
    lefts = {boxes[c][0] + boxes[c][2] for c in stack}
    assert len(lefts) == 1, f"source groups are not one right-aligned stack: {lefts}"
    tops = [boxes[c][1] for c in stack]
    assert tops == sorted(tops), f"stack order follows the chain: {tops}"
    assert boxes["cRnd"][0] + boxes["cRnd"][2] < boxes["cTex"][0], "a group feeding a group sits to its left"
    assert all(pos[m][0] > boxes["cTex"][0] + boxes["cTex"][2] for m in ("Mul0", "MulI")), "chain right of the stack"
    for g in ("Tex", "Grad", "Fr"):  # parameters at the left edge of their group
        assert pos[f"{g}0"][0] == min(pos[m][0] for m in nodes if m.startswith(g) and m[len(g):].isdigit())

    # 2. A function: two output groups share a hash group; outputs inside groups; one wire skips a column.
    nodes = {"In": node("param", 0, 0), "Hash": node("node", 300, 0), "Frac": node("node", 300, 200),
             "Add": node("node", 0, 400), "OutT": node("sink", 0, 600, 160, 240),
             "Floor": node("node", 400, 400), "Sat": node("node", 400, 500), "OutM": node("sink", 400, 700, 192, 176)}
    comments = {"cA": C(-20, -50, 900, 280, "Random Start Time"), "cB": C(-20, 260, 400, 300, "Hash"),
                "cC": C(380, 260, 600, 300, "Channel Select")}
    edges = [("In", "Add", 0, 0), ("Hash", "Frac", 0, 0), ("Frac", "Add", 1, 0), ("Add", "OutT", 0, 0),
             ("Frac", "Floor", 0, 0), ("Floor", "Sat", 0, 0), ("Sat", "OutM", 0, 0), ("Hash", "Sat", 1, 0)]
    pos, boxes = check(nodes, edges, comments)
    assert boxes["cB"][0] + boxes["cB"][2] < min(boxes["cA"][0], boxes["cC"][0]), "shared group feeds from the left"

    # 3. No comments at all, a fan-in tree with a cycle guard and a long desc bubble mid-graph.
    nodes = {k: node("param" if k.startswith("p") else "node", i * 40, 0) for i, k in enumerate(
        ["p1", "p2", "p3", "a", "b", "c", "out"])}
    nodes["out"]["kind"] = "sink"
    nodes["a"].update(top=40, bubble_w=900)
    edges = [("p1", "a", 0, 0), ("p2", "a", 1, 0), ("p3", "b", 0, 0), ("a", "c", 0, 0), ("b", "c", 1, 0),
             ("c", "out", 0, 0), ("p1", "c", 2, 0)]
    check(nodes, edges, {})
    _depth(["x", "y"], {"x": ["y"], "y": ["x"]})  # a cycle must not recurse forever

    assert title_height("Texture", 18, 400) == 48 and title_height("T\n" + "d" * 200, 18, 400) > 96

    # 4. The Hayba calls that apply a plan: only what moved, the output node never, then validate + compile.
    nodes = {"ROOT": dict(x0=0, y0=0), "a": dict(x0=0, y0=0), "b": dict(x0=16, y0=32)}
    comments = {"c1": dict(x0=0, y0=0, w0=64, h0=64), "c2": dict(x0=0, y0=0, w0=64, h0=64)}
    calls = hayba_calls("/Game/F/MF_X", True, nodes, comments, {"ROOT": (32, 32), "a": (48, 0), "b": (16, 32)},
                        {"c1": (0, 0, 64, 64), "c2": (0, 0, 96, 64)})
    assert [c["name"] for c in calls] == ["material_set_node", "material_set_comment", "material_validate",
                                          "material_compile"], calls
    assert calls[0]["args"] == {"function_path": "/Game/F/MF_X", "node_id": "a", "node_pos": [48, 0]}, calls[0]
    assert calls[1]["args"]["comment_id"] == "c2" and calls[1]["args"]["size"] == [96, 64], calls[1]
    assert hayba_calls("/Game/M", False, nodes, {}, {"a": (0, 0)}, {}) == [], "nothing moved, nothing to do"
    for text, want in (("Combine", "Combine"), ("Texture\nT_Lines x2, opposite pans", "Texture"),
                       ("Object Position Random - Start Time", "Object Position Random - Start Time"),
                       ("MF_LS_ObjectRandomTime: hash(ObjectPositionWS) -> per-card random start", "MF_LS_ObjectRandomTime"),
                       ("Resolve the cost of the selected verb against inventory", "Resolve the cost of the")):
        assert title_only(text) == want, (text, title_only(text))
    with_desc = dict(nodes, a=dict(nodes["a"], desc_path="/Game/M.M:MaterialExpressionAdd_0"))
    comments = {"c1": dict(x0=0, y0=0, w0=64, h0=64, text="Texture", text0="Texture\nlong why")}
    calls = hayba_calls("/Game/M", False, with_desc, comments, {"a": (0, 0)}, {"c1": (0, 0, 64, 64)})
    assert calls[0]["args"]["text"] == "Texture" and calls[1]["args"]["properties"]["Desc"] == "", calls
    bub = hayba_calls("/Game/M", False, nodes, {}, {"a": (0, 0)}, {}, ["/Game/M.M:MaterialExpressionComment_0"])
    assert [c["name"] for c in bub] == ["object_set_property", "material_validate", "material_compile"], bub
    assert bub[0]["args"]["properties"] == {"bCommentBubbleVisible_InDetailsPanel": True, "bColorCommentBubble": True}
    print("graph_layout selftest ok")


# ---------------------------------------------------------------- editor side (read-only; Hayba applies the plan)
ROOT_ROWS = ["MP_BASE_COLOR", "MP_METALLIC", "MP_SPECULAR", "MP_ROUGHNESS", "MP_ANISOTROPY", "MP_EMISSIVE_COLOR",
             "MP_OPACITY", "MP_OPACITY_MASK", "MP_NORMAL", "MP_TANGENT", "MP_WORLD_POSITION_OFFSET",
             "MP_SUBSURFACE_COLOR", "MP_CUSTOM_DATA0", "MP_CUSTOM_DATA1", "MP_AMBIENT_OCCLUSION", "MP_REFRACTION",
             "MP_PIXEL_DEPTH_OFFSET", "MP_SHADING_MODEL", "MP_SURFACE_THICKNESS", "MP_DISPLACEMENT"]


def _prop(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def _expr_box(e, connected, hidden):
    """estimate() inputs for one expression."""
    MEL = unreal.MaterialEditingLibrary
    cls = e.get_class().get_name().replace("MaterialExpression", "", 1)
    names = list(MEL.get_material_expression_input_names(e))
    ins = [(str(n), bool(c)) for n, c in zip(names, connected + [False] * len(names))]
    outs, two_line, title = [""], False, cls
    pname = _prop(e, "parameter_name")
    if "Parameter" in cls and pname is not None:
        title, two_line = max(str(pname), "x" * 18, key=len), True
    elif cls == "FunctionInput":
        title = "Input %s (Vector3)" % _prop(e, "input_name", "")
    elif cls == "FunctionOutput":
        title, two_line = "Output %s" % _prop(e, "output_name", ""), True
    elif cls == "MaterialFunctionCall":
        f = _prop(e, "material_function")
        if f:
            title = f.get_name()
            outs = [str(_prop(o, "output_name", "")) for o in MEL.get_material_function_expressions(f)
                    if isinstance(o, unreal.MaterialExpressionFunctionOutput)] or [""]
    elif cls in ("NamedRerouteDeclaration", "NamedRerouteUsage"):
        title = str(_prop(e, "name", "") or cls)
    elif cls == "Custom":
        title = str(_prop(e, "description", "Custom"))
    elif cls.startswith("Constant") and cls != "Constant":
        title = "x" * 20
    collapsed = hidden.get("bCollapsed")
    preview = None if collapsed is None else collapsed == "False"
    return estimate(cls, title, ins, outs, "", two_line, preview)  # per-node desc bubbles are stripped


def _comments(asset):
    pkg = asset.get_outermost().get_name()
    return [c for c in unreal.ObjectIterator(unreal.MaterialExpressionComment)
            if c.get_outermost().get_name() == pkg and unreal.SystemLibrary.is_valid(c)]


def _hidden(asset):
    """{object name: {property: text}} from a T3D export of the asset: SizeX/SizeY of comments, EditorX/EditorY of
    the material output and bCollapsed are plain UPROPERTY()s that Python cannot read."""
    import re
    import tempfile
    path = os.path.join(tempfile.gettempdir(), "foa_graph_layout.t3d")
    task = unreal.AssetExportTask()
    task.object = asset
    task.exporter = unreal.ObjectExporterT3D()
    task.filename = path
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    if not unreal.Exporter.run_asset_export_task(task):
        return {}
    props, stack = {}, []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            m = re.match(r'Begin Object\b.*?\bName="?([^"\s]+)"?', line)
            if m:
                stack.append(m.group(1))
                props.setdefault(stack[-1], {})
            elif line.startswith("End Object"):
                stack and stack.pop()
            elif stack and "=" in line:
                k, v = line.split("=", 1)
                props[stack[-1]].setdefault(k, v)
    os.remove(path)
    return props


def _int(text, default=0):
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return default


def read_graph(asset):
    """(nodes, edges, comments, bubbles_off) for plan(), read without touching the graph. The output node is 'ROOT'."""
    MEL = unreal.MaterialEditingLibrary
    fn_graph = isinstance(asset, unreal.MaterialFunction)
    try:
        hidden = _hidden(asset)
    except Exception as err:  # comment sizes then fall back to defaults; the plan is still checked
        unreal.log_warning("graph_layout: T3D export failed: %s" % err)
        hidden = {}
    exprs = {}
    for e in (MEL.get_material_function_expressions(asset) if fn_graph else MEL.get_material_expressions(asset)):
        if not isinstance(e, unreal.MaterialExpressionComment):
            exprs[e.get_name()] = e
    nodes, edges = {}, []
    for name, e in exprs.items():
        ins = list(MEL.get_inputs_for_material_expression(None if fn_graph else asset, e))
        for i, src in enumerate(ins):
            if src is not None and src.get_name() in exprs:
                o = 0
                try:
                    out_name = MEL.get_input_node_output_name_for_material_expression(e, src)
                    o = {"R": 1, "G": 2, "B": 3, "A": 4, "RGBA": 5}.get(str(out_name), 0)
                except Exception:
                    pass
                edges.append((src.get_name(), name, i, o))
        nd = _expr_box(e, [s is not None for s in ins], hidden.get(name, {}))
        cls = e.get_class().get_name()
        kind = "sink" if cls == "MaterialExpressionFunctionOutput" else (
            "param" if "Parameter" in cls or cls == "MaterialExpressionFunctionInput" else "node")
        nd.update(kind=kind, x0=e.get_editor_property("material_expression_editor_x"),
                  y0=e.get_editor_property("material_expression_editor_y"))
        if _prop(e, "desc"):  # the user's rule: no per-node comment bubbles
            nd["desc_path"] = e.get_path_name()
        nodes[name] = nd
    if not fn_graph:
        rows = []
        for row, mp in enumerate(ROOT_ROWS):
            prop = getattr(unreal.MaterialProperty, mp, None)
            src = MEL.get_material_property_input_node(asset, prop) if prop is not None else None
            if src is not None and src.get_name() in exprs:
                edges.append((src.get_name(), "ROOT", row, 0))
            rows.append((mp[3:].title().replace("_", " "), True))
        if asset.get_name() not in hidden:  # the output node is the anchor: never plan around a guessed position
            raise RuntimeError("graph_layout: could not read the output node position of %s (T3D export)" % asset)
        h = hidden[asset.get_name()]
        root = estimate("Root", asset.get_name(), rows, [])
        root.update(kind="sink", x0=_int(h.get("EditorX")), y0=_int(h.get("EditorY")))
        nodes["ROOT"] = root
    comments, bubbles_off = {}, []
    for c in _comments(asset):
        h = hidden.get(c.get_name(), {})
        if not (_int(h.get("SizeX")) and _int(h.get("SizeY"))):  # a guessed size would regroup nodes wrongly
            raise RuntimeError("graph_layout: could not read the size of %s in %s (T3D export)" % (c.get_name(), asset))
        comments[c.get_name()] = dict(x0=c.get_editor_property("material_expression_editor_x"),
                                      y0=c.get_editor_property("material_expression_editor_y"),
                                      w0=_int(h.get("SizeX")), h0=_int(h.get("SizeY")),
                                      text=title_only(str(c.get_editor_property("text"))),
                                      text0=str(c.get_editor_property("text")), font=c.get_editor_property("font_size") or 18)
        if not (c.get_editor_property("comment_bubble_visible_in_details_panel")
                and c.get_editor_property("color_comment_bubble")):
            bubbles_off.append(c.get_path_name())
    return nodes, edges, comments, sorted(bubbles_off)


def hayba_calls(path, function, nodes, comments, pos, boxes, bubbles=()):
    """The Hayba calls that apply a plan: one per moved node, one per comment box that moves, resizes or loses its
    description (text cut to the title), object_set_property to clear per-node desc bubbles and to turn on comment
    bubble flags that are off, then validate and compile (which saves)."""
    key = "function_path" if function else "material_path"
    calls = [{"name": "material_set_node", "args": {key: path, "node_id": n, "node_pos": [x, y]}}
             for n, (x, y) in sorted(pos.items()) if n != "ROOT" and (x, y) != (nodes[n]["x0"], nodes[n]["y0"])]
    for c, (x, y, w, h) in sorted(boxes.items()):
        args = {key: path, "comment_id": c, "node_pos": [x, y], "size": [w, h]}
        if comments[c].get("text0", comments[c].get("text")) != comments[c].get("text"):
            args["text"] = comments[c]["text"]
        if len(args) > 4 or (x, y, w, h) != tuple(comments[c][k] for k in ("x0", "y0", "w0", "h0")):
            calls.append({"name": "material_set_comment", "args": args})
    calls += [{"name": "object_set_property", "args": {"path": nodes[n]["desc_path"], "properties": {
        "Desc": "", "bCommentBubbleVisible": False}}} for n in sorted(nodes) if nodes[n].get("desc_path")]
    calls += [{"name": "object_set_property", "args": {"path": c, "properties": {
        "bCommentBubbleVisible_InDetailsPanel": True, "bColorCommentBubble": True}}} for c in bubbles]
    if calls:
        calls += [{"name": "material_validate", "args": {key: path}}, {"name": "material_compile", "args": {key: path}}]
    return calls


def layout_material(asset, dry_run=False):
    """Plans the layout of one material or material function and returns it as Hayba calls; Python only reads the
    graph (editor-rules, Hayba first). Apply summary["calls"] in order with hayba_invoke(name, args) while holding the editor lock; the last call,
    material_compile, saves. The plan is also written to Saved/GraphLayout/<asset name>.json. Unless dry_run, the
    asset's editor is closed first, as before any graph edit. The material output node is the anchor and stays."""
    import json
    if isinstance(asset, str):
        asset = unreal.load_asset(asset)
    if asset is None:
        return {"error": "asset not found"}
    path = asset.get_path_name().split(".")[0]
    if not dry_run:
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(asset)
    nodes, edges, comments, bubbles_off = read_graph(asset)
    sized = {k: dict(v) for k, v in nodes.items()}
    pos, boxes = plan(sized, edges, comments, "ROOT" if "ROOT" in nodes else None)
    issues = problems(sized, edges, comments, pos, boxes)
    blocked = [p for p in issues if not p.startswith("warn:")]
    summary = {"asset": path, "nodes": len(nodes), "comments": len(comments), "problems": issues,
               "calls": [] if blocked else hayba_calls(path, isinstance(asset, unreal.MaterialFunction),
                                                        nodes, comments, pos, boxes, bubbles_off),
               "bubble_flags_off": bubbles_off,
               "moves": {n: (nodes[n]["x0"], nodes[n]["y0"], *pos[n]) for n in sorted(pos)},
               "boxes": {c: (tuple(comments[c][k] for k in ("x0", "y0", "w0", "h0")), boxes[c]) for c in sorted(boxes)},
               "graph": {"nodes": nodes, "edges": edges, "comments": comments}}  # for offline re-planning
    out_dir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "GraphLayout/"
    os.makedirs(out_dir, exist_ok=True)
    summary["plan_file"] = out_dir + asset.get_name() + ".json"
    with open(summary["plan_file"], "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    return summary


def main():
    if unreal is None or "--selftest" in sys.argv:
        return selftest()
    paths = [p.strip() for p in os.environ.get("FOA_LAYOUT_ASSETS", "").split(",") if p.strip()]
    dry = "--dry-run" in os.environ.get("FOA_FLAGS", "").split()
    dirty = {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    for p in paths:
        a = unreal.load_asset(p)
        if a is None:
            print("graph_layout", {"asset": p, "error": "not found"})
            continue
        if a.get_outermost().get_name() in dirty:  # another lane's unsaved, maybe half-built graph
            print("graph_layout", {"asset": p, "skipped": "unsaved changes in the editor"})
            continue
        if isinstance(a, unreal.Material) and (
                a.get_editor_property("material_domain") == unreal.MaterialDomain.MD_POST_PROCESS):
            print("graph_layout", {"asset": p, "skipped": "post-process material: take it off PP_DreamMono first"})
            continue
        s = layout_material(a, dry_run=dry)
        del a
        moves, boxes = s.pop("moves"), s.pop("boxes")
        s.pop("graph")
        print("graph_layout", {k: (len(v) if k == "calls" else v) for k, v in s.items()})
        if dry:
            for n, (x0, y0, x, y) in moves.items():
                print("  move %-48s (%6d,%6d) -> (%6d,%6d)" % (n, x0, y0, x, y))
            for c, (old, new) in boxes.items():
                print("  box  %-48s %s -> %s" % (c, old, new))


if __name__ == "__main__":
    main()
