""" Tests for Force Majeure circumstances """

from juster_base import JusterBaseTestCase, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class ForceMajeureTest(JusterBaseTestCase):

    def _prepare_to_force_majeure(self):
        """ This code is the same for two tests: """

        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        # Creating default event:
        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee)

        # Check that trying to run TFM in betting time (at the beginning) is failed:
        self.check_trigger_force_majeure_fails_with(sender=self.a)

        # Participant A: adding liquidity 1/1 just at start:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=1_000_000,
            expected_above_eq=1,
            expected_below=1)

        # Participant B: bets aboveEq for 1 tez:
        self.storage = self.check_bet_succeed(
            participant=self.b,
            amount=1_000_000,
            bet='aboveEq',
            minimal_win=1_000_000)

        # Check that trying to run TFM after betting time
        # (but inside window) is failed:
        self.current_time = self.default_event_params['betsCloseTime']
        self.check_trigger_force_majeure_fails_with(sender=self.a)


    def test_force_majeure_start_measurement_fail(self):

        self._prepare_to_force_majeure()

        # Trying to run start measurement after time window is elapsed:
        max_lag = self.default_config['maxAllowedMeasureLag']
        self.current_time = self.default_event_params['betsCloseTime'] + max_lag*2
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1*ONE_HOUR,
            'rate': 6_000_000
        }

        self.check_start_measurement_callback_fails_with(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address,
            msg_contains='Measurement failed: oracle time exceed maxAllowedMeasureLag')

        # Failed to start measurement in time window, run TFM is succeed:
        self.storage = self.check_trigger_force_majeure_succeed(sender=self.a)

        # Trying to bet / LP after TFM should fail with Bets / Providing
        # liquidity after betCloseTime is not allowed. Because of this this
        # scenario is not tested here

        # check A withdraws the same value as he lp-ed:
        self.storage = self.check_withdraw_succeed(self.a, 1_000_000)
        # B withdraws the same value as he betted:
        self.storage = self.check_withdraw_succeed(self.b, 1_000_000)


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
            'lastUpdate': self.current_time - int(0.5*ONE_HOUR),
            'rate': 8_000_000
        }
        self.storage = self.check_start_measurement_succeed(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)

        # Trying to run force majeure during measure period is failed:
        self.current_time = bets_close_time + measure_period // 2
        self.check_trigger_force_majeure_fails_with(sender=self.a)

        # Trying to run force majeure during max lag window is failed:
        self.current_time = bets_close_time + measure_period + max_lag // 2
        self.check_trigger_force_majeure_fails_with(sender=self.a)

        # Trying to run close after time window is elapsed:
        max_lag = self.default_config['maxAllowedMeasureLag']
        self.current_time = bets_close_time + measure_period + max_lag * 2
        callback_values.update({'lastUpdate': self.current_time - 1*ONE_HOUR})

        self.check_close_callback_fails_with(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address,
            msg_contains='Close failed: oracle time exceed maxAllowedMeasureLag')

        # Failed to close in time window, run TFM is succeed:
        self.storage = self.check_trigger_force_majeure_succeed(sender=self.a)

        # check A withdraws the same value as he lp-ed:
        self.storage = self.check_withdraw_succeed(self.a, 1_000_000)
        # B withdraws the same value as he betted:
        self.storage = self.check_withdraw_succeed(self.b, 1_000_000)
