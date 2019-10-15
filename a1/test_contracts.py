""" Unit tests for the TermContract, MTMContract, and PrepaidContract classes
in A1.
"""

import unittest
import datetime
from bill import Bill
from hypothesis import settings, given, example, strategies as st
from call import Call
from contract import TermContract, MTMContract, PrepaidContract
from math import ceil

MTM_MONTHLY_FEE = 50.00
TERM_MONTHLY_FEE = 20.00
TERM_DEPOSIT = 300.00
TERM_MINS = 100
MTM_MINS_COST = 0.05
TERM_MINS_COST = 0.1
PREPAID_MINS_COST = 0.025


class TestTermContract(unittest.TestCase):
    """ Unit tests for the TermContract class in A1.
    """

    @given(start=st.dates(), end=st.dates())  # generate random dates
    def test_init(self, start, end):
        """ Test if a TermContract can be initialized properly with random
        start/end dates.
        """
        tc = TermContract(start, end)
        assert tc.start is start
        assert tc.end is end

    def test_new_month_not_first_month(self):
        """ Test that the new_month function works in general, aka test that it
        sets up the bill and rate correctly, and that it bills the right monthly
        fee.
        """
        tc = TermContract(datetime.date(2000, 9, 29),
                          datetime.date(2007, 9, 29))
        bill = Bill()
        tc.new_month(month=10, year=2000, bill=bill)
        assert tc.bill is bill
        # check that the rate per minute is appropriate for the class
        self.assertEqual(tc.bill.min_rate, TERM_MINS_COST)
        # check that the monthly fee has been billed
        self.assertEqual(tc.bill.fixed_cost, TERM_MONTHLY_FEE)
        # check that nothing else has been billed, since no calls were made
        self.assertAlmostEqual(tc.bill.fixed_cost, tc.bill.get_cost())

    def test_new_month_first_month(self):
        """ Test that the new_month function works as expected, and also that it
        bills the term deposit on the first month of the term.
        """
        tc = TermContract(datetime.date(2000, 9, 29),
                          datetime.date(2007, 9, 29))
        bill = Bill()
        tc.new_month(month=9, year=2000, bill=bill)
        assert tc.bill is bill
        # check that the rate per minute is appropriate for the class
        self.assertEqual(tc.bill.min_rate, TERM_MINS_COST)
        # check that the deposit and monthly fee have been billed
        self.assertAlmostEqual(tc.bill.fixed_cost,
                               TERM_MONTHLY_FEE + TERM_DEPOSIT)
        # check that nothing else has been billed, since no calls were made
        self.assertAlmostEqual(tc.bill.fixed_cost, tc.bill.get_cost())

    # generate random durations for the calls
    @given(t1=st.integers(min_value=0, max_value=TERM_MINS / 2 * 60),
           t2=st.integers(min_value=0, max_value=TERM_MINS / 2 * 60))
    # edge cases
    @example(t1=0, t2=0)
    @example(t1=TERM_MINS / 2 * 60, t2=TERM_MINS / 2 * 60)
    @example(t1=TERM_MINS * 60, t2=0 * 60)
    @example(t1=0, t2=TERM_MINS * 60)
    def test_bill_call_free(self, t1: int, t2: int):
        """ Test that calls are billed as free as long as there are enough free
        minutes remaining.

        (The examples test the case the calls use all the free minutes.)
        """
        tc = TermContract(datetime.date(2000, 9, 29),
                          datetime.date(2007, 9, 29))
        bill = Bill()
        tc.new_month(month=10, year=2007, bill=bill)
        c1 = Call(src_nr="123-4567", dst_nr="987-6543",
                  calltime=datetime.datetime(year=2007, month=10, day=31,
                                             hour=20, minute=30, second=0),
                  duration=t1,
                  src_loc=(-79.45188229255568, 43.62186408875219),
                  dst_loc=(-79.36866519485261, 43.680793196449336))
        c2 = Call(src_nr="123-4567", dst_nr="987-6543",
                  calltime=datetime.datetime(year=2007, month=10, day=31,
                                             hour=21, minute=30, second=0),
                  duration=t2,
                  src_loc=(-79.45188229255568, 43.62186408875219),
                  dst_loc=(-79.36866519485261, 43.680793196449336))
        tc.bill_call(c1)
        tc.bill_call(c2)
        # the calls should be free, so the only cost billed should be the
        # monthly fee
        self.assertEqual(tc.bill.get_cost() - TERM_MONTHLY_FEE, 0, (t1, t2))

    @given(t1=st.integers(min_value=0,
                          max_value=100000000))  # generate random durations
    def test_bill_call_not_free(self, t1):
        """ Test that a call is billed correctly if there are no free minutes
        remaining for the month.
        """
        t1_mins = ceil(t1 / 60)
        tc = TermContract(datetime.date(2000, 9, 29),
                          datetime.date(2007, 9, 29))
        bill = Bill()
        tc.new_month(month=10, year=2007, bill=bill)
        # max out free mins so that a new call must be billed
        tc.bill.add_free_minutes(TERM_MINS)
        c1 = Call(src_nr="123-4567", dst_nr="987-6543",
                  calltime=datetime.datetime(year=2007, month=10, day=31,
                                             hour=20, minute=30, second=0),
                  duration=t1,
                  src_loc=(-79.45188229255568, 43.62186408875219),
                  dst_loc=(-79.36866519485261, 43.680793196449336))
        tc.bill_call(c1)
        # check that the entire call has been billed
        self.assertAlmostEqual(tc.bill.get_cost() - TERM_MONTHLY_FEE,
                               t1_mins * TERM_MINS_COST)

    @given(t1=st.integers(min_value=TERM_MINS * 60,
                          max_value=10000000))  # generate durations
    def test_bill_call_partially_free(self, t1):
        """ Test that a call is billed correctly even if it is longer than the
        number of free minutes remaining for the month.

        E.g. if 10 free minutes are remaining for the month and a call lasts 11
        minutes, then 10 minutes should be counted as free and 1 minute should
        be billed normally.
        """
        t1_mins = ceil(t1 / 60)
        tc = TermContract(datetime.date(2000, 9, 29),
                          datetime.date(2007, 9, 29))
        tc.new_month(10, 2007, Bill())
        # make a call whose duration is longer than the number of free mins left
        c1 = Call(src_nr="123-4567", dst_nr="987-6543",
                  calltime=datetime.datetime(year=2007, month=10, day=31,
                                             hour=20, minute=30, second=0),
                  duration=t1,
                  src_loc=(-79.45188229255568, 43.62186408875219),
                  dst_loc=(-79.36866519485261, 43.680793196449336))
        tc.bill_call(c1)
        # check that free mins have been maxed out
        self.assertEqual(tc.bill.free_min, TERM_MINS)
        # check that the rest of the call has been billed
        self.assertEqual(tc.bill.billed_min, t1_mins - TERM_MINS)

    def test_cancel_contract_before_end(self):
        """ Test that if a contract is cancelled before its end date, the
        deposit is forfeited.
        """
        tc = TermContract(datetime.date(2000, 9, 29),
                          datetime.date(2007, 9, 29))
        # go to last month of contract (contract not over, but almost!)
        tc.new_month(month=9, year=2007, bill=Bill())
        cancel = tc.cancel_contract()
        # check that the deposit has been forfeited
        self.assertAlmostEqual(cancel, TERM_MONTHLY_FEE)

    def test_cancel_contract_after_end(self):
        """ Test that if a contract is cancelled after its end date, the
        deposit is returned.
        """
        tc = TermContract(datetime.date(2000, 9, 29),
                          datetime.date(2007, 9, 29))
        # go to first month after contract
        tc.new_month(month=10, year=2007, bill=Bill())
        cancel = tc.cancel_contract()
        # check that the deposit has been returned
        self.assertAlmostEqual(cancel, TERM_MONTHLY_FEE - TERM_DEPOSIT)


