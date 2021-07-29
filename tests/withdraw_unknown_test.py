""" Testing that it is impossible to withdraw for participant that
    are not participated in event (or that are already withdrawn)
"""

from juster_base import JusterBaseTestCase, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class WithdrawUnknownTest(JusterBaseTestCase):

    def test_withdraw_unknown(self):
        """ Test that witdrawing for unknown participant would not succeed """

        amount = self.measure_start_fee + self.expiration_fee

        # Creating empty event with no participants:
        self.new_event(
            event_params=self.default_event_params, amount=amount)

        # Forced finish:
        self.storage['events'][0].update({
            'isClosed': True,
            'isBetsAboveEqWin': True
        })

        # Withdraw is not succeed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.withdraw(self.a, 1_000_000)
        msg = 'Participant not found'
        self.assertTrue(msg in str(cm.exception))


    def test_withdraw_twice(self):
        """ Test that witdrawing second time would raise error """

        amount = self.measure_start_fee + self.expiration_fee

        # Making event with provided liquidity:
        self.new_event(
            event_params=self.default_event_params, amount=amount)

        # A provides liquidity with 1 tez:
        self.provide_liquidity(
            participant=self.a,
            amount=1_000_000,
            expected_above_eq=1,
            expected_below=1)

        # Forced finish:
        self.storage['events'][0].update({
            'isClosed': True,
            'isBetsAboveEqWin': True
        })

        # First withdraw is succeed:
        self.withdraw(self.a, 1_000_000)

        # Second raises error:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.withdraw(self.a, 1_000_000)
        msg = 'Participant not found'
        self.assertTrue(msg in str(cm.exception))

