from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase


class NextEventLiquidityTestCase(LineAggregatorBaseTestCase):
    def test_that_next_event_liquidity_amount_calculated_properly(self):

        # creating default event:
        self.add_line(max_active_events=10)

        # providing liquidity:
        self.deposit_liquidity(self.a, amount=80_000_000)
        self.approve_liquidity(self.a, entry_position_id=0)
        self.assertEqual(self.storage['nextEventLiquidity'], 8_000_000)

        # second provider adds some liquidity with 20% shares:
        self.deposit_liquidity(self.b, amount=20_000_000)
        self.approve_liquidity(self.a, entry_position_id=1)
        self.assertEqual(self.storage['nextEventLiquidity'], 10_000_000)

        # creating one event:
        self.create_event(event_line_id=0, next_event_id=0)
        self.wait(3600)

        # A decided to remove liquidity and then redeposit it back:
        withdrawn_amount = self.claim_liquidity(
            self.a, position_id=0, shares=80_000_000)
        self.assertEqual(self.storage['nextEventLiquidity'], 2_000_000)

        # Run and finish event with profit 2xtz:
        self.create_event(event_line_id=0, next_event_id=1)
        self.wait(3600)
        self.pay_reward(event_id=1, amount=4_000_000)
        self.assertEqual(self.storage['nextEventLiquidity'], 2_200_000)

        # Run and finish event with loss 1xtz:
        self.create_event(event_line_id=0, next_event_id=2)
        self.wait(3600)
        self.pay_reward(event_id=2, amount=1_200_000)
        self.assertEqual(self.storage['nextEventLiquidity'], 2_100_000)

