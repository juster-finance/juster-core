""" Tests for Force Majeure circumstances """

from pytezos import MichelsonRuntimeError

from tests.interpret.juster.juster_base import ONE_HOUR
from tests.interpret.juster.juster_base import RUN_TIME
from tests.interpret.juster.juster_base import JusterBaseTestCase


class SlippageTest(JusterBaseTestCase):
    def test_minimal_win(self):
        """Testing bet minimal win option:"""

        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        # Creating default event:
        self.new_event(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee,
        )

        # Participant A: adding liquidity 1tez in each pool:
        self.provide_liquidity(
            participant=self.a,
            amount=2_000_000,
            expected_above_eq=1,
            expected_below=1,
        )

        # Participant B bets aboveEq with 1tez, expected minimal win 1_500_000 succeed:
        self.bet(
            participant=self.b,
            amount=1_000_000,
            bet='aboveEq',
            minimal_win=1_500_000,
        )

        # Participant B bets aboveEq with 1tez, expected minimal win 1_500_001 failed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.bet(
                participant=self.b,
                amount=1_000_000,
                bet='aboveEq',
                minimal_win=1_500_001,
            )
        msg = 'Wrong minimalWinAmount'
        self.assertTrue(msg in str(cm.exception))

    def test_slippage(self):
        """Testing provide liquidity slippage option:"""

        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        # Creating default event:
        self.new_event(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee,
        )

        # Participant A: adding liquidity 2:1:
        self.provide_liquidity(
            participant=self.a,
            amount=3_000_000,
            expected_above_eq=2,
            expected_below=1,
        )

        # Participant B: adding liquidity 400:100 with slippage 100% succeed:
        slippage_100 = self.storage['ratioPrecision']

        self.provide_liquidity(
            participant=self.a,
            amount=3_000_000,
            expected_above_eq=400,
            expected_below=100,
            max_slippage=slippage_100,
        )

        # Participant B: adding liquidity 401:100 with slippage 100% fails:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.provide_liquidity(
                participant=self.a,
                amount=3_000_000,
                expected_above_eq=401,
                expected_below=100,
                max_slippage=slippage_100,
            )
        msg = 'Expected ratio very differs from current pool ratio'
        self.assertTrue(msg in str(cm.exception))

        # Participant B: adding liquidity 100:100 with slippage 100% succeed:
        self.provide_liquidity(
            participant=self.a,
            amount=3_000_000,
            expected_above_eq=100,
            expected_below=100,
            max_slippage=slippage_100,
        )

        # Participant B: adding liquidity 100:101 with slippage 100% fails:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.provide_liquidity(
                participant=self.a,
                amount=3_000_000,
                expected_above_eq=100,
                expected_below=101,
                max_slippage=slippage_100,
            )
        msg = 'Expected ratio very differs from current pool ratio'
        self.assertTrue(msg in str(cm.exception))

        # Participant B: adding liquidity 300:100 with slippage 50% succeed:
        slippage_50 = slippage_100 // 2

        self.provide_liquidity(
            participant=self.a,
            amount=3_000_000,
            expected_above_eq=300,
            expected_below=100,
            max_slippage=slippage_50,
        )

        # Participant B: adding liquidity 301:100 with slippage 50% fails:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.provide_liquidity(
                participant=self.a,
                amount=3_000_000,
                expected_above_eq=301,
                expected_below=100,
                max_slippage=slippage_50,
            )
        msg = 'Expected ratio very differs from current pool ratio'
        self.assertTrue(msg in str(cm.exception))
