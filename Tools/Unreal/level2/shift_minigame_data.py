"""Shift rules shared by the native graph author and the playtest driver."""

PERIOD, WINDOW_START, WINDOW_END = 2.6, .42, .72
RECIPES = ((2, 1, 0), (0, 1, 2), (1, 1, 1), (1, 0, 2))
BAYS = (0, 2, 1, 0)
LEDGER = ((5, 7), (8, 5), (6, 8), (9, 7))
PACKED = ('PackedRice', 'PackedTea', 'PackedOat')
TITLES = ('Pack the crate', 'Dispatch the parcel', 'Balance the ledger')


if __name__ == '__main__':
    assert len(RECIPES) == len(BAYS) == len(LEDGER) == 4
    assert all(sum(recipe) == 3 and all(0 <= count <= 2 for count in recipe) for recipe in RECIPES)
    assert set(BAYS) == {0, 1, 2} and 0 < WINDOW_START < WINDOW_END < 1
    assert all(0 <= start <= 20 and 0 <= end <= 20 and 2 <= abs(start-end) <= 3 for start, end in LEDGER)
