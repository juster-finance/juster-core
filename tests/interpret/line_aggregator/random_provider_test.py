from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase
from random import randint


class RandomProviderTestCase(LineAggregatorBaseTestCase):
    def test_provider_should_get_calculated_reward_in_multiple_events(self):

        ITERATIONS = 5

        for _ in range(ITERATIONS):
            self.drop_changes()
            STEPS = 10
            ENTER_STEP = randint(0, STEPS-1)
            EXIT_STEP = randint(ENTER_STEP, STEPS-1)
            PROFIT_LOSS = randint(-10, 10) * 300_000

            self.add_line(max_active_events=3)

            # A is core provider:
            shares = 30_000_000
            total_liquidity = 30_000_000
            self.deposit_liquidity(self.a, amount=total_liquidity)
            self.approve_liquidity(self.a, entry_position_id=0)

            for step in range(STEPS):

                if step == ENTER_STEP:
                    self.deposit_liquidity(self.b, amount=total_liquidity)
                    self.approve_liquidity(self.b, entry_position_id=1)

                created_id = self.create_event()
                self.wait(3600)
                self.pay_reward(
                    event_id=created_id,
                    amount=self.storage['nextEventLiquidity'] + PROFIT_LOSS
                )
                total_liquidity += PROFIT_LOSS

                if step == EXIT_STEP:
                    self.claim_liquidity(self.b, position_id=1, shares=shares)

            provider_profit_loss = (EXIT_STEP - ENTER_STEP + 1) * PROFIT_LOSS / 2
            self.assertEqual(self.balances[self.b], provider_profit_loss)

