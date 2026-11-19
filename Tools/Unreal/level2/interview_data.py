"""Authored conversation, evidence and local interview rules. No editor imports."""
ROOT='/Game/FoA/Level2/Journey'
WIDGET=ROOT+'/WBP_L2Interview'
ORIGIN=(30000,-110000,0)
SPLAT='/Game/FoA/Level2/Dream/SM_DreamInterview/StaticMeshes/SM_DreamInterview'
SKY='/Game/FoA/Level2/Dream/M_L2_PanoSky'
# V2 measured SPZ: X +/-222.66, Y +/-410.67, Z0..290.99. FloorZ27,
# platformZ37. Player(80,320) has no waist/head-height obstructions within30cm.
# Native framing still needs proof; the setup rejects the superseded v1 bounds.
STAGING_MEASURED=True
SPLAT_SIZE=(445.32,821.34,290.99)
BACKDROP=(0,0,-27)
CAMERA=((170,233,155),(-5,180,0))
PLAYER=(80,320,92)
PLAYER_YAW=180
DESK=(-40,233,10)
INTERVIEWER=(-120,233,0)
IDLE_SOURCE='/Game/FoA/Characters/Player/Anims/GASP/AS_GASP_M_Relaxed_Stand_Idle_Loop'
IDLE=ROOT+'/Animation/AS_GASP_M_Relaxed_Stand_Idle_Loop_Interview'
SUIT='/Game/FoA/Characters/Teen/Mesh/SK_Teen_Suit'
SUIT_MATERIAL='/Game/FoA/Characters/Teen/Cloth/MI_Teen_Suit'
SETTLE_SECONDS=.35
MAX_COMPOSURE=100


def geometry_size(padded,positive,negative):
    """Undo render-only ellipse bounds padding without changing the authored frame."""
    return tuple(float(size)-float(plus)-float(minus) for size,plus,minus in zip(padded,positive,negative))


NOTES=(
    'Name the task. Say what you did. Give the result. A job title is not evidence.',
    'Match the item to its label. Check the shelf before you move anything.',
    'Give a start time you can keep. If you will be late, call before that time.',
)


def answer(text,reply,cost=0):return dict(text=text,reply=reply,cost=cost)


CONTACTS=(
 dict(speaker='Career adviser',question='First application? Tell me what you need help with.',
      choices=(answer('I have never had a job. What can I put down?',
                      'Something you have actually done. Take a ticket, then we will find one example.'),
               answer('My C.V. is mostly empty. Can you help me make it sound better?',
                      'Clearer, yes. Bigger, no. Take ticket eighteen. We will start with the facts.'),
               answer('I need work today. Is anybody hiring?',
                      'The grocery and the office tower are taking applications. Take a ticket first; they will ask for an example.')),
      task='Take ticket 18 from the tray.',
      debrief='Eighteen. You are up. What is one thing you have finished recently?',
      responses=(answer('I put my room back in order. I had to decide where to start.',
                        'Good. Task, action, result. Explain the decision, not an impressive job title.'),
                 answer('Interior management. Five years of it.',
                        'That is a title. Under it, write what you actually did. Someone will ask.'),
                 answer('Nothing that counts as work.',
                        'Unpaid does not mean nothing. You put the room in order. Start there.'))),
 dict(speaker='Grocery supervisor',question='The late shift is full. Can you help me with this shelf while we talk?',
      choices=(answer('Show me what needs doing.',
                      'Three labels have slipped. Check which item belongs over each one, then straighten them.'),
               answer('Would helping count as experience?',
                      'It would be something you did. Check the items against the labels first. We do not guess here.'),
               answer('I can move quickly. Where do I start?',
                      'Start by looking. Fast is no use if a customer takes the wrong thing. Face those three labels.')),
      task='Check and face the three shelf labels.',
      debrief='They are straight. What did you check before you moved them?',
      responses=(answer('The item above each label. Then I put the label square beneath it.',
                        'Exactly. Match, then move. That is the part to remember.'),
                 answer('I made the whole row look even.',
                        'Even helps. Correct matters more. Match each item to its label before you move it.'),
                 answer('I assumed the person before me had put them in the right place.',
                        'Do not build your work on an unchecked guess. Match the item and the label. Every time.'))),
 dict(speaker='Receptionist',question='There is an interview upstairs. Before I send you in, when could you start?',
      choices=(answer('Tomorrow morning. I can plan for that.',
                      'Then give a time you can keep. Take a seat and think through the journey here.'),
               answer('Immediately. Any time at all.',
                      'That sounds generous. It is not a schedule. Sit down and give me a real time.'),
               answer('I am worried I will not manage it.',
                      'Then make a plan for the difficult part. Sit for a moment. You are here now.')),
      task='Sit down and make a start-time plan.',
      debrief='The morning goes wrong. You cannot make the time you promised. What do you do?',
      responses=(answer('Call before I am due. Explain, give a new time, and keep them updated.',
                        'That is dependable. It is not the promise that nothing will ever go wrong.'),
                 answer('Promise I will never be late.',
                        'Nobody can promise that. Call before your start time. Give a time you can actually keep.'),
                 answer('Get there as fast as I can and explain afterwards.',
                        'Call first. Otherwise someone is waiting without knowing whether you are coming.'))),
)

