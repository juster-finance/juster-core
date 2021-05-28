""" Test for empty event without any LP and bets
    Test for event that ends EQ (target dynamics === actual dynamics)
"""

from state_transformation_base import (
    StateTransformationBaseTest, RUN_TIME, ONE_HOUR)
from pytezos import MichelsonRuntimeError


class ManagerDeterminedTest(StateTransformationBaseTest):

    def test_update_config(self):

        self.current_time = RUN_TIME
        self.id = len(self.storage['events'])

        # Creating event:
        amount = self.measure_start_fee + self.expiration_fee
        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=amount)

        bets_close = self.default_event_params['betsCloseTime']
        period = self.default_event_params['measurePeriod']

        # No bets / no liquidity, starting measurement:
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

        # Emulating calback with price is increased 25%:
        callback_values.update({'lastUpdate': self.current_time})

        self.storage = self.check_close_callback_succeed(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)

        self.assertTrue(self.storage['events'][self.id]['isbetsAboveEqWin'])
