"""Authored L2 stop text and progression, shared by the native Blueprint builder and checks."""
ROOT = '/Game/FoA/Level2/Journey'
BP = ROOT + '/BP_L2Journey'
HUD = ROOT + '/WBP_L2Journey'
OWNER = 'l2-journey'


def compact_body(value):
    """Keep paragraph boundaries without spending a full empty line on each."""
    return value.replace('\n\n','\n')


STOPS = (
    dict(place='Career Center',
         information='Ticket 18. Now serving 17.\n\nName an experience section. Household actions can be described.\n\nNo placement without experience.',
         truth='I have no job experience.',
         revision='5 Years of Experience in Interior Management.',
         flag='Knows.L2Experience', note='Name the task. Say what you did. Give the result. A job title is not evidence.'),
    dict(place='All-Night Grocery',
         information='Aisle 9. Stocking. Sorting. Inventory.\n\nYou straighten the labels.\n\nThank you. The position has been filled.',
         truth='I straightened some labels.',
         revision='3 Years of Experience in Warehousing and Office Logistics.',
         flag='Knows.L2Logistics', note='Match the item to its label. Check the shelf before you move anything.'),
    dict(place='Office',
         information='Your made bed is the only seat.\n\nWhen can you start?\n\nWe need someone dependable.',
         truth='I got out of bed today.',
         revision='Available Immediately. Reliable Under Pressure.',
         flag='Knows.L2Reliability', note='Give a start time you can keep. If you will be late, call before that time.'),
)

# Scene action precedes the original/replacement UI. No claimed grocery action
# appears in the C.V. until the actual label components have finished moving.
SCENES=(
    dict(arrival='The chairs are occupied. Nobody moves.\n\nNow serving seventeen.',
         action='Take ticket 18',acting='Eighteen. Of course it is eighteen.',
         dialogue=('CLERK\nPrevious experience.\n\nI have not had a job.\n\nWhat have you done at home?',
                   'Mostly stayed there.\n\nCLERK\nPut it under experience.\n\nThese two are taking applications. The grocery first.'),
         rejection='The adviser slides the page back.\n\n"I cannot place you today. Take that example to the grocery, then the office. Describe the work you actually did."'),
    dict(arrival='PA\nStaff to aisle nine.\n\nEvery aisle is aisle nine.\n\nStocking. Sorting. Inventory.',
         action='Face the shelf labels',acting='One label. Then the next.',
         dialogue=('They are straight now.\n\nThere is nobody here.',),
         rejection='The supervisor checks the rota.\n\n"The late shift has been filled. I am sorry. Keep the example. The office is still taking applications."'),
    dict(arrival='No stairs. No elevator.\n\nThat is my bed. Mom made it.\n\nRECEPTIONIST\nTake a seat.',
         action='Sit on the edge of the bed',acting='Sitting. Not lying down.',
         dialogue=('RECEPTIONIST\nWhen can you start?\n\nToday. I am here.',
                   'RECEPTIONIST\nThere is a gap in your history.\n\nSeventeen days.'),
         rejection='The receptionist hands the page back.\n\n"There is no opening at this desk. The interviewer upstairs is waiting. Give them a plan you can keep."'),
)

def employability(confirmed, progress):
    confirmed=max(0,min(3,confirmed))
    return 20*confirmed + (40*max(0,min(12,progress))//12 if confirmed==3 else 0)