# Each opening answer changes the following question AND its three complete
# answer texts. Replies acknowledge the exact words the player chose.
SECTIONS=(
 dict(topic='Experience',question='Your C.V. says five years in interior management. What did that work involve?',
      choices=(answer('It was unpaid work at home. I organised a room that I had stopped looking after.',
                      'Thank you for being clear. Tell me what you did, in order.'),
               answer('I managed an interior and kept everything running.',
                      'That is the wording on the page. I need the work underneath it.',15),
               answer('I ran a team responsible for several properties.',
                      'Several properties? Who else was on that team?',35)),
      followups=(
       dict(question='What did you tackle first, and how did you know you were finished?',choices=(
        answer('I cleared the space, grouped related things, then checked the room was usable.',
               'A sequence and a result. I can understand that.'),
        answer('I worked until I was tired.', 'Effort matters, but tired is not a finished task.',15),
        answer('I do not remember. It was only my room.', 'You have made your own example disappear.',35))),
       dict(question='Leave the title aside. Describe one decision you made in that room.',choices=(
        answer('I cleared the blocked space, grouped related things, then checked the result.',
               'That is the useful answer. Keep the decision in the story.'),
        answer('I maintained the interior to a high standard.', 'You have replaced one title with another.',35),
        answer('I should have done it sooner.', 'Perhaps. I asked what you did when you started.',15))),
       dict(question='Name one person you supervised, and one property outside your home.',choices=(
        answer('I overstated it. My real example is organising my room. I can explain that.',
               'Correcting the claim costs you less than inventing another person.'),
        answer('I cannot discuss my previous clients.', 'You are asking me to trust a claim you cannot support.',35),
        answer('It was informal. There are no records.', 'Then be precise about what you can stand behind.',15))),
      )),
 dict(topic='Skills',question='At the grocery, what did you do before you straightened the shelf labels?',
      choices=(answer('I checked the item above each label. Then I put the label square beneath it.',
                      'You checked the relationship before you changed it. Good.'),
               answer('I made the row look tidy as quickly as I could.',
                      'Tidy is visible. Correct is less visible. Let us separate the two.',15),
               answer('I reorganised their stock system.',
                      'Their whole stock system? You were there for a few minutes.',35)),
      followups=(
       dict(question='One item does not match the label. What would you do next?',choices=(
        answer('Check the item and ask the supervisor before moving the label or the stock.',
               'You know where your information ends. That prevents a second mistake.'),
        answer('Move the item to whichever gap looks right.', 'An empty space is not proof that the item belongs there.',35),
        answer('Leave it for the next shift.', 'You have noticed a problem and passed it on without a word.',15))),
       dict(question='A neat label is under the wrong item. Is the shelf finished?',choices=(
        answer('No. I need to check the item against its label, then correct it with the supervisor.',
               'Now you are checking the work, not only its appearance.'),
        answer('Yes. Customers can work out what it means.', 'The customer should not have to repair your assumption.',35),
        answer('I would straighten it again.', 'Straightening the wrong answer does not make it correct.',15))),
       dict(question='Which part of their stock system did you change?',choices=(
        answer('Three labels. I checked the items, faced the labels and reported what I did.',
               'A small completed task is useful. Keep it that size.'),
        answer('I improved the entire workflow.', 'There is no example behind that sentence.',35),
        answer('I do not think the details matter.', 'The details are how I know whether you did the work.',15))),
      )),
 dict(topic='Availability',question='You wrote available immediately. Give me a start time you can actually keep.',
      choices=(answer('Tomorrow at nine. I will plan the trip tonight and leave time for a delay.',
                      'A time and a plan. Now tell me what happens when the plan changes.'),
               answer('Any time. I will never let you down.',
                      'Nobody can promise that. I want to hear how you handle a difficult morning.',15),
               answer('Whenever I wake up. I work better without a fixed time.',
                      'Someone else would be waiting for you. That is part of this job.',35)),
      followups=(
       dict(question='It is eight thirty. The car will not start. You are due at nine. What do you do?',choices=(
        answer('Call now, explain the delay, arrange another route, and give a realistic arrival time.',
               'You have kept the person waiting informed. That is a workable plan.'),
        answer('Keep trying the car until nine, then call.', 'You knew early enough to warn them. Use that time.',15),
        answer('Say I am already on my way.', 'That buys a few minutes and loses your credibility.',35))),
       dict(question='You have promised never to be late. Tomorrow the car will not start. What do you say?',choices=(
        answer('I cannot promise that today. I will call before nine and agree a realistic time.',
               'That is more dependable than a perfect promise.'),
        answer('Nothing. I will fix it before anybody notices.', 'Silence leaves another person planning around a fiction.',35),
        answer('I will apologise when I arrive.', 'An apology afterwards does not replace a warning beforehand.',15))),
       dict(question='Your colleague starts at nine and cannot leave until you arrive. What changes?',choices=(
        answer('My start time affects them. I will plan for nine and call first if I cannot make it.',
               'Now there is another person in your plan. Keep them there.'),
        answer('They should be flexible too.', 'Flexibility has to be agreed. You cannot assign it to somebody else.',35),
        answer('I would try to get there earlier.', 'Trying is a beginning. Give them a time and a way to reach you.',15))),
      )),
)


