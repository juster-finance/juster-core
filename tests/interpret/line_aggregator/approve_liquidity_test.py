from pytezos import MichelsonRuntimeError
from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase


class ApproveLiquidityTestCase(LineAggregatorBaseTestCase):
    def test_should_fail_when_try_to_approve_liquidity_twice(self):

        # creating default event:
        self.add_line()

        # providing liquidity:
        self.deposit_liquidity()
        self.approve_liquidity(entry_position_id=0)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_liquidity(entry_position_id=0)
        msg = 'Entry position is not found'
        self.assertTrue(msg in str(cm.exception))


    def test_should_fail_if_trying_to_approve_unexisted_entry_position(self):

        # creating default event:
        self.add_line()

        # providing liquidity:
        self.deposit_liquidity()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_liquidity(entry_position_id=12)
        msg = 'Entry position is not found'
        self.assertTrue(msg in str(cm.exception))


    def test_should_not_be_possible_to_approve_entry_position_before_time(self):

        # different contract storage that includes lag for liquidity added:
        self.storage['entryLockPeriod'] = 3600

        # creating default event:
        self.add_line()

        # providing liquidity:
        self.deposit_liquidity()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_liquidity(entry_position_id=0)
        msg = 'Cannot approve liquidity before acceptAfter'
        self.assertTrue(msg in str(cm.exception))

        # waiting 1 second less that needed, still should not be able to approve:
        self.wait(3599)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_liquidity(entry_position_id=0)
        msg = 'Cannot approve liquidity before acceptAfter'
        self.assertTrue(msg in str(cm.exception))

        # waiting 1 second more and succeed to approve:
        self.wait(1)
        self.approve_liquidity(entry_position_id=0)
