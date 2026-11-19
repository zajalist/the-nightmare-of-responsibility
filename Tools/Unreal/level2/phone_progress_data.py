"""Level 2 phone copy and shared progress display rules. No engine dependencies."""
from journey_data import STOPS

PHONE_PHASES = (1, 2, 4, 5, 7, 8, 11)
GOAL = 'Find a job'
MOM = 'Did you go out?'
PHONE_REVISIONS=(
    'Interior management: 5 years',
    'Warehouse and office: 3 years',
    'Available now. Reliable.',
)
MESSAGES = (
    ('Mom', MOM),
    ('Career Center', 'Drop in any weekday, 9 to 4. No appointment needed.'),
    ('Draft', 'I went out.'),
)


def can_open_phone(phase, stop_busy=False, phone_session=False, dialogue_mode=0):
    return phase in PHONE_PHASES and not stop_busy and not phone_session and dialogue_mode==0


def phone_lines(edited):
    return [PHONE_REVISIONS[i] if done else row['truth'] for i,(row,done) in enumerate(zip(STOPS,edited))]


def progress(value):
    value = min(100, max(0, int(value)))
    return value, value / 100.


def show_progress(phase):
    return phase in (2, 3, 4, 5, 6, 7, 8, 11)
