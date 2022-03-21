from tests.interpret.pool.pool_base import PoolBaseTestCase
from pytezos import MichelsonRuntimeError
from tests.test_data import generate_line_params


class PoolViewsTestCase(PoolBaseTestCase):

    def get_line(self, line_id):
        return self.pool.getLine(line_id).onchain_view(storage=self.storage)

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

