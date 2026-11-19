"""FoA type scale -> /Game/FoA/UI/Fonts/F_FoA_Typography, a DataTable of RichTextStyleRow (engine struct).
A RichTextBlock uses it directly as its Text Style Set; Blueprints read Row.TextStyle.Font for plain TextBlocks.
Sizes are UMG points at the 1920x1080 reference (px = pt * 4/3). Casing is the row's TransformPolicy.
Line height is not part of FTextBlockStyle, so LH below is TextBlock.LineHeightPercentage, which UMG multiplies
by the font's own line height (Darker Grotesque 1.36 em, mostly ascender room above the caps).
WBP_TypeSpecimen (same folder) shows every style applied and is generated from this table.
  python Tools/Unreal/ue_remote.py Tools/Unreal/make_typography.py"""
import csv
import io

DEST = "/Game/FoA/UI/Fonts"
FONT = {"Display": "F_FoA_Display", "UI": "F_FoA_UI"}
INK, DIM = (0.86, 0.86, 0.86, 1.0), (0.86, 0.86, 0.86, 0.62)  # linear; ~#EDEDED, secondary at 62%

# row: (font, typeface, size_pt, tracking_1/1000em, LineHeightPercentage, casing, color, shadow)
STYLES = {  # Darker Grotesque, sizes from the approved direction page v3 at 1920 px (pt = px x 0.75)
    "Default":     ("UI", "Medium", 20, 0, 1.0, "None", INK, False),            # = Body; RichText base row
    "Display":     ("Display", "ExtraBold", 110, 0, 0.85, "None", INK, False),  # logotype "The Nightmare" (11 vw)
    "Title":       ("UI", "SemiBold", 51, 0, 0.90, "None", INK, False),         # logotype "of Responsibility" (0.46 x)
    "H1":          ("Display", "ExtraBold", 59, 0, 0.90, "None", INK, False),   # pause headline: the current objective
    "H2":          ("Display", "ExtraBold", 52, 0, 0.90, "None", INK, False),   # dialog question
    "Narration":   ("UI", "Medium", 32, 0, 1.0, "None", INK, False),            # dream lines (no italic in this family)
    "Eyebrow":     ("UI", "SemiBold", 16, 0, 1.0, "None", DIM, False),          # kept for old lookups; plain, no caps
    "Menu":        ("UI", "SemiBold", 38, 0, 1.12, "None", DIM, False),         # main menu word (2.6 vw)
    "MenuActive":  ("UI", "SemiBold", 38, 0, 1.12, "None", INK, False),
    "MenuSmall":   ("UI", "SemiBold", 29, 0, 1.12, "None", INK, False),         # pause and dialog words (2.05 vw)
    "Body":        ("UI", "Medium", 20, 0, 1.0, "None", INK, False),            # dialog body (1.35 vw)
    "Caption":     ("UI", "Medium", 16, 0, 1.0, "None", DIM, False),            # build, hints, day line (1.1 vw)
    "Prompt":      ("UI", "SemiBold", 19, 0, 1.0, "None", INK, False),          # "Press any key" (1.3 vw)
    "HUDPrompt":   ("UI", "SemiBold", 26, 0, 1.0, "None", INK, True),           # interact sentence (1.8 vw)
    "Objective":   ("Display", "ExtraBold", 36, 0, 1.0, "None", INK, True),     # HUD objective (2.5 vw)
    "KeyCap":      ("Display", "ExtraBold", 12, 0, 1.0, "None", INK, False),    # glyph inside the key box (0.82 vw)
    "Subtitle":    ("UI", "SemiBold", 26, 0, 1.0, "None", INK, True),
    "Speaker":     ("UI", "SemiBold", 16, 0, 1.0, "None", DIM, True),
    "PhoneClock":  ("Display", "ExtraBold", 64, 0, 1.0, "None", INK, False),
    "Mono":        ("UI", "Medium", 18, 0, 1.0, "None", INK, False),            # phone and calendar rows (row name kept)
    "MonoLabel":   ("UI", "Medium", 15, 0, 1.0, "None", DIM, False),
}


def row_text(font, face, size, track, lh, casing, color, shadow):
    r, g, b, a = color
    s = (f"(Font=(FontObject=\"/Script/Engine.Font'{DEST}/{FONT[font]}.{FONT[font]}'\",TypefaceFontName=\"{face}\","
         f"Size={size},LetterSpacing={track}),"
         f"ColorAndOpacity=(SpecifiedColor=(R={r},G={g},B={b},A={a}),ColorUseRule=UseColor_Specified),"
         f"TransformPolicy={casing}")
    if shadow:  # soft drop shadow keeps HUD text readable over bright B&W frames
        s += ",ShadowOffset=(X=0.0,Y=1.5),ShadowColorAndOpacity=(R=0.0,G=0.0,B=0.0,A=0.85)"
    return s + ")"


if __name__ == "__main__":
    import unreal  # editor-only; STYLES stays importable outside UE (the specimen tree is generated from it)

    path = f"{DEST}/F_FoA_Typography"
    dt = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if dt is None:
        fac = unreal.DataTableFactory()
        fac.set_editor_property("struct", unreal.RichTextStyleRow.static_struct())
        dt = unreal.AssetToolsHelpers.get_asset_tools().create_asset("F_FoA_Typography", DEST, unreal.DataTable, fac)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["Name", "TextStyle"])
    for name, spec in STYLES.items():
        w.writerow([name, row_text(*spec)])
    assert unreal.DataTableFunctionLibrary.fill_data_table_from_csv_string(dt, buf.getvalue()), "CSV fill failed"
    names = [str(n) for n in unreal.DataTableFunctionLibrary.get_data_table_row_names(dt)]
    assert names == list(STYLES), names
    unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
    print("rows:", names)
