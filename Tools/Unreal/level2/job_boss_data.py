"""The final interviewer tests judgement against the work on the player's C.V."""

from interview_data import answer

STARTING_COMPOSURE = 75
NOTES = (
    'Your C.V. records what you checked and what you actually sent.',
    'If an order can still be intercepted, prevent the mistake from leaving first.',
    'Give the person waiting a decision, an owner and a time for the next update.',
)


def turn(question,*choices):
    return dict(question=question,choices=choices)


def section(topic,opening,*followups):
    assert len(opening['choices'])==len(followups)==3
    return dict(topic=topic,**opening,followups=followups)


SECTIONS = (
    section('Evidence',turn('Your trial went well. What tells you that an order is actually ready to leave?',
        answer('A second person at the bench signs it off.', 'You’ve shifted the decision to somebody else. Who checks your work when they’re busy?',20),
        answer('The code and count agree with the request I’m sending it against.', 'Fine. Which request do you trust if two are on the bench?'),
        answer('It leaves on time and the receiving side hasn’t complained.', 'A quiet receiver may just be opening the wrong case.',37)),
        turn('You are alone for twenty minutes. What would you sign off yourself?',
            answer('Any order I’m familiar with. I’d save unfamiliar ones for the second checker.', 'Familiarity can still hide a changed code.',19),
            answer('Everything as long as I log my name against it.', 'That tells me who sent it. I asked how you knew it was right.',38),
            answer('Only orders I can match to a current request. I’d hold any that don’t match.', 'You’ve drawn a line you can defend.')),
        turn('Two requests share a number. One says two cases, one says three. The driver is waiting.',
            answer('Find out which revision is current before releasing either quantity.', 'You can explain the delay without guessing the order.'),
            answer('Send two. It’s easier to send one more than to ask for one back.', 'You’ve made a decision the order owner never made.',34),
            answer('Ask the driver which quantity the customer usually takes.', 'They can tell you what’s usual. That won’t resolve this request.',18)),
        turn('The receiving desk is closed until morning. What evidence would you leave behind?',
            answer('A note saying everything that should have gone out did.', 'That’s another claim without a check underneath it.',33),
            answer('The order numbers, the counts I checked and the cases I held.', 'Now the next shift can pick up where you stopped.'),
            answer('The time the truck left and my name.', 'Useful for tracing the truck. It still doesn’t tell them what went on it.',16))),
    section('Pressure',turn('You spot a wrong case on a trolley that has already left your bench. What do you do first?',
        answer('Correct the record while the exact numbers are still in my head.', 'Good record. The case is still moving.',24),
        answer('Tell my supervisor and wait for them to decide.', 'Waiting may cost us the chance to stop it.',16),
        answer('Stop the trolley if I can. If it’s out of reach, call dispatch with the order number.', 'You’ve kept the mistake within reach. Now repair it.')),
        turn('Dispatch can still pull it off the truck. What do you send them?',
            answer('The order number, the case code and a clear hold instruction.', 'They can act on that.'),
            answer('A copy of the corrected record.', 'They’ll need to work out what you need them to do.',18),
            answer('The whole manifest. They can see what changed.', 'You’ve given a busy person a second investigation.',35)),
        turn('Your supervisor won’t be back for five minutes. Who owns the next call?',
            answer('Dispatch. I’ll assume they’ll spot it on their own.', 'You saw it first. Waiting is a decision too.',39),
            answer('I do. I’ll ask dispatch to hold it and tell my supervisor what I’ve done.', 'You acted within the time you had.'),
            answer('I’ll leave a note for the supervisor and wait by the bay.', 'Stay there if you need to, but tell the people who can stop the case.',19)),
        turn('The trolley is stopped. The rest of the orders are correct. What can you release?',
            answer('The checked orders. Keep the one wrong case and its paperwork together.', 'That contains the issue without losing the rest of the shift.'),
            answer('Everything except the case that looks wrong. Check its code later.', 'You’ve got the time to identify it now.',18),
            answer('Nothing until tomorrow. I can’t be certain of any of it.', 'You’ve found one failure and frozen a whole shift.',31))),
    section('Responsibility',turn('The driver needs a decision at six tomorrow. You might be late. What do you do tonight?',
        answer('Set an earlier alarm. I’ll sort out the rest if it happens.', 'An alarm helps you. The driver still has no plan.',18),
        answer('Arrange a backup and agree who can cover the decision if I call in.', 'Good. Someone can act before six.'),
        answer('Promise I’ll be there. There’s no point raising a problem that hasn’t happened.', 'A promise doesn’t tell anyone what to do when you miss it.',38)),
        turn('At 05:40 your car won’t start. The driver asks whether to wait. What do you say?',
            answer('Give me twenty minutes. I’m sure I can get it started.', 'The driver needed a decision by six, not a guess at six.',31),
            answer('Use the agreed cover now. I’ll update you at six with my arrival time.', 'That keeps the shift moving and tells me when to expect you.'),
            answer('I may be late. Ask around and see if anyone’s there.', 'That passes on the problem without handing over the decision.',18)),
        turn('Your cover hasn’t seen the changed order. What do you hand over?',
            answer('The changed order, the one open question, and when I’ll check back.', 'Enough to act, with the uncertainty left visible.'),
            answer('The whole inbox. I don’t want to leave anything out.', 'The urgent decision can disappear in a whole inbox.',19),
            answer('Tell them to do what I would have done.', 'They don’t know what you checked.',37)),
        turn('You gave me your word. Now you know you can’t keep it. Tell me what I can count on instead.',
            answer('I’ll make it up by taking every shift next week.', 'That sounds like another promise made under pressure.',36),
            answer('I’ll call now, give you the decision that needs cover, and check back at six.', 'That’s something I can count on.'),
            answer('I’ll be there as fast as I can and explain when I arrive.', 'The driver will have made the decision by then.',21))),
)


def selftest():
    from itertools import product
    outcomes=[]
    for choices in product(range(3),repeat=6):
        damage=0
        for section_index,row in enumerate(SECTIONS):
            opening,follow=choices[2*section_index:2*section_index+2]
            damage+=row['choices'][opening]['cost']+row['followups'][opening]['choices'][follow]['cost']
        outcomes.append(damage<STARTING_COMPOSURE)
    assert 0 < sum(outcomes) < len(outcomes)*.25, sum(outcomes)


if __name__=='__main__':
    selftest()
