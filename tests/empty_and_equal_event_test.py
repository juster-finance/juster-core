""" Test for empty event without any LP and bets
    Test for event that ends EQ (target dynamics === actual dynamics)
"""

from juster_base import (
    JusterBaseTestCase, RUN_TIME, ONE_HOUR)
from pytezos import MichelsonRuntimeError


class EmptyEqualEventTest(JusterBaseTestCase):

    def test_empty_equal_event(self):

        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        # Creating event:
        amount = self.measure_start_fee + self.expiration_fee
        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=amount)

        bets_close = self.default_event_params['betsCloseTime']
        period = self.default_event_params['measurePeriod']

        # No bets / no liquidity, starting measurement:
        self.current_time = bets_close

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time,
            'rate': 6_000_000
        }
        self.storage = self.check_start_measurement_succeed(
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

        self.assertTrue(self.storage['events'][self.id]['isBetsAboveEqWin'])
