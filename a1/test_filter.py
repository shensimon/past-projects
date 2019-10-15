""" Tests for the CustomerFilter, DurationFilter, and LocationFilter filters
in A1.
"""

import pytest
from hypothesis import settings, given, example, strategies as st
from filter import CustomerFilter, DurationFilter, LocationFilter
from data import tiny_data
from application import import_data, create_customers, process_event_history, \
    find_customer_by_number

LOG = import_data()  # gets data from dataset.json
CUSTOMERS = create_customers(LOG)  # creates customers based on the data in LOG
process_event_history(LOG, CUSTOMERS)  # gives customers their event history
CALL_LIST = []  # list of calls
for c in CUSTOMERS:
    hist = c.get_history()
    CALL_LIST.extend(hist[0])


@given(s=st.text(alphabet=st.characters(min_codepoint=0x0000,
                                        max_codepoint=0x02AF),
                 max_size=100))
def test_absolute_garbage(s: str) -> None:
    """ Test that none of the filters raise errors when absolute garbage input
    strings are passed in.
    """
    print(s)
    cf = CustomerFilter()
    df = DurationFilter()
    lf = LocationFilter()
    # test that nothing crashes
    cf.apply(CUSTOMERS, CALL_LIST, s)
    df.apply(CUSTOMERS, CALL_LIST, s)
    lf.apply(CUSTOMERS, CALL_LIST, s)


@given(id=st.integers(min_value=0, max_value=9999))
def test_customer_filter(id: int):
    """ Test that CustomerFilter works in the general case - with (more or less)
    valid inputs, aka 4 digit numerical customer IDs. Customer IDs may not
    belong to any customer.
    """
    filt = CustomerFilter()
    results = filt.apply(CUSTOMERS, CALL_LIST, str(id))
    cust = None
    for c in CUSTOMERS:
        if c.get_id() == id:
            cust = c
            break
    if cust is None:
        # if no customer has the ID, the original dataset should be returned
        assert results == CALL_LIST
    else:
        # if a customer has the ID, every call in the results of the filter
        # should involve the customer as either the source or destination
        for c in results:
            assert c.src_number in cust or c.dst_number in cust


@given(s=st.sampled_from(['L', 'G']),
       t=st.integers(min_value=0, max_value=9999))
def test_duration_filter(s: str, t: int):
    """ Test that DurationFilter works in the general case - with valid inputs,
    aka either 'L' or 'G' followed by the limit time (in seconds).
    """
    filt = DurationFilter()
    results = filt.apply(CUSTOMERS, CALL_LIST, s + str(t))
    for call in results:
        if s == 'L':
            assert call.duration < t
        else:
            assert call.duration > t


@given(x1=st.floats(min_value=-79.697878, max_value=-79.196382),
       y1=st.floats(min_value=43.576959, max_value=43.799568),
       x2=st.floats(min_value=-79.697878, max_value=-79.196382),
       y2=st.floats(min_value=43.576959, max_value=43.799568))
def test_location_filter(x1: float, y1: float, x2: float, y2: float):
    """ Test that LocationFilter works in the general case - with valid inputs,
    aka coordinates within the range of the map.
    """
    filt = LocationFilter()
    results = filt.apply(CUSTOMERS, CALL_LIST, f'{x1}, {y1}, {x2}, {y2}')
    if x1 > x2 or y1 > y2:
        assert results == CALL_LIST
    else:
        for call in results:
            src_in_range = x1 <= call.src_loc[0] <= x2 \
                           and y1 <= call.src_loc[1] <= y2
            dst_in_range = x1 <= call.dst_loc[0] <= x2 \
                           and y1 <= call.dst_loc[1] <= y2
            assert src_in_range or dst_in_range


if __name__ == '__main__':
    pytest.main(['-v', '-s', 'test_filter.py'])
