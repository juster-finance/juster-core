from tests.interpret.pool.pool_base import PoolBaseTestCase
from pytezos import MichelsonRuntimeError
from tests.test_data import generate_line_params


class PoolViewsTestCase(PoolBaseTestCase):

    def test_get_line_view(self):

        line_params = dict(
            currency_pair='XTZ-USD',
            max_events=2,
            bets_period=3600,
            last_bets_close_time=0,
            juster_address=self.juster_address,
            min_betting_period=0,
            advance_time=0,
            measure_period=3600
        )

        self.add_line(**line_params)
        actual_line = self.get_line(0)
        expected_line = generate_line_params(**line_params)

        self.assertDictEqual(expected_line, actual_line)

        # check requesting line that not in contract does not fail:
        self.assertTrue(self.get_line(42) is None)


    def test_get_next_line_id_view(self):
        self.assertEqual(self.get_next_line_id(), 0)
        self.add_line()
        self.assertEqual(self.get_next_line_id(), 1)


    def test_get_entry_view(self):

        self.add_line()
        self.deposit_liquidity(sender=self.a, amount=1000)

        actual_entry = self.get_entry(0)
        expected_entry = {
            'provider': self.a,
            'acceptAfter': self.current_time,
            'amount': 1000
        }

        self.assertDictEqual(expected_entry, actual_entry)

        # check requesting entry that not in contract does not fail:
        self.assertTrue(self.get_entry(42) is None)


    def test_get_next_entry_id_view(self):
        self.add_line()
        self.assertEqual(self.get_next_entry_id(), 0)
        self.deposit_liquidity(sender=self.a, amount=1000)
        self.assertEqual(self.get_next_entry_id(), 1)


    def test_get_position_view(self):

        self.add_line()
        self.deposit_liquidity(sender=self.a, amount=1000)
        self.approve_liquidity()

        actual_position = self.get_position(0)
        expected_position = {
            'shares': 1000,
            'addedCounter': 0,
            'entryLiquidityUnits': 0,
            'provider': self.a,
        }

        self.assertDictEqual(expected_position, actual_position)

        # check requesting position that not in contract does not fail:
        self.assertTrue(self.get_position(42) is None)


    def test_get_next_position_id_view(self):
        self.add_line()
        self.deposit_liquidity(sender=self.a, amount=1000)
        self.assertEqual(self.get_next_position_id(), 0)
        self.approve_liquidity()
        self.assertEqual(self.get_next_position_id(), 1)


    def test_get_claim_view(self):
        self.add_line(max_events=2)
        self.deposit_liquidity(sender=self.a, amount=1000)
        self.approve_liquidity()
        self.create_event()
        self.claim_liquidity(position_id=0, sender=self.a, shares=420)

        actual_claim = self.get_claim(event_id=0, position_id=0)
        expected_claim = {
            'shares': 420,
            'provider': self.a,
        }

        self.assertDictEqual(expected_claim, actual_claim)

        # check requesting claim that not in contract does not fail:
        self.assertTrue(self.get_claim(event_id=42, position_id=0) is None)


    def test_get_withdrawal_view(self):
        self.add_line(max_events=2)
        self.deposit_liquidity(sender=self.a, amount=1000)
        self.approve_liquidity()
        self.claim_liquidity(position_id=0, sender=self.a, shares=420)

        actual_withdrawal = self.get_withdrawal(withdrawal_id=0)
        expected_withdrawal = {
            'liquidityUnits': 0,
            'positionId': 0,
            'shares': 420,
        }

        self.assertDictEqual(expected_withdrawal, actual_withdrawal)

        # check requesting withdrawal that not in contract does not fail:
        self.assertTrue(self.get_withdrawal(withdrawal_id=42) is None)


    def test_get_next_withdrawal_id_view(self):
        self.add_line()
        self.deposit_liquidity(sender=self.a, amount=1000)
        self.approve_liquidity()
        self.assertEqual(self.get_next_withdrawal_id(), 0)
        self.claim_liquidity(position_id=0, sender=self.a, shares=420)
        self.assertEqual(self.get_next_withdrawal_id(), 1)


    def test_get_active_events_view(self):
        self.add_line()
        self.deposit_liquidity()
        self.approve_liquidity()
        self.assertEqual(self.get_active_events(), {})
        self.create_event()
        self.assertEqual(self.get_active_events(), {0: 0})


    def test_get_event_view(self):
        self.add_line(max_events=1)
        self.deposit_liquidity(sender=self.a, amount=1000)
        self.approve_liquidity()
        self.create_event(next_event_id=777)

        actual_event = self.get_event(event_id=777)
        expected_event = {
            'createdCounter': 1,
            'totalShares': 1000,
            'lockedShares': 0,
            'result': None,
            'shares': 1000,
            'provided': 1000
        }

        self.assertDictEqual(expected_event, actual_event)

        # check requesting withdrawal that not in contract does not fail:
        self.assertTrue(self.get_event(event_id=42) is None)


    def test_is_deposit_paused_view(self):
        self.assertFalse(self.is_deposit_paused())
        self.trigger_pause_deposit()
        self.assertTrue(self.is_deposit_paused())


    def test_get_entry_lock_period_view(self):
        self.assertEqual(self.get_entry_lock_period(), 0)
        self.set_entry_lock_period(new_period=3600)
        self.assertEqual(self.get_entry_lock_period(), 3600)


    def test_get_manager_view(self):
        self.assertEqual(self.get_manager(), self.manager)
        self.propose_manager(proposed_manager=self.c)
        self.accept_ownership(sender=self.c)
        self.assertEqual(self.get_manager(), self.c)


    def test_get_total_shares_view(self):
        self.add_line()
        self.deposit_liquidity(amount=100)
        self.assertEqual(self.get_total_shares(), 0)
        self.approve_liquidity()
        self.assertEqual(self.get_total_shares(), 100)


    def test_get_next_liquidity_view(self):
        self.add_line(max_events=10)
        self.deposit_liquidity(amount=100)
        self.assertEqual(self.get_next_liquidity_f(), 0)
        self.approve_liquidity()
        expected_next_liquidity = 10 * self.storage['precision']
        self.assertEqual(self.get_next_liquidity_f(), expected_next_liquidity)


    def test_get_liquidity_units_view(self):
        self.current_time = 0
        self.add_line(max_events=4, measure_period=10, bets_period=10)
        self.deposit_liquidity(amount=100)
        self.approve_liquidity()
        self.assertEqual(self.get_liquidity_units(), 0)
        self.create_event()
        # provided * duration / total_shares:
        expected_liquidity_units = 25 * (10+10) / 100
        self.assertEqual(self.get_liquidity_units(), expected_liquidity_units)


    def test_get_state_values_view(self):
        self.add_line(max_events=2)
        self.deposit_liquidity(amount=100)
        self.approve_liquidity()
        self.deposit_liquidity(amount=100)
        self.assertEqual(self.get_liquidity_units(), 0)
        self.create_event()

        precision = self.storage['precision']
        actual_state_values = self.get_state_values()
        expected_state_values = {
            'precision': precision,
            'activeLiquidityF': 50 * precision,
            'withdrawableLiquidityF': 0,
            'entryLiquidityF': 100 * precision,
            'counter': 2,
            'maxEvents': 2,
        }
        self.assertDictEqual(expected_state_values, actual_state_values)

