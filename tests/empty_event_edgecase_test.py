""" Test edge case when event created without liquidity and then somebody tries
    to withdraw """

from juster_base import JusterBaseTestCase, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class EmptyEventEdgeCase(JusterBaseTestCase):

    def test_should_be_possible_to_remove_event_with_zero_liquidity(self):
        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        # Creating default event:
        self.new_event(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee)

        # No one provides liquidity, no one bets, starting measure:
        bets_close = self.default_event_params['betsCloseTime']
        period = self.default_event_params['measurePeriod']
        self.current_time = bets_close

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time,
            'rate': 6_000_000
        }

        self.start_measurement(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)

        # Closing event:
        self.current_time = bets_close + period

        # Emulating calback with price is increased 25%:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time,
            'rate': 7_500_000
        }
        self.close(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)

        # A tries to withdraw:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.withdraw(self.a, 0)
        msg = 'Participant not found'
        self.assertTrue(msg in str(cm.exception))

