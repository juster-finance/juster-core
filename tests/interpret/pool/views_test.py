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

