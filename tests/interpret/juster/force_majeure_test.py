""" Tests for Force Majeure circumstances """

from pytezos import MichelsonRuntimeError

from tests.interpret.juster.juster_base import ONE_HOUR
from tests.interpret.juster.juster_base import RUN_TIME
from tests.interpret.juster.juster_base import JusterBaseTestCase


class ForceMajeureTest(JusterBaseTestCase):
    def _prepare_to_force_majeure(self):
        """This code is the same for two tests:"""

        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        # Creating default event:
        self.new_event(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee,
        )

        # Check that trying to run TFM in betting time (at the beginning) is failed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.trigger_force_majeure(sender=self.a)

        # Participant A: adding liquidity 1/1 just at start:
        self.provide_liquidity(
            participant=self.a,
            amount=1_000_000,
            expected_above_eq=1,
            expected_below=1,
        )

        # Participant B: bets aboveEq for 1 tez:
        self.bet(
            participant=self.b,
            amount=1_000_000,
            bet='aboveEq',
            minimal_win=1_000_000,
        )

        # Check that trying to run TFM after betting time
        # (but inside window) is failed:
        self.current_time = self.default_event_params['betsCloseTime']
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.trigger_force_majeure(sender=self.a)

    def test_force_majeure_start_measurement_fail(self):

        self._prepare_to_force_majeure()

        # Trying to run start measurement after time window is elapsed:
        max_lag = self.default_config['maxAllowedMeasureLag']
        self.current_time = (
            self.default_event_params['betsCloseTime'] + max_lag * 2
        )
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1 * ONE_HOUR,
            'rate': 6_000_000,
        }

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.start_measurement(
                callback_values=callback_values,
                source=self.a,
                sender=self.oracle_address,
            )
        msg = 'Measurement failed: oracle time exceed maxAllowedMeasureLag'
        self.assertTrue(msg in str(cm.exception))

        # Failed to start measurement in time window, run TFM is succeed:
        self.trigger_force_majeure(sender=self.a)

        # Trying to bet / LP after TFM should fail with Bets / Providing
        # liquidity after betCloseTime is not allowed. Because of this this
        # scenario is not tested here

        # check A withdraws the same value as he lp-ed:
        self.withdraw(self.a, 1_000_000)
        # B withdraws the same value as he betted:
        self.withdraw(self.b, 1_000_000)

    def test_force_majeure_close_fail(self):

        self._prepare_to_force_majeure()

        bets_close_time = self.default_event_params['betsCloseTime']
        max_lag = self.default_config['maxAllowedMeasureLag']
        measure_period = self.default_event_params['measurePeriod']

        # Running measurement:
        self.current_time = bets_close_time + max_lag // 2

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

        # Trying to run force majeure during measure period is failed:
        self.current_time = bets_close_time + measure_period // 2
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.trigger_force_majeure(sender=self.a)

        # Trying to run force majeure during max lag window is failed:
        self.current_time = bets_close_time + measure_period + max_lag // 2
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.trigger_force_majeure(sender=self.a)

        # Trying to run close after time window is elapsed:
        max_lag = self.default_config['maxAllowedMeasureLag']
        self.current_time = bets_close_time + measure_period + max_lag * 2
        callback_values.update(
            {'lastUpdate': self.current_time - 1 * ONE_HOUR}
        )

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.close(
                callback_values=callback_values,
                source=self.a,
                sender=self.oracle_address,
            )
        msg = "Close failed: oracle time exceed maxAllowedMeasureLag"
        self.assertTrue(msg in str(cm.exception))

        # Failed to close in time window, run TFM is succeed:
        self.trigger_force_majeure(sender=self.a)

        # check A withdraws the same value as he lp-ed:
        self.withdraw(self.a, 1_000_000)
        # B withdraws the same value as he betted:
        self.withdraw(self.b, 1_000_000)

    def test_trying_to_run_force_majeure_twice(self):

        self._prepare_to_force_majeure()
        max_lag = self.default_config['maxAllowedMeasureLag']
        self.current_time = (
            self.default_event_params['betsCloseTime'] + max_lag * 2
        )

        # Failed to start measurement in time window, run TFM is succeed:
        self.trigger_force_majeure(sender=self.a)

        # Running the same force majeure second time, should fail:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.trigger_force_majeure(sender=self.a)
        msg = 'Already in Force Majeure state'
        self.assertTrue(msg in str(cm.exception))

        # check A withdraws the same value as he lp-ed:
        self.withdraw(self.a, 1_000_000)
        # B withdraws the same value as he betted:
        self.withdraw(self.b, 1_000_000)
