"""Job offer, order and C.V. copy shared by the runtime builder and proof."""

from typing import NamedTuple


class Pitch(NamedTuple):
    question: str
    options: tuple[str, str, str]
    points: tuple[int, int, int]
    replies: tuple[str, str, str]


class Order(NamedTuple):
    request: str
    cases: tuple[str, str, str]
    correct: int


class Job(NamedTuple):
    employer: str
    role: str
    address: str
    pitch: tuple[Pitch, Pitch]
    orders: tuple[Order, ...]
    seconds: int
    evidence: str


JOBS = (
    Job('Queen Market', 'Receiving clerk', 'Queen Street', (
        Pitch('The night truck is late. A case turns up with the wrong label. What do you do?', (
            'Put it with the closest match and keep the line moving.',
            'Set it aside. Check the manifest before it goes out.',
            'Ask who normally checks deliveries, then keep the rest moving.',
        ), (0, 2, 1), ('Then a wrong case leaves my dock.', 'Good. Keep the mistake here.', 'I can work with that.')),
        Pitch('The dock opens at six. What can you promise me tomorrow?', (
            'I’ll be there at six. If the car gives me trouble, I’ll call before then.',
            'I can start early. I’ll check the route tonight.',
            'Any time you like. I never run late.',
        ), (2, 1, 0), ('That gives me a plan I can work with.', 'Check it before you turn in.', 'I asked for a time I can count on.')),
    ), (
        Order('Pack 2 rice and 1 tea in a crate that holds 3. Which crate can leave?', ('1 rice and 2 tea', '3 rice', '2 rice and 1 tea'), 2),
        Order('The truck holds 4 cases. Tea gets priority. Which load can leave?', ('3 tea and 1 rice', '4 rice', '3 tea and 2 rice'), 0),
        Order('Pack 2 oat milk and 2 rice. One of the rice cases is split open.', ('Send all four', 'Replace the split rice case', 'Fill the gap with tea'), 1),
        Order('Load 5 cases into two crates. Each crate holds 3 at most.', ('1 in the first, 4 in the second', '3 in the first, 2 in the second', '4 in the first, 1 in the second'), 1),
    ), 34, 'Packed four stock orders from a manifest.'),
    Job('Night Dispatch', 'Dispatch assistant', 'South connector', (
        Pitch('Two orders share a destination. One leaves tonight. How will you keep them apart?', (
            'Mark the deadline on each order and check it at dispatch.',
            'Keep the first one I saw on top.',
            'Ask the driver which one they were expecting.',
        ), (2, 0, 1), ('That keeps the decision with the paperwork.', 'The stack gets moved all night.', 'Ask, then check the label.')),
        Pitch('A driver is waiting and the manifest is incomplete. What do you tell them?', (
            'Tell them we’ll send it now and check it tomorrow.',
            'Say which case needs checking and give them a time for an update.',
            'Tell them there’s a delay and get the supervisor.',
        ), (0, 2, 1), ('The driver inherits the mistake.', 'That gives them something to plan around.', 'That works if you stay with it.')),
    ), (
        Order('One driver is free. Bay 03 closes in 2 minutes and is a minute away. What goes first?', ('Bay 03 before it closes', 'Bay 08, due in 5 minutes', 'Bay 12, due in 8 minutes'), 0),
        Order('The bridge to bay 08 is blocked. The parcel is due in 6 minutes.', ('Wait 8 minutes for the bridge', 'Send it to bay 03', 'Take the 4-minute service road to bay 08'), 2),
        Order('One parcel still needs a label. Both vans leave in a minute.', ('Load the unlabelled parcel first', 'Send the verified parcel and hold the other', 'Hold both vans'), 1),
        Order('A chilled parcel expires in 4 minutes. The driver can take one parcel now.', ('Chilled parcel to bay 12 in 2 minutes', 'Standard parcel to bay 03 in 2 minutes', 'Chilled parcel to bay 12 in 6 minutes'), 0),
    ), 32, 'Matched four dispatch orders to their bays.'),
    Job('Northline Supply', 'Inventory assistant', 'Northline Avenue', (
        Pitch('A rush order empties your shelf. The count on the screen still says three. What now?', (
            'Tell the next shift to check it if they get time.',
            'Ask who pulled the rush order, then check the shelf.',
            'Count what’s there and record the difference before promising more.',
        ), (0, 1, 2), ('They’ll start the day with a bad count.', 'Good start. Leave a record.', 'That gives us a number we can trust.')),
        Pitch('The replacement parts look almost the same. How will you avoid sending the wrong ones?', (
            'Check the part code and quantity against the request at packing.',
            'Keep the two cases apart while I work.',
            'Match the case by its colour.',
        ), (2, 1, 0), ('Both checks belong at the bench.', 'Separation helps. Read the code as well.', 'The supplier changes the boxes.')),
    ), (
        Order('The ledger says 8 seals. You count 5. No orders are outstanding.', ('Add 3 to stock', 'Subtract 3 from stock', 'Leave the count at 8'), 1),
        Order('The ledger says 4 caps. You count 7, but 2 are already reserved.', ('Record 7 available', 'Record 4 available', 'Record 5 available'), 2),
        Order('The shelf holds 6 filters. A return adds 3, but 1 is damaged.', ('Record 8 usable filters', 'Record 9 usable filters', 'Record 7 usable filters'), 0),
        Order('The system shows 10 seals. You find 7 loose and 3 in a sealed kit.', ('Subtract the 3 from all records', 'Record 7 loose and 3 reserved in the kit', 'Record all 10 as loose'), 1),
    ), 30, 'Checked four parts orders by code and quantity.'),
)


PITCH, TIME_SKIP, SHIFT, RESULT = 4, 5, 6, 7
HIRE_SCORE, MAX_MISSES, CV_PER_JOB, BOSS_MINIMUM = 3, 2, 30, 60


def selftest():
    for job in JOBS:
        assert sum(max(p.points) for p in job.pitch) >= HIRE_SCORE
        assert sum(min(p.points) for p in job.pitch) < HIRE_SCORE
        assert len(job.orders) == 4 and len({o.correct for o in job.orders}) == 3
        assert all(0 <= o.correct < len(o.cases) == len(set(o.cases)) == 3 for o in job.orders)
    assert CV_PER_JOB < BOSS_MINIMUM <= CV_PER_JOB * 2


if __name__ == '__main__':
    selftest()
    print('Three jobs checked for reachable hires, order choices and interview eligibility')