class TestMTMContract(unittest.TestCase):
    """ Unit tests for the MTMContract class in A1.
    """
    def test_new_month(self):
        """Test that the new_month function works in general, aka test that it
        sets up the bill and rate correctly, and that it bills the right monthly
        fee.
        """
        mc = MTMContract(datetime.date(2000, 9, 29))
        bill = Bill()
        mc.new_month(month=10, year=2000, bill=bill)
        assert mc.bill is bill
        # check that the rate per minute is appropriate for the class
        self.assertEqual(mc.bill.min_rate, MTM_MINS_COST)
        # check that the monthly fee have been billed
        self.assertEqual(mc.bill.fixed_cost, MTM_MONTHLY_FEE)


class TestPrepaidContract(unittest.TestCase):
    """ Unit tests for the PrepaidContract class in A1.
    """
    def test_new_month_no_top_off(self):
        """ Test that the new_month function works in general, aka test that it
        sets up the bill and rate correctly, and that it sets up and bills the
        balance correctly. Test that the balance is NOT topped off if there is
        >=$10 of credit.
        """
        pc = PrepaidContract(datetime.date(2000, 9, 29), 100)
        bill1 = Bill()
        pc.new_month(month=10, year=2000, bill=bill1)
        assert pc.bill is bill1
        # the balance should not have changed
        self.assertAlmostEqual(pc.balance, -100)
        # the bill cost should be the balance
        self.assertAlmostEqual(pc.bill.get_cost(), pc.balance)
        bill2 = Bill()
        pc.new_month(month=11, year=2000, bill=bill2)
        assert pc.bill is bill2
        # the balance still should not have changed
        self.assertAlmostEqual(pc.balance, -100)
        self.assertAlmostEqual(pc.bill.get_cost(), pc.balance)

    def test_new_month_top_off(self):
        """ Test that the new_month function works in general, aka test that it
        sets up the bill and rate correctly, and that it sets up and bills the
        balance correctly. Test that the balance is topped off if there is
        <$10 of credit, and not unnecessarily topped off after that.
        """
        pc = PrepaidContract(datetime.date(2000, 9, 29), 0)
        bill1 = Bill()
        pc.new_month(month=10, year=2000, bill=bill1)
        assert pc.bill is bill1
        self.assertEqual(pc.bill.min_rate, PREPAID_MINS_COST)
        # the balance should have decreased by $25 because of the top off
        self.assertEqual(pc.balance, -25)
        # the customer should not be billed for the top off, their bill should
        # simply reflect the new balance
        self.assertAlmostEqual(pc.bill.get_cost(), pc.balance)
        bill2 = Bill()
        pc.new_month(month=11, year=2000, bill=bill2)
        assert pc.bill is bill2
        self.assertEqual(pc.bill.min_rate, PREPAID_MINS_COST)
        # the balance should not have changed
        self.assertEqual(pc.balance, -25)
        self.assertAlmostEqual(pc.bill.get_cost(), pc.balance)

    def test_cancel_contract_negative_balance(self):
        """ Test that $0 is charged as the cancellation fee if the contract is
        cancelled while the balance is negative (aka some credit exists).
        """
        pc = PrepaidContract(datetime.date(2000, 9, 29), 25)
        pc.new_month(month=10, year=2000, bill=Bill())
        self.assertAlmostEqual(pc.balance, -25)
        cancel = pc.cancel_contract()
        # since the balance is negative, it should be forfeited, so the cost for
        # the month should be $0
        self.assertAlmostEqual(cancel, 0)

    def test_cancel_contract_positive_balance(self):
        """ Test that the balance is charged as the cancellation fee if the
        contract is cancelled while the balance is positive.
        """
        pc = PrepaidContract(datetime.date(2000, 9, 29), 10)
        pc.new_month(month=10, year=2000, bill=Bill())
        # make a call that costs $15
        c1 = Call(src_nr="123-4567", dst_nr="987-6543",
                  calltime=datetime.datetime(year=2000, month=10, day=31,
                                             hour=20, minute=30, second=0),
                  duration=ceil(15 / PREPAID_MINS_COST * 60),
                  src_loc=(-79.45188229255568, 43.62186408875219),
                  dst_loc=(-79.36866519485261, 43.680793196449336))
        pc.bill_call(c1)
        # since the call was very long, the balance should be positive now
        self.assertAlmostEqual(pc.balance, 5)
        cancel = pc.cancel_contract()
        # since the balance is positive, it should be billed, so the cost for
        # the month should be the balance
        self.assertAlmostEqual(cancel, pc.balance)


if __name__ == '__main__':
    unittest.main(exit=False)
