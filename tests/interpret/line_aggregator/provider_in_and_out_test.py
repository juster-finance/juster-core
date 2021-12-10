from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase


class ProviderInAndOutTestCase(LineAggregatorBaseTestCase):
    def test_provider_should_have_the_same_shares_if_decided_to_reenter(self):

        # creating default event:
        self.add_line(max_active_events=10)

        # providing liquidity:
        provided_amount = 80_000_000
        self.deposit_liquidity(self.a, amount=provided_amount)

        # creating 9 events:
        for next_event_id in range(9):
            self.create_event(event_line_id=0, next_event_id=next_event_id)
            self.wait(3600)

        # second provider adds some liquidity with 20% shares:
        self.deposit_liquidity(self.b, amount=20_000_000)

        # creating 10th event: 8xtz + 2xtz should be provided:
        self.create_event(event_line_id=0, next_event_id=9)

        # A decided to remove liquidity and then redeposit it back:
        withdrawn_amount = self.claim_liquidity(
            self.a, position_id=0, shares=80_000_000)
        self.assertEqual(withdrawn_amount, 0)

        self.deposit_liquidity(self.a, amount=provided_amount)

        # should receive the same amount of shares:
        self.assertEqual(self.storage['positions'][2]['shares'], provided_amount)
        self.assertEqual(self.storage['totalShares'], 100_000_000)
        self.assertEqual(self.storage['nextEventLiquidity'], 10_000_000)

