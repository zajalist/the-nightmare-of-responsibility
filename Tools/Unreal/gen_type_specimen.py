"""Emits the Hayba ui_build_tree JSON for /Game/FoA/UI/Fonts/WBP_TypeSpecimen from make_typography.STYLES.
  python Tools/Unreal/gen_type_specimen.py > tree.json   (then ui_build_tree under RootCanvas, BG anchored 0,0,1,1)"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_typography import DEST, FONT, STYLES  # noqa: E402

FAMILY = {"Display": "Cormorant", "UI": "Plex Sans", "Mono": "Plex Mono"}


def color(rgba):
    r, g, b, a = rgba
    return f"(SpecifiedColor=(R={r},G={g},B={b},A={a}),ColorUseRule=UseColor_Specified)"


def text(name, style, s, alpha=None, wrap=0, just=None):
    font, face, size, track, lh, casing, col, shadow = STYLES[style]
    p = {
        "Text": s,
        "Font": f"(FontObject=\"/Script/Engine.Font'{DEST}/{FONT[font]}.{FONT[font]}'\",TypefaceFontName=\"{face}\","
                f"Size={size},LetterSpacing={track})",
        "ColorAndOpacity": color(col[:3] + (alpha if alpha is not None else col[3],)),
        "LineHeightPercentage": lh,
        "TextTransformPolicy": casing,
    }
    if shadow:
        p["ShadowOffset"] = "(X=0.0,Y=1.5)"
        p["ShadowColorAndOpacity"] = "(R=0.0,G=0.0,B=0.0,A=0.85)"
    if wrap:
        p["WrapTextAt"] = wrap
    if just:
        p["Justification"] = just
    return {"class": "TextBlock", "name": name, "properties": p}


def spec(style, extra=""):
    font, face, size, track, lh, casing, _, _ = STYLES[style]
    t = f"{style} · {FAMILY[font]} {face} · {size:g}/{lh:g}/{track:+d}".replace("/+0", "/0")
    t += " · caps" if casing == "ToUpper" else ""
    return t + extra


def label(name, s):
    return text(name, "MonoLabel", s, alpha=0.36)


def pad(node, top=0, bottom=0, left=0, right=0, fill=None, halign=None, valign=None):
    sp = {"padding": [left, top, right, bottom]}  # Hayba slot keys, not UE struct strings (those are dropped)
    if fill is not None:
        sp["fill"] = fill
    if halign:
        sp["horizontal_alignment"] = halign
    if valign:
        sp["vertical_alignment"] = valign
    node["slot_props"] = sp
    return node


def vbox(name, children):
    return {"class": "VerticalBox", "name": name, "children": children}


def hbox(name, children):
    return {"class": "HorizontalBox", "name": name, "children": children}


def gap(name, h):
    return {"class": "Spacer", "name": name, "properties": {"Size": f"(X=1.0,Y={h})"}}


def rule(name, alpha=0.14):
    return {"class": "Image", "name": name,
            "properties": {"Brush": "(ImageSize=(X=8.0,Y=1.0))", "ColorAndOpacity": f"(R=1.0,G=1.0,B=1.0,A={alpha})"}}


def box(name, child, fill_rgba, outline_rgba, radius, width, padding):
    fr, fg, fb, fa = fill_rgba
    orr, og, ob, oa = outline_rgba
    return {"class": "Border", "name": name, "properties": {
        "Background": f"(DrawAs=RoundedBox,TintColor=(SpecifiedColor=(R={fr},G={fg},B={fb},A={fa})),"
                      f"OutlineSettings=(CornerRadii=(X={radius},Y={radius},Z={radius},W={radius}),"
                      f"Color=(SpecifiedColor=(R={orr},G={og},B={ob},A={oa})),Width={width},RoundingType=FixedRadius))",
        "Padding": padding}, "children": [child]}


BLACK = (0.0, 0.0, 0.0, 1.0)  # pure black: offscreen render double-encodes sRGB, so near-black would preview grey

serif = vbox("ColSerif", [
    label("L_Display", spec("Display")),
    pad(text("T_Display", "Display", "FoA"), top=6),
    pad(label("L_Title", spec("Title")), top=10),
    pad(text("T_Title", "Title", "The Nightmare of Responsibility"), top=14),
    gap("Gap_S1", 44), rule("Rule_Serif1"), gap("Gap_S2", 40),
    label("L_Eyebrow", spec("Eyebrow")),
    pad(label("L_H1", spec("H1")), top=6),
    pad(text("T_Eyebrow", "Eyebrow", "Chapter II"), top=22),
    pad(text("T_H1", "H1", "The Bedroom, Again"), top=12),
    pad(label("L_H2", spec("H2")), top=40),
    pad(text("T_H2", "H2", "Things You Said You Would Do"), top=10),
    pad(label("L_Narration", spec("Narration")), top=36),
    pad(text("T_Narration", "Narration",
             "The keys were never where you left them.", wrap=640), top=10),
])

keycap = box("KeyCapBox", text("T_KeyCap", "KeyCap", "E", just="Center"),
             (0, 0, 0, 0), (0.86, 0.86, 0.86, 0.85), 4, 1.5, "(Left=9,Top=4,Right=9,Bottom=4)")
ui = vbox("ColUI", [
    label("L_Menu", spec("MenuActive")),
    pad(label("L_Menu2", spec("Menu")), top=6),
    pad(text("T_MenuActive", "MenuActive", "Continue"), top=18),
    pad(text("T_Menu1", "Menu", "New Game"), top=10),
    pad(text("T_Menu2", "Menu", "Settings"), top=10),
    pad(text("T_Menu3", "Menu", "Quit"), top=10),
    pad(label("L_Body", spec("Body")), top=40),
    pad(text("T_Body", "Body",
             "Your mother called three times. The plumber did not. Somewhere in this room is the thing you "
             "promised to do on Monday, and it has been waiting, very patiently, since Monday.", wrap=480), top=12),
    pad(label("L_Caption", spec("Caption")), top=30),
    pad(text("T_Caption", "Caption", "Autosaved 08:45. Progress is kept when you quit to the menu."), top=10),
    pad(label("L_HUD", spec("HUDPrompt")), top=40),
    pad(label("L_KeyCap", spec("KeyCap")), top=6),
    pad(hbox("HUDRow", [
        pad(keycap, valign="Center"),
        pad(text("T_HUDPrompt", "HUDPrompt", "Pick up the keys"), left=14, valign="Center"),
    ]), top=16),
    pad(label("L_Speaker", spec("Speaker")), top=40),
    pad(label("L_Subtitle", spec("Subtitle")), top=6),
    pad(text("T_Speaker", "Speaker", "Mom"), top=16),
    pad(text("T_Subtitle", "Subtitle", "You said you'd call the plumber. You promised.", wrap=480), top=6),
])

phone_inner = vbox("PhoneStack", [
    pad(text("T_PhoneDate", "MonoLabel", "Tue 14 Nov"), halign="Center"),
    pad(text("T_PhoneClock", "PhoneClock", "08:45", just="Center"), top=6, halign="Center"),
    gap("Gap_P1", 26), rule("Rule_Phone", 0.14), gap("Gap_P2", 22),
    text("T_Cal1", "Mono", "09:30  Dentist (moved twice)"),
    pad(text("T_Cal2", "Mono", "11:00  Call the plumber"), top=8),
    pad(text("T_Cal3", "Mono", "--:--  Responsibility", alpha=0.45), top=8),
    gap("Gap_P3", 22), rule("Rule_Phone2", 0.14), gap("Gap_P4", 20),
    text("T_Missed", "MonoLabel", "3 missed calls · Mom"),
])
phone = vbox("ColPhone", [
    label("L_Phone", "IBM Plex Mono"),
    pad(label("L_PhoneClock", spec("PhoneClock").replace("Plex Mono ", "")), top=6),
    pad(label("L_Mono", spec("Mono").replace("Plex Mono ", "")), top=6),
    pad(label("L_MonoLabel", spec("MonoLabel").replace("Plex Mono ", "").replace(" · caps", "")), top=6),
    pad({"class": "SizeBox", "name": "PhoneSize", "properties": {"WidthOverride": 360, "HeightOverride": 580},
         "children": [box("PhoneFrame", phone_inner, BLACK, (0.86, 0.86, 0.86, 0.22), 36, 1.5,
                          "(Left=30,Top=64,Right=30,Bottom=30)")]}, top=22),
])

tree = {"class": "Border", "name": "BG", "properties": {
    "Background": "(DrawAs=Image,TintColor=(SpecifiedColor=(R=0.0,G=0.0,B=0.0,A=1.0),ColorUseRule=UseColor_Specified))",
    "BrushColor": "(R=0.0,G=0.0,B=0.0,A=1.0)", "Padding": "(Left=120,Top=64,Right=120,Bottom=56)"},
    "children": [vbox("Page", [
        hbox("Header", [
            pad(text("T_HeaderL", "MonoLabel", "FoA  ·  Type specimen", alpha=0.62), fill=1),
            text("T_HeaderR", "MonoLabel", "F_FoA_Typography  ·  size pt / line-height % / tracking ‰  ·  1920×1080",
                 alpha=0.36),
        ]),
        gap("Gap_H1", 18), rule("Rule_Header"), gap("Gap_H2", 44),
        pad(hbox("Columns", [
            pad(serif, fill=1.3, right=88),
            pad(ui, fill=1, right=88),
            phone,
        ]), fill=1),
        hbox("Footer", [
            pad(text("T_FooterL", "MonoLabel",
                     "Cormorant Garamond · IBM Plex Sans · IBM Plex Mono  ·  SIL Open Font License 1.1", alpha=0.36), fill=1),
            text("T_FooterR", "Caption", "Il1 O0 rn m  0123456789", alpha=0.36),
        ]),
    ])]}
print(json.dumps(tree, ensure_ascii=True))
