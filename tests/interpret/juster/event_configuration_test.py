""" Tests that checks different edgecases in event creation """

from pytezos import MichelsonRuntimeError

from tests.interpret.juster.juster_base import ONE_HOUR
from tests.interpret.juster.juster_base import RUN_TIME
from tests.interpret.juster.juster_base import JusterBaseTestCase


class EventConfigurationTest(JusterBaseTestCase):

    def test_event_configuration(self):
        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        # Checking that creating event with too short measure period is failed:
        min_measure_period = self.default_config['minMeasurePeriod']
        event_params = self.default_event_params.copy()
        event_params['measurePeriod'] = min_measure_period // 2

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.new_event(
                event_params=event_params,
                amount=self.measure_start_fee + self.expiration_fee)
        msg = 'measurePeriod is less than minimal value'
        self.assertTrue(msg in str(cm.exception))

        # Checking that creating event with too big measure period is failed:
        max_measure_period = self.default_config['maxMeasurePeriod']
        event_params = self.default_event_params.copy()
        event_params['measurePeriod'] = max_measure_period * 2

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.new_event(
                event_params=event_params,
                amount=self.measure_start_fee + self.expiration_fee)
        msg = 'measurePeriod is exceed maximum value'
        self.assertTrue(msg in str(cm.exception))

        # Checking that creating event that closes too soon is failed:
        min_period_btc = self.default_config['minPeriodToBetsClose']
        event_params = self.default_event_params.copy()
        event_params['betsCloseTime'] = RUN_TIME + min_period_btc // 2

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.new_event(
                event_params=event_params,
                amount=self.measure_start_fee + self.expiration_fee)
        msg = 'betsCloseTime is less than minimal allowed period'
        self.assertTrue(msg in str(cm.exception))

        # Checking that creating event that have too big bets time is failed:
        max_period_btc = self.default_config['maxPeriodToBetsClose']
        event_params = self.default_event_params.copy()
        event_params['betsCloseTime'] = RUN_TIME + max_period_btc * 2

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.new_event(
                event_params=event_params,
                amount=self.measure_start_fee + self.expiration_fee)
        msg = 'betsCloseTime is exceed maximum allowed period'
        self.assertTrue(msg in str(cm.exception))

        # Checking that creating event with too small liquidity fee is failed:
        self.storage['config']['minLiquidityPercent'] = 10_000
        event_params = self.default_event_params.copy()
        event_params['liquidityPercent'] = 1_000

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.new_event(
                event_params=event_params,
                amount=self.measure_start_fee + self.expiration_fee)
        msg = 'liquidityPercent is less than minimal value'
        self.assertTrue(msg in str(cm.exception))

        # Checking that creating event with too big liquidity fee is failed:
        max_liquidity_fee = self.default_config['maxLiquidityPercent']
        event_params = self.default_event_params.copy()
        event_params['liquidityPercent'] = max_liquidity_fee * 2

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.new_event(
                event_params=event_params,
                amount=self.measure_start_fee + self.expiration_fee)
        msg = 'liquidityPercent is exceed maximum value'
        self.assertTrue(msg in str(cm.exception))

