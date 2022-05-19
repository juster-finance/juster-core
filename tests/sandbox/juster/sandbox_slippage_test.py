from pytezos.rpc.errors import MichelsonError

from tests.sandbox.sandbox_base import SandboxedJusterTestCase


class SandboxSlippageTestCase(SandboxedJusterTestCase):

    def test_slippage(self):
        self._create_simple_event(self.manager)
        self._provide_liquidity(
            event_id=0,
            user=self.manager,
            expected_below=1,
            expected_above_eq=1,
            max_slippage=1000,
            amount=1_000_000
        )
        self.bake_block()

        # B bets in aboveEq:
        bet_res = self._bet(
            event_id=0,
            user=self.b,
            side='aboveEq',
            minimal_win_amount=1_500_000,
            amount=1_000_000
        )

        # A provides liquidity after b made bet in the same block:
        pl_res = self._provide_liquidity(
            event_id=0,
            user=self.manager,
            expected_below=1,
            expected_above_eq=1,
            max_slippage=1000,
            amount=1_000_000
        )

        self.bake_block()
        bet_res = self._find_call_result_by_hash(self.a, bet_res.hash())

        with self.assertRaises(MichelsonError) as cm:
            pl_res = self._find_call_result_by_hash(self.a, pl_res.hash())

        self.assertTrue(
            'Expected ratio very differs from current pool ratio'
            in str(cm.exception))
