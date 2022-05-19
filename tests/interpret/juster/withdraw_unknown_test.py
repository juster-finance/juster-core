""" Testing that it is impossible to withdraw for participant that
    are not participated in event (or that are already withdrawn)
"""

from pytezos import MichelsonRuntimeError

from tests.interpret.juster.juster_base import ONE_HOUR
from tests.interpret.juster.juster_base import RUN_TIME
from tests.interpret.juster.juster_base import JusterBaseTestCase


class WithdrawUnknownTest(JusterBaseTestCase):
    def test_withdraw_unknown(self):
        """Test that witdrawing for unknown participant would not succeed"""

        amount = self.measure_start_fee + self.expiration_fee

        # Creating empty event with one paritcipant:
        self.new_event(event_params=self.default_event_params, amount=amount)

        # A provides liquidity with 1 tez:
        self.provide_liquidity(
            participant=self.a,
            amount=1_000_000,
            expected_above_eq=1,
            expected_below=1,
        )

        # Forced finish:
        self.storage['events'][0].update(
            {'closedOracleTime': 0, 'isClosed': True, 'isBetsAboveEqWin': True}
        )

        # B is not participated so withdraw should fail:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.withdraw(self.b, 0)
        msg = 'Participant not found'
        self.assertTrue(msg in str(cm.exception))

    def test_withdraw_twice(self):
        """Test that witdrawing second time would raise error"""

        amount = self.measure_start_fee + self.expiration_fee

        # Making simple event with two providers (need two so event would
        # not be removed after first withdrawal):
        self.new_event(event_params=self.default_event_params, amount=amount)

        # A provides liquidity with 1 tez:
        self.provide_liquidity(
            participant=self.a,
            amount=1_000_000,
            expected_above_eq=1,
            expected_below=1,
        )

        # B provides liquidity with 1 tez:
        self.provide_liquidity(
            participant=self.b,
            amount=1_000_000,
            expected_above_eq=1,
            expected_below=1,
        )

        # Forced finish:
        self.storage['events'][0].update(
            {'closedOracleTime': 0, 'isClosed': True, 'isBetsAboveEqWin': True}
        )

        # First withdraw is succeed:
        self.withdraw(self.a, 1_000_000)

        # Second raises error:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.withdraw(self.a, 1_000_000)

        msg = 'Already withdrawn'
        self.assertTrue(msg in str(cm.exception))
