"""Offline bounds, authored text fit and L1 isolation for the unified L2 treatment."""
import unittest
import math
from pathlib import Path
from PIL import Image,ImageFont
import l2_ink_style as s
import interview_data as d


def rect(slot,width,height):
    amin=slot.get('anchors_min',[0,0]);amax=slot.get('anchors_max',amin)
    pos=slot['position'];size=slot['size'];align=slot.get('alignment',[0,0])
    w=width*(amax[0]-amin[0])-pos[0]-size[0] if amax[0]!=amin[0] else size[0]
    return (width*amin[0]+pos[0]-align[0]*w,height*amin[1]+pos[1]-align[1]*size[1],w,size[1])


class InkStyleTests(unittest.TestCase):
    def test_canvas_edges_fit_1280_and_1920(self):
        for width,height in ((1280,720),(1920,1080)):
            for path,rows in s.plans().items():
                for row in rows:
                    if 'position' not in row.get('slot_props',{}):continue
                    x,y,w,h=rect(row['slot_props'],width,height)
                    self.assertTrue(x>=0 and y>=0 and w>0 and h>0 and x+w<=width and y+h<=height,
                                    (path,row['name'],width,(x,y,w,h)))
                    angle=math.radians(row.get('properties',{}).get('RenderTransform',{}).get('Angle',0))
                    rw=abs(w*math.cos(angle))+abs(h*math.sin(angle))
                    rh=abs(w*math.sin(angle))+abs(h*math.cos(angle))
                    self.assertTrue(x+w/2-rw/2>=0 and y+h/2-rh/2>=0 and
                                    x+w/2+rw/2<=width and y+h/2+rh/2<=height,
                                    (row['name'],'rotated bounds',width))

    def test_phone_edits_are_only_l2_children(self):
        for row in s.plans()[s.PHONE]:self.assertIn('L2',row['name'])

    def test_compact_phone_claims_fit_one_line_above_thumb(self):
        import phone_progress_data
        font=ImageFont.truetype('P:/FoA-Assets/fonts/DarkerGrotesque/DarkerGrotesque-SemiBold.ttf',36)
        for line in phone_progress_data.PHONE_REVISIONS:
            self.assertLessEqual(font.getlength(line),428,line)
        rows={row['name']:row for row in s.plans()[s.PHONE]}
        self.assertEqual(rows['L2CVBlock']['slot_props']['padding'],[0,0,0,0])
        self.assertEqual(rows['Size_L2Employability']['slot_props']['padding'],[0,4,0,6])
        for i in range(3):self.assertEqual(rows['Txt_L2CV'+str(i)]['slot_props']['padding'],[0,0,0,4])

    def test_answer_frames_fill_the_button(self):
        for row in s.plans()[s.INTERVIEW]:
            if row['name'].startswith('AnswerPad'):
                self.assertEqual(row['slot_props'],dict(horizontal_alignment='Fill',vertical_alignment='Fill'))

    def test_answer_text_starts_past_actual_texture_slice(self):
        image=Image.open(s.SOURCE/'T_L2InkPanel.png').convert('RGBA')
        self.assertEqual(image.size,(1024,512))
        # Slate Box uses resource ActualSize, not desired brush ImageSize.
        inner_left=max(next(x for x in range(90) if image.getpixel((x,y))[:3]==(0,0,0)
                            and image.getpixel((x,y))[3]==255) for y in range(20,440))
        for row in s.plans()[s.INTERVIEW]:
            if row['name'].startswith('AnswerPad'):
                self.assertGreaterEqual(row['properties']['Padding'][0],inner_left+10)

    def test_authored_speakers_and_answers_fit(self):
        fonts=Path('P:/FoA-Assets/fonts/DarkerGrotesque')
        heading=ImageFont.truetype(str(fonts/'DarkerGrotesque-ExtraBold.ttf'),round(44*4/3))
        body=ImageFont.truetype(str(fonts/'DarkerGrotesque-SemiBold.ttf'),round(24*4/3))
        for speaker in [row['speaker'] for row in d.CONTACTS]+['Interviewer']:
            self.assertLessEqual(heading.getlength(speaker),544,speaker)
        answers=[]
        for row in d.CONTACTS:answers += row['choices']+row['responses']
        for section in d.SECTIONS:
            answers += section['choices']
            for follow in section['followups']:answers += follow['choices']
        for answer in answers:
            self.assertLessEqual(body.getlength(answer['text']),1020,answer['text'])
        self.assertNotIn('Persona',Path(s.__file__).read_text())

    def test_focus_red_keeps_white_text_contrast(self):
        # UE LinearColor values are already linear luminance contributions.
        luminance=sum(a*b for a,b in zip(s.RED[:3],(.2126,.7152,.0722)))
        self.assertGreaterEqual(1.05/(luminance+.05),4.5)

    def test_expressive_titles_keep_body_horizontal(self):
        for path in (s.INTERVIEW,s.JOURNEY,s.DRIVE):
            for row in s.plans()[path]:
                if row['name'] in ('Txt_Question','Txt_Answer0','Txt_Answer1','Txt_Answer2','Txt_Body','Txt_Hint'):
                    self.assertEqual(row['properties'].get('RenderTransform',{}).get('Angle',0),0)

    def test_feedback_has_room_for_player_line_and_reply(self):
        font=ImageFont.truetype('P:/FoA-Assets/fonts/DarkerGrotesque/DarkerGrotesque-SemiBold.ttf',round(24*4/3))
        rows=[]
        for contact in d.CONTACTS:rows+=contact['choices']+contact['responses']
        for section in d.SECTIONS:
            rows+=section['choices']
            for followup in section['followups']:rows+=followup['choices']
        for row in rows:
            lines=0
            for paragraph in ('You: '+row['text']+'\n\n'+row['reply']).split('\n'):
                lines+=1;current=''
                for word in paragraph.split():
                    trial=(current+' '+word).strip()
                    if font.getlength(trial)>1088:lines+=1;current=word
                    else:current=trial
            self.assertLessEqual(lines*sum(font.getmetrics()),176,row)

    def test_every_authored_journey_body_stays_above_the_hint(self):
        import ast
        import journey_data as j
        source=ast.parse(Path(__file__).with_name('build_journey.py').read_text())
        bodies=[n.args[2].value for n in ast.walk(source) if isinstance(n,ast.Call)
                and isinstance(n.func,ast.Name) and n.func.id=='text' and len(n.args)>2
                and isinstance(n.args[2],ast.Constant)]
        bodies += [row[key] for row in j.SCENES for key in ('arrival','acting','rejection')]
        bodies += [body for row in j.SCENES for body in row['dialogue']]
        bodies += [row['truth']+'\n\nBecomes\n'+row['revision'] for row in j.STOPS]
        bodies += [row['information'] for row in j.STOPS]
        rows={row['name']:row for row in s.plans()[s.JOURNEY]}
        body=rows['Txt_Body'];width,height=body['slot_props']['size']
        font=ImageFont.truetype('P:/FoA-Assets/fonts/DarkerGrotesque/DarkerGrotesque-SemiBold.ttf',36)
        for authored in bodies:
            compact=j.compact_body(authored)
            self.assertEqual(authored.split(),compact.split())
            lines=0
            for paragraph in compact.split('\n'):
                lines+=1;line=''
                for word in paragraph.split():
                    trial=(line+' '+word).strip()
                    if line and font.getlength(trial)>width:lines+=1;line=word
                    else:line=trial
            measured=sum(font.getmetrics())*(1+(lines-1)*body['properties']['LineHeightPercentage'])
            self.assertLessEqual(measured,height,(measured,authored))
        _,body_y,_,body_h=rect(body['slot_props'],1280,720)
        _,hint_y,_,_=rect(rows['Txt_Hint']['slot_props'],1280,720)
        self.assertGreaterEqual(hint_y-body_y-body_h,10)


if __name__=='__main__':unittest.main()
