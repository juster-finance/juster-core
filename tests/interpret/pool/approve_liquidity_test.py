from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class ApproveLiquidityTestCase(PoolBaseTestCase):
    def test_should_fail_when_try_to_approve_liquidity_twice(self):

        # creating default event:
        self.add_line()

        # providing liquidity:
        self.deposit_liquidity()
        self.approve_liquidity(entry_id=0)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_liquidity(entry_id=0)
        msg = 'Entry is not found'
        self.assertTrue(msg in str(cm.exception))


    def test_should_fail_if_trying_to_approve_unexisted_entry_position(self):

        # creating default event:
        self.add_line()

        # providing liquidity:
        self.deposit_liquidity()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_liquidity(entry_id=12)
        msg = 'Entry is not found'
        self.assertTrue(msg in str(cm.exception))


    def test_should_not_be_possible_to_approve_entry_position_before_time(self):

        # different contract storage that includes lag for liquidity added:
        self.storage['entryLockPeriod'] = 3600

        # creating default event:
        self.add_line()

        # providing liquidity:
        self.deposit_liquidity()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_liquidity(entry_id=0)
        msg = 'Cannot approve liquidity before acceptAfter'
        self.assertTrue(msg in str(cm.exception))

        # waiting 1 second less that needed, still should not be able to approve:
        self.wait(3599)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_liquidity(entry_id=0)
        msg = 'Cannot approve liquidity before acceptAfter'
        self.assertTrue(msg in str(cm.exception))

        # waiting 1 second more and succeed to approve:
        self.wait(1)
        self.approve_liquidity(entry_id=0)


    def test_that_anyone_can_approve_others_liquidity(self):
        # creating default event:
        self.add_line()

        # providing liquidity with A:
        self.deposit_liquidity(sender=self.a)

        # approving with B:
        self.approve_liquidity(sender=self.b, entry_id=0)


    def test_should_fail_if_approved_liquidity_amount_more_than_entry_liquidity(self):
        # NOTE: this scenario should not happen under normal conditions
        # but there are wrong state check in approve_liquidity entrypoint

        # creating default event:
        self.add_line()

        # providing liquidity with A:
        self.deposit_liquidity(sender=self.a, amount=2_000_000)

        # modifying contract state:
        self.storage['entryLiquidityF'] = 1_000_000

        # approving:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_liquidity(entry_id=0)
        msg = 'Wrong state'
        self.assertTrue(msg in str(cm.exception))


    def test_should_not_include_withdrawable_liquidity_in_share_calculation(self):
        # scenario with running event where provider decides to go out:
        self.add_line()
        self.deposit_liquidity(sender=self.a, amount=1_000)
        self.approve_liquidity(entry_id=0)
        self.create_event()
        self.claim_liquidity(sender=self.a, shares=500)
        self.wait(3600)
        self.pay_reward(event_id=0, amount=500)

        # another provider adds 500 mutez and should receive 500 shares:
        self.deposit_liquidity(sender=self.b, amount=500)
        self.approve_liquidity(entry_id=1)
        received_shares = self.storage['positions'][1]['shares']
        self.assertEqual(received_shares, 500)

