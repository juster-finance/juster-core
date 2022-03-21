from tests.interpret.pool.pool_base import PoolBaseTestCase


class LiquidityUnitsTestCase(PoolBaseTestCase):

    def test_should_calculate_liquidity_units_properly(self):
        # creating event with expected duration 200:
        self.add_line(max_events=1, bets_period=100, measure_period=100)
        self.deposit_liquidity(amount=100)
        self.approve_liquidity()

        self.storage['liquidityUnits'] = 0
        self.current_time = 0

        self.create_event()
        # provided_amount * duration / total_shares:
        expected_units = 100 * (100 + 100) / 100
        self.assertEqual(self.storage['liquidityUnits'], expected_units)

        # should add withdrawal when provider claims:
        self.claim_liquidity(shares=100)
        withdrawal = self.storage['withdrawals'][0]
        self.assertEqual(withdrawal['liquidityUnits'], expected_units)


    def test_multiple_withdrawals_should_have_the_same_units(self):
        self.current_time = 0
        self.add_line()
        entry_a = self.deposit_liquidity(amount=1000)
        entry_b = self.deposit_liquidity(amount=1000)
        position_a = self.approve_liquidity(entry_id=entry_a)
        position_b = self.approve_liquidity(entry_id=entry_b)

        self.create_event()
        self.wait(3600)
        self.create_event()

        self.claim_liquidity(position_id=position_a, shares=1000)
        self.claim_liquidity(position_id=position_b, shares=100)

        w = self.storage['withdrawals']
        units_a = w[0]['liquidityUnits']
        units_b = w[1]['liquidityUnits']

        self.assertEqual(units_a, units_b)

