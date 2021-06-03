""" Test where provided liquidity is too much """

from state_transformation_base import StateTransformationBaseTest, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class VeryBigNumbersTest(StateTransformationBaseTest):

    def test_very_big_numbers(self):
        self.current_time = RUN_TIME
        self.id = self.storage['lastEventId']

        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee)

        mutez_dugits = 1_000_000
        billion = 1_000_000_000

        # A provides 2 bln tez in liquidity (more than current supply) and succeed:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=2*billion*mutez_dugits,
            expected_above_eq=1,
            expected_bellow=1,
            )

        # Participant B: bets bellow for 1 bln tez and succeed:
        self.storage = self.check_bet_succeed(
            participant=self.b,
            amount=1*billion*mutez_dugits,
            bet='bellow',
            minimal_win=1*billion*mutez_dugits)

        # starting measure:
        bets_close = self.default_event_params['betsCloseTime']
        period = self.default_event_params['measurePeriod']
        self.current_time = bets_close
        self.storage = self.check_start_measurement_succeed(sender=self.a)

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time,
            'rate': 6_000_000
        }
        self.storage = self.check_start_measurement_callback_succeed(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)

        # Closing event:
        self.current_time = bets_close + period
        self.storage = self.check_close_succeed(sender=self.a)

        # Emulating calback:
        callback_values.update({'lastUpdate': self.current_time})
        self.storage = self.check_close_callback_succeed(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)

        self.storage = self.check_withdraw_succeed(self.a, 3*billion*mutez_dugits)
