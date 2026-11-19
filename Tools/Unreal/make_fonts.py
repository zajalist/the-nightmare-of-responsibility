"""Creates FoA's composite Font assets (Runtime cache) in /Game/FoA/UI/Fonts, named by role so a family swap
never breaks a widget reference. Typeface entries are filled by Hayba object_set_property (FFontData is not
exposed to Python): see COMPOSITE below for the exact strings.
  python Tools/Unreal/ue_remote.py Tools/Unreal/make_fonts.py"""
import unreal

DEST = "/Game/FoA/UI/Fonts"
FACES = "/Game/FoA/UI/Fonts/Faces"
FONTS = {  # first typeface = the fallback for any widget that names a typeface the font lacks
    "F_FoA_Display": ("DarkerGrotesque", ["ExtraBold"]),            # 800: logotype, titles
    "F_FoA_UI": ("DarkerGrotesque", ["SemiBold", "Medium"]),        # 600 menus and prompts, 500 small UI
}


def composite(fam, styles):
    entries = ",".join(
        f'(Name="{s}",Font=(FontFaceAsset="/Script/Engine.FontFace\'{FACES}/FF_{fam}_{s}.FF_{fam}_{s}\'",'
        f"LoadingPolicy=LazyLoad,Hinting=Default))" for s in styles)
    return f"(DefaultTypeface=(Fonts=({entries})))"


COMPOSITE = {name: composite(*spec) for name, spec in FONTS.items()}

if __name__ == "__main__":
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    for name in FONTS:
        path = f"{DEST}/{name}"
        font = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else \
            tools.create_asset(name, DEST, unreal.Font, unreal.FontFactory())
        font.set_editor_property("font_cache_type", unreal.FontCacheType.RUNTIME)
        font.set_editor_property("legacy_font_name", FONTS[name][1][0])  # typeface used when a widget names none
        unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
        print(name, "ok")
    for name, value in COMPOSITE.items():
        print(f"COMPOSITE {name} {value}")
