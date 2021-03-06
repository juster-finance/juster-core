""" Test with simple multiple events + models equal """

from pytezos import MichelsonRuntimeError

from tests.interpret.juster.juster_base import ONE_HOUR
from tests.interpret.juster.juster_base import RUN_TIME
from tests.interpret.juster.juster_base import JusterBaseTestCase


class MultipleEventsTest(JusterBaseTestCase):
    def _run_measurement(self):
        """Run defaul measurement call and callback:"""

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - int(0.5 * ONE_HOUR),
            'rate': 8_000_000,
        }
        self.start_measurement(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address,
        )

    def _run_close(self):
        """Run defaul close call and callback:"""

        # Emulating calback with price is increased 25%:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - int(0.5 * ONE_HOUR),
            'rate': 10_000_000,
        }
        self.close(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address,
        )

    def test_with_multiple_events(self):
        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        # Creating event 0:
        self.new_event(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee,
        )

        # B provides liquidity [x3 1 tez]:
        for _ in range(3):
            self.provide_liquidity(
                participant=self.b,
                amount=1_000_000,
                expected_above_eq=1,
                expected_below=1,
            )

        # Creating event 1:
        self.id = self.storage['nextEventId']
        self.new_event(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee,
        )

        # B provides liquidity [x1 3 tez]:
        self.provide_liquidity(
            participant=self.b,
            amount=3_000_000,
            expected_above_eq=1,
            expected_below=1,
        )

        # Checking that ratios in event 0 and 1 are the same:
        event_0 = self.storage['events'][0]
        event_1 = self.storage['events'][1]
        self.assertEqual(event_0['poolAboveEq'], event_1['poolAboveEq'])
        self.assertEqual(event_0['poolBelow'], event_1['poolBelow'])

        # No one bets, measure, close, B withdraws all in both events:
        bets_close_time = self.default_event_params['betsCloseTime']
        max_lag = self.default_config['maxAllowedMeasureLag']
        measure_period = self.default_event_params['measurePeriod']

        for event_id in [0, 1]:
            self.id = event_id

            self.current_time = bets_close_time + max_lag // 2
            self._run_measurement()

            self.current_time = bets_close_time + measure_period + max_lag // 2
            self._run_close()

            self.withdraw(self.b, 3_000_000)

        # Creating event 2:
        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']
        self.new_event(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee,
        )

        # A provides liquidity with 3:1 rate:
        self.provide_liquidity(
            participant=self.a,
            amount=3_000_000,
            expected_above_eq=3,
            expected_below=1,
        )

        # B bets three times for 1 tez:
        for _ in range(3):
            self.bet(
                participant=self.b,
                amount=1_000_000,
                bet='aboveEq',
                minimal_win=1_000_000,
            )

        # Creating event 3:
        self.id = self.storage['nextEventId']
        self.new_event(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee,
        )

        # A provides liquidity with 3:1 rate:
        self.provide_liquidity(
            participant=self.a,
            amount=3_000_000,
            expected_above_eq=3,
            expected_below=1,
        )

        # B bets one time for 3 tez:
        self.bet(
            participant=self.b,
            amount=3_000_000,
            bet='aboveEq',
            minimal_win=3_000_000,
        )

        # Checking that ratios in event 2 and 3 are the same:
        event_2 = self.storage['events'][2]
        event_3 = self.storage['events'][3]
        self.assertEqual(event_2['poolAboveEq'], event_3['poolAboveEq'])
        self.assertEqual(event_2['poolBelow'], event_3['poolBelow'])

        # Measure, close, B wins 1:6 0.5tez:
        for event_id in [2, 3]:
            self.id = event_id

            self.current_time = bets_close_time + max_lag // 2
            self._run_measurement()

            self.current_time = bets_close_time + measure_period + max_lag // 2
            self._run_close()

            self.withdraw(self.a, 2_500_000)
            self.withdraw(self.b, 3_500_000)
