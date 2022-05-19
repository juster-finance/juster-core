""" Reproducing bug with wrong withdrawals for provider that deposited two times with
    the reversal of the ratio
"""

from pytezos import MichelsonRuntimeError

from tests.interpret.juster.juster_base import ONE_HOUR
from tests.interpret.juster.juster_base import RUN_TIME
from tests.interpret.juster.juster_base import JusterBaseTestCase


class FourParticipantsDeterminedTest(JusterBaseTestCase):

    def test_should_handle_reverse_ratio(self):

        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        # Creating event:
        amount = self.measure_start_fee + self.expiration_fee
        self.new_event(
            event_params=self.default_event_params,
            amount=amount)

        # Participant A: adding liquidity 2:1:
        self.provide_liquidity(
            participant=self.a,
            amount=2_000_000,
            expected_above_eq=2,
            expected_below=1)

        # Participant B: bets below reversing ratio to 1:2:
        self.bet(
            participant=self.b,
            amount=1_000_000,
            bet='below',
            minimal_win=1_000_000)

        # Participant A: adding more liquidity for new ratio 1:2:
        self.provide_liquidity(
            participant=self.a,
            amount=2_000_000,
            expected_above_eq=1,
            expected_below=2)

        # Running measurement:
        self.current_time = RUN_TIME + 26*ONE_HOUR

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1*ONE_HOUR,
            'rate': 6_000_000
        }
        self.start_measurement(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)

        # Closing event:
        self.current_time = RUN_TIME + 38*ONE_HOUR

        # Emulating calback with price is increased 25%:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1*ONE_HOUR,
            'rate': 7_500_000
        }
        self.close(
            callback_values=callback_values,
            source=self.b,
            sender=self.oracle_address)

        # Withdrawals:
        self.current_time = RUN_TIME + 64*ONE_HOUR
        self.withdraw(self.a, 5_000_000)
        self.withdraw(self.b, 0)