# Keep the follow-up paired with its opening answer while varying visible order.
_AUTHORED_SECTIONS=SECTIONS
_OPENING_ORDERS=((1,0,2),(0,2,1),(1,2,0))
_FOLLOWUP_ORDERS=(((1,2,0),(1,0,2),(1,0,2)),((2,0,1),(1,2,0),(2,1,0)),((0,2,1),(1,0,2),(2,0,1)))
SECTIONS=tuple(dict(section,choices=tuple(section['choices'][i] for i in order),
    followups=tuple(dict(section['followups'][i],choices=tuple(section['followups'][i]['choices'][n]
        for n in _FOLLOWUP_ORDERS[index][i])) for i in order))
    for index,(section,order) in enumerate(zip(_AUTHORED_SECTIONS,_OPENING_ORDERS)))


def question(step,prior=0):
    section=SECTIONS[step//2]
    return section if step%2==0 else section['followups'][max(0,min(2,prior))]


def resolve(step,prior,choice,composure):
    assert 0<=step<6 and 0<=choice<3
    row=question(step,prior);picked=row['choices'][choice]
    remaining=max(0,composure-picked['cost'])
    return dict(step=step+1,prior=choice if step%2==0 else prior,composure=remaining,
                score=60 if remaining==0 else 60+(40*(step+1)//6),failed=remaining==0,won=remaining>0 and step==5,
                player=picked['text'],reply=picked['reply'])
