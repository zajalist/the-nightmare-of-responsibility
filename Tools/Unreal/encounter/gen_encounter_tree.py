"""Emits the Hayba ui_build_tree JSON for WBP_Encounter's designer tree (under the root canvas), styled from
F_FoA_Typography. Functional layout for the battle; the UI lane owns the final look and may restyle anything here
(the graph only needs the names). 1920x1080:
  top centre     the battle log (one line of narration in a quiet panel)
  left middle    the enemy line: five rows of name, progress pips and its intent line
  bottom left    the command window: the target and its Act moves; Breathe, Mirror, Items, Flee, Next target
  bottom right   Composure and Resolve, and the Nightmare's statuses
  centre         the timed key prompt; a floating damage number moved over whoever was hit
  python Tools/Unreal/encounter/gen_encounter_tree.py > tree.json"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from make_typography import DEST, FONT, STYLES  # noqa: E402

SAND_BUTTON = "/Game/FoA/UI/Widgets/Common/WBP_SandButton.WBP_SandButton_C"
INK = (0.86, 0.86, 0.86)
ROWS, PIPS, ACTS = 5, 6, 3


def color(rgb, a):
    return f"(SpecifiedColor=(R={rgb[0]},G={rgb[1]},B={rgb[2]},A={a}),ColorUseRule=UseColor_Specified)"


def text(name, style, s, alpha=None, wrap=0, just=None, size=None):
    font, face, pt, track, lh, casing, col, shadow = STYLES[style]
    p = {"Text": s,
         "Font": f"(FontObject=\"/Script/Engine.Font'{DEST}/{FONT[font]}.{FONT[font]}'\",TypefaceFontName=\"{face}\","
                 f"Size={size or pt},LetterSpacing={track})",
         "ColorAndOpacity": color(col[:3], alpha if alpha is not None else col[3]),
         "LineHeightPercentage": lh, "TextTransformPolicy": casing,
         "ShadowOffset": "(X=0.0,Y=1.5)", "ShadowColorAndOpacity": "(R=0.0,G=0.0,B=0.0,A=0.85)"}
    if wrap:
        p["WrapTextAt"] = wrap
    if just:
        p["Justification"] = just
    return {"class": "TextBlock", "name": name, "properties": p}


def slot(node, **sp):
    node["slot_props"] = sp
    return node


def pad(node, left=0, top=0, right=0, bottom=0, **sp):
    return slot(node, padding=[left, top, right, bottom], **sp)


def canvas(node, anchor, align, pos, size=None):
    sp = {"anchors_min": anchor, "anchors_max": anchor, "alignment": align, "position": pos, "auto_size": size is None}
    if size:
        sp["size"] = size
    return slot(node, **sp)


def vbox(name, children):
    return {"class": "VerticalBox", "name": name, "children": children}


def hbox(name, children):
    return {"class": "HorizontalBox", "name": name, "children": children}


def pip(name, d):
    return pad({"class": "Image", "name": name, "properties": {
        "Brush": f"(ImageSize=(X={d},Y={d}),DrawAs=RoundedBox,TintColor=(SpecifiedColor=(R=1,G=1,B=1,A=1)),"
                 f"OutlineSettings=(RoundingType=HalfHeightRadius))",
        "ColorAndOpacity": f"(R={INK[0]},G={INK[1]},B={INK[2]},A=1.0)"}}, right=9, vertical_alignment="Center")


def bar(name, w=360, h=4):
    return {"class": "SizeBox", "name": f"Size_{name}", "properties": {"HeightOverride": h, "WidthOverride": w},
            "children": [{"class": "ProgressBar", "name": name, "properties": {
                "Percent": 1.0,
                "WidgetStyle": "(BackgroundImage=(DrawAs=Box,TintColor=(SpecifiedColor=(R=0.86,G=0.86,B=0.86,A=0.16))),"
                               "FillImage=(DrawAs=Box,TintColor=(SpecifiedColor=(R=1,G=1,B=1,A=1))),"
                               "MarqueeImage=(DrawAs=NoDrawType))",
                "FillColorAndOpacity": f"(R={INK[0]},G={INK[1]},B={INK[2]},A=1.0)"}}]}


def button(name, label):
    return pad({"class": SAND_BUTTON, "name": name, "properties": {"Label": label}}, bottom=8)


def panel(name, child, padding="(Left=28,Top=16,Right=28,Bottom=18)"):
    return {"class": "Border", "name": name, "properties": {
        "Background": "(DrawAs=RoundedBox,TintColor=(SpecifiedColor=(R=0,G=0,B=0,A=0.55)),"
                      "OutlineSettings=(CornerRadii=(X=6,Y=6,Z=6,W=6),Color=(SpecifiedColor=(R=0.86,G=0.86,B=0.86,A=0.22)),"
                      "Width=1,RoundingType=FixedRadius))",
        "Padding": padding}, "children": [child]}


def stat(label, top):
    return pad(vbox(f"Box_{label}", [
        hbox(f"Row_{label}", [pad(text(f"Txt_{label}Label", "HUDPrompt", label), right=24, fill=1),  # gap before the number
                              text(f"Txt_{label}", "HUDPrompt", "100")]),
        pad(bar(f"Bar_{label}"), top=10),
    ]), top=top)


def enemy_row(i):
    return pad(vbox(f"Row{i}", [
        text(f"Txt_Enemy{i}", "H2", "The Shirt (inside out)", size=24),
        pad(hbox(f"Pips{i}", [pip(f"Pip{i}_{k}", 10) for k in range(PIPS)]), top=6),
        pad(text(f"Txt_Intent{i}", "Narration", "The tie rears back and goes very still.", alpha=0.7, size=18), top=4),
    ]), bottom=8)  # 5 rows clear both the HUD objective above and the command box below


tree = [
    canvas(panel("LogPanel", text("Txt_Narration", "Narration", "The Shirt (inside out) blocks your way.", wrap=900,
                                  just="Center", size=26)), [0.5, 0], [0.5, 0], [0, 56]),
    canvas(vbox("EnemyRows", [enemy_row(i) for i in range(ROWS)]), [0, 0.5], [0, 0.5], [96, -110]),
    canvas(hbox("CommandBox", [
        pad(vbox("ActBox", [
            text("Txt_Target", "H2", "The Shirt (inside out)", size=22),
            pad(vbox("ActButtons", [button(f"Btn_Act{i}", "Button Up") for i in range(ACTS)]), top=10),
        ]), right=40),
        vbox("CmdButtons", [button("Btn_Breathe", "Breathe"), button("Btn_Mirror", "Mirror"),
                            button("Btn_Items", "Items"), button("Btn_Flee", "Flee"),
                            button("Btn_NextTarget", "Next target")]),
    ]), [0, 1], [0, 1], [96, -72]),
    canvas(vbox("SelfBox", [stat("Composure", 0), stat("Resolve", 22),
                            pad(text("Txt_Statuses", "Body", "The tie is tight", alpha=0.7), top=18)]),
           [1, 1], [1, 1], [-120, -96]),
    canvas(vbox("PromptBox", [
        slot({"class": "Border", "name": "KeyCap", "properties": {
            "Background": "(DrawAs=RoundedBox,TintColor=(SpecifiedColor=(R=0,G=0,B=0,A=0.35)),"
                          "OutlineSettings=(CornerRadii=(X=10,Y=10,Z=10,W=10),"
                          "Color=(SpecifiedColor=(R=0.86,G=0.86,B=0.86,A=0.9)),Width=2,RoundingType=FixedRadius))",
            "Padding": "(Left=30,Top=10,Right=30,Bottom=12)"},
            "children": [text("Txt_PromptKey", "KeyCap", "W", just="Center", size=44)]}, horizontal_alignment="Center"),
        pad(bar("Bar_Window", 180, 3), top=18, horizontal_alignment="Center"),
        pad(hbox("Pips_Hits", [pip(f"PipHit{k}", 10) for k in range(3)]), top=14, horizontal_alignment="Center"),
    ]), [0.5, 0.5], [0.5, 0.5], [0, 120]),
    canvas(text("Txt_Damage", "H1", "+2", size=54), [0, 0], [0.5, 1.0], [0, 0]),
]

# Every widget the graph reads is a variable (panels and some leaf widgets default to not being one).
READ = {"Txt_Narration", "EnemyRows", "Txt_Target", "ActButtons", "Btn_Breathe", "Btn_Mirror", "Btn_Items", "Btn_Flee",
        "Btn_NextTarget", "Txt_Composure", "Bar_Composure", "Txt_Resolve", "Bar_Resolve", "Txt_Statuses", "PromptBox",
        "Txt_PromptKey", "Bar_Window", "Pips_Hits", "Txt_Damage"} | {f"Btn_Act{i}" for i in range(ACTS)}


def mark_vars(node):
    if node.get("name") in READ:
        node.setdefault("properties", {})["bIsVariable"] = True
    for c in node.get("children", []):
        mark_vars(c)


for n in tree:
    mark_vars(n)

if __name__ == "__main__":
    print(json.dumps(tree, ensure_ascii=True))
