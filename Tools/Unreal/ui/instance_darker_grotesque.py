"""Static Medium (500), SemiBold (600) and ExtraBold (800) TTFs from Google Fonts' variable Darker Grotesque
(UE font faces render a variable font at its default instance only). Offline: python -P <this> ; output next to
the source in P:/FoA-Assets/fonts/DarkerGrotesque. Licence OFL 1.1, no Reserved Font Name, so instances keep the name."""
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

D = 'P:/FoA-Assets/fonts/DarkerGrotesque'
for style, wght in (('Medium', 500), ('SemiBold', 600), ('ExtraBold', 800)):
    f = instantiateVariableFont(TTFont(f'{D}/DarkerGrotesque[wght].ttf'), {'wght': wght}, updateFontNames=True)
    f.save(f'{D}/DarkerGrotesque-{style}.ttf')
    n = f['name']
    print(style, f['OS/2'].usWeightClass, n.getDebugName(4), '|', n.getDebugName(6))
