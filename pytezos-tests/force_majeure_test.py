""" Tests for Force Majeure circumstances """

from state_transformation_base import StateTransformationBaseTest, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class ForceMajeureDeterminedTest(StateTransformationBaseTest):

    def test_force_majeure_start_measurement_fail(self):

        self.current_time = RUN_TIME
        self.id = len(self.storage['events'])

        # Creating default event:
        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee)

        # Check that trying to run TFM in betting time (at the beginning) is failed:
        self.check_trigger_force_majeure_fails_with(sender=self.a)

        # Participant A: adding liquidity 1/1 just at start:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=2_000_000,
            expected_for=1,
            expected_against=1)

        # Participant B: bets FOR for 1 tez:
        self.storage = self.check_bet_succeed(
            participant=self.b,
            amount=1_000_000,
            bet='for',
            minimal_win=1_000_000)

        # Check that trying to run TFM after betting time
        # (but inside window) is failed:
        self.current_time = self.default_event_params['betsCloseTime']
        self.check_trigger_force_majeure_fails_with(sender=self.a)

        # Failed to start measurement in time window, run TFM is succeed:
        max_lag = self.default_config['maxAllowedMeasureLag']
        self.current_time = self.default_event_params['betsCloseTime'] + max_lag*2
        self.storage = self.check_trigger_force_majeure_succeed(sender=self.a)

        # Trying to bet / LP after TFM should fail with Bets / Providing
        # liquidity after betCloseTime is not allowed. Because of this this
        # scenario is not tested here

        # check A withdraws the same value as he lp-ed:
        self.storage = self.check_withdraw_succeed(self.a, 2_000_000)
        # B withdraws the same value as he betted:
        self.storage = self.check_withdraw_succeed(self.b, 1_000_000)


    def test_force_majeure_close_fail(self):

        self.current_time = RUN_TIME
        self.id = len(self.storage['events'])

        # Creating default event:
        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee)

        # TODO:
