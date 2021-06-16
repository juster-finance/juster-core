""" Tests that checks different edgecases in event creation """

from state_transformation_base import StateTransformationBaseTest, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class EventConfigurationDeterminedTest(StateTransformationBaseTest):

    def test_event_configuration(self):
        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        # Checking that creating event with too short measure period is failed:
        min_measure_period = self.default_config['minMeasurePeriod']
        event_params = self.default_event_params.copy()
        event_params['measurePeriod'] = min_measure_period // 2

        self.check_new_event_fails_with(
            event_params=event_params,
            amount=self.measure_start_fee + self.expiration_fee,
            msg_contains='measurePeriod is less than minimal value')

        # Checking that creating event with too big measure period is failed:
        max_measure_period = self.default_config['maxMeasurePeriod']
        event_params = self.default_event_params.copy()
        event_params['measurePeriod'] = max_measure_period * 2

        self.check_new_event_fails_with(
            event_params=event_params,
            amount=self.measure_start_fee + self.expiration_fee,
            msg_contains='measurePeriod is exceed maximum value')

        # Checking that creating event that closes too soon is failed:
        min_period_btc = self.default_config['minPeriodToBetsClose']
        event_params = self.default_event_params.copy()
        event_params['betsCloseTime'] = RUN_TIME + min_period_btc // 2

        self.check_new_event_fails_with(
            event_params=event_params,
            amount=self.measure_start_fee + self.expiration_fee,
            msg_contains='betsCloseTime is less than minimal allowed period')

        # Checking that creating event that have too big bets time is failed:
        max_period_btc = self.default_config['maxPeriodToBetsClose']
        event_params = self.default_event_params.copy()
        event_params['betsCloseTime'] = RUN_TIME + max_period_btc * 2

        self.check_new_event_fails_with(
            event_params=event_params,
            amount=self.measure_start_fee + self.expiration_fee,
            msg_contains='betsCloseTime is exceed maximum allowed period')


        # Checking that creating event with too small liquidity fee is failed:
        self.storage['config']['minLiquidityPercent'] = 10_000
        event_params = self.default_event_params.copy()
        event_params['liquidityPercent'] = 1_000

        self.check_new_event_fails_with(
            event_params=event_params,
            amount=self.measure_start_fee + self.expiration_fee,
            msg_contains='liquidityPercent is less than minimal value')

        # Checking that creating event with too big liquidity fee is failed:
        max_liquidity_fee = self.default_config['maxLiquidityPercent']
        event_params = self.default_event_params.copy()
        event_params['liquidityPercent'] = max_liquidity_fee * 2

        self.check_new_event_fails_with(
            event_params=event_params,
            amount=self.measure_start_fee + self.expiration_fee,
            msg_contains='liquidityPercent is exceed maximum value')
