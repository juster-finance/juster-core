from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class ClaimPayoutIssueTest(PoolBaseTestCase):
    def test_should_not_overestimate_provided_liquidity_when_line_added(self):
        self.add_line(max_events=2)
        entry_id = self.deposit_liquidity(amount=1_000_000)
        position_id = self.approve_liquidity(entry_id=entry_id)

        # first events starts and 50% liquidity goes into it:
        first_event = self.create_event()
        self.wait(3600)

        self.add_line(max_events=1)

        # second event starts and 33% of liquidity goes into:
        second_event = self.create_event()
        self.wait(3600)

        # third event starts and event.shares should be less than 33%
        # to prevent overestimate:
        third_event = self.create_event()
        self.wait(3600)

        # provider succesfully claims all liquidity:
        self.claim_liquidity(shares=1_000_000, position_id=position_id)
