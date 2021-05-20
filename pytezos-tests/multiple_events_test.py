""" Test with simple multiple events + models equal """

from state_transformation_base import StateTransformationBaseTest, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class MultipleEventsDeterminedTest(StateTransformationBaseTest):

    def _run_measurement(self):
        """ Run defaul measurement call and callback: """

        self.storage = self.check_start_measurement_succeed(sender=self.a)

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - int(0.5*ONE_HOUR),
            'rate': 8_000_000
        }
        self.storage = self.check_start_measurement_callback_succeed(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)


    def _run_close(self):
        """ Run defaul close call and callback: """

        self.storage = self.check_close_succeed(sender=self.a)

        # Emulating calback with price is increased 25%:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - int(0.5*ONE_HOUR),
            'rate': 10_000_000
        }
        self.storage = self.check_close_callback_succeed(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)


    def test_with_multiple_events(self):
        self.current_time = RUN_TIME
        self.id = len(self.storage['events'])

        # Creating event 0:
        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee)

        # B provides liquidity [x3 1 tez]:
        for _ in range(3):
            self.storage = self.check_provide_liquidity_succeed(
                participant=self.b,
                amount=1_000_000,
                expected_for=1,
                expected_against=1)

        # Creating event 1:
        self.id = len(self.storage['events'])
        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee)

        # B provides liquidity [x1 3 tez]:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.b,
            amount=3_000_000,
            expected_for=1,
            expected_against=1)

        # Checking that ratios in event 1 and 2 are the same:
        event_0 = self.storage['events'][0]
        event_1 = self.storage['events'][1]
        self.assertEqual(event_0['poolFor'], event_1['poolFor'])
        self.assertEqual(event_0['poolAgainst'], event_1['poolAgainst'])

        # No one bets, measure, close, B withdraws all in both events:
        self.current_time = RUN_TIME
        bets_close_time = self.default_event_params['betsCloseTime']
        max_lag = self.default_config['maxAllowedMeasureLag']
        measure_period = self.default_event_params['measurePeriod']

        for event_id in [0, 1]:
            self.id = event_id

            self.current_time = bets_close_time + max_lag // 2
            self._run_measurement()

            self.current_time = bets_close_time + measure_period + max_lag // 2
            self._run_close()

            self.storage = self.check_withdraw_succeed(self.b, 3_000_000)


        """ TODO:
        - event created 3
        - A provides liquidity with 3:1 rate
        - PARALLEL: B bets three times for 1 tez

        - event created 4
        - A provides liquidity with 3:1 rate
        - PARALLEL: B bets one time for 3 tez
        TODO: check that ratios in event 3 & 4 the same
        - finishing event 3, 4, withdrawing
            - check balance account is zero
        - event 3 B loosed, check that zero operation in withdraw is succeed
        - event 3 B wins

        - TODO: check that all ledgers and event records is cleaned at close

        """
