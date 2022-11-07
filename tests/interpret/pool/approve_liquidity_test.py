from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class ApproveEntryTestCase(PoolBaseTestCase):
    def test_should_fail_when_try_to_approve_entry_twice(self):

        # creating default event:
        self.add_line()

        # providing liquidity:
        self.deposit_liquidity()
        self.approve_entry(entry_id=0)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_entry(entry_id=0)
        msg = 'Entry is not found'
        self.assertTrue(msg in str(cm.exception))

    def test_should_fail_if_trying_to_approve_unexisted_entry_position(self):

        # creating default event:
        self.add_line()

        # providing liquidity:
        self.deposit_liquidity()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_entry(entry_id=12)
        msg = 'Entry is not found'
        self.assertTrue(msg in str(cm.exception))

    def test_should_not_be_possible_to_approve_entry_position_before_time(
        self,
    ):

        # different contract storage that includes lag for liquidity added:
        self.storage['entryLockPeriod'] = 3600

        # creating default event:
        self.add_line()

        # providing liquidity:
        self.deposit_liquidity()

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_entry(entry_id=0)
        msg = 'Cannot approve liquidity before acceptAfter'
        self.assertTrue(msg in str(cm.exception))

        # waiting 1 second less that needed, still should not be able to approve:
        self.wait(3599)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_entry(entry_id=0)
        msg = 'Cannot approve liquidity before acceptAfter'
        self.assertTrue(msg in str(cm.exception))

        # waiting 1 second more and succeed to approve:
        self.wait(1)
        self.approve_entry(entry_id=0)

    def test_that_anyone_can_approve_others_liquidity(self):
        # creating default event:
        self.add_line()

        # providing liquidity with A:
        self.deposit_liquidity(sender=self.a)

        # approving with B:
        self.approve_entry(sender=self.b, entry_id=0)

    def test_should_fail_if_approved_liquidity_amount_more_than_entry_liquidity(
        self,
    ):
        # NOTE: this scenario should not happen under normal conditions
        # but there are wrong state check in approve_entry entrypoint

        # creating default event:
        self.add_line()

        # providing liquidity with A:
        self.deposit_liquidity(sender=self.a, amount=2_000_000)

        # modifying contract state:
        self.storage['entryLiquidityF'] = 1_000_000

        # approving:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_entry(entry_id=0)
        msg = 'Wrong state'
        self.assertTrue(msg in str(cm.exception))

    def test_should_not_include_withdrawable_liquidity_in_share_calculation(
        self,
    ):
        # scenario with running event where provider decides to go out:
        self.add_line()
        self.deposit_liquidity(sender=self.a, amount=1_000)
        self.approve_entry(entry_id=0)
        self.create_event()
        self.claim_liquidity(sender=self.a, shares=500)
        self.wait(3600)
        self.pay_reward(event_id=0, amount=500)

        # another provider adds 500 mutez and should receive 500 shares:
        self.deposit_liquidity(sender=self.b, amount=500)
        provider = self.approve_entry(entry_id=1)
        received_shares = self.storage['shares'][provider]
        self.assertEqual(received_shares, 500)

    def test_should_disallow_approving_zero_shares(self):
        self.add_line(max_events=1)
        entry_one_id = self.deposit_liquidity(sender=self.a, amount=1000)
        self.approve_entry(entry_id=entry_one_id)

        # decreasing liquidity by 1 mutez to make share price 1001/1000
        event_id = self.create_event()
        self.pay_reward(event_id=0, amount=1001)

        # trying to deposit 1 mutez fail, because floor(0.999) = 0 shares added:
        entry_two_id = self.deposit_liquidity(sender=self.b, amount=1)
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.approve_entry(entry_id=entry_two_id)
        msg = 'Approve 0 shares dissalowed'
        self.assertTrue(msg in str(cm.exception))

        # trying to deposit 2 mutez succeed and adds 1 share:
        entry_three_id = self.deposit_liquidity(sender=self.b, amount=2)
        self.approve_entry(entry_id=entry_three_id)
        assert self.storage['shares'][self.b] == 1
