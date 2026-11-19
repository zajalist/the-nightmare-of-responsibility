from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
p=Path('P:/FoA/Saved/CharacterShots/mpfb/portrait_face')
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',19)
canvas=Image.new('RGB',(1520,1010),(28,28,30));d=ImageDraw.Draw(canvas)
ref=Image.open('C:/Users/Admin/AppData/Local/Temp/codex-clipboard-qcM2F0.png').convert('RGB')
canvas.paste(ref,(20,55));d.text((20,15),'Supplied portrait',font=font,fill='white')
d.multiline_text((20,490),'Visible contour interpretation\n\nExisting rig, eyes and hair retained.\nSkull and neck locked.\nNo FaceSlip in these previews.\n\nTop: current neutral face\nBottom: portrait variant',font=small,fill=(205,205,210),spacing=9)
for col,view in enumerate(('front','threequarter','profile')):
    x=390+col*376
    for row,label in enumerate(('before','after')):
        im=Image.open(p/f'{label}_{view}.png').convert('RGB');im.thumbnail((368,430))
        y=55+row*480;canvas.paste(im,(x,y));d.text((x,y-35),f'{label.title()} | {view}',font=font,fill='white')
canvas.save(p/'comparison.png')
print(p/'comparison.png')
