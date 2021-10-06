from sandbox_base import SandboxedJusterTestCase
from pytezos.rpc.errors import MichelsonError


class SandboxSlippageTestCase(SandboxedJusterTestCase):

    def test_slippage(self):
        self._create_simple_event(self.manager)

        self.manager.contract(self.juster.address).provideLiquidity(
            eventId=0,
            expectedRatioBelow=1,
            expectedRatioAboveEq=1,
            maxSlippage=1000
        ).with_amount(1_000_000).inject()

        self.bake_block()

        # B bets in aboveEq:
        bet_res = self.b.contract(self.juster.address).bet(
            eventId=0,
            bet='aboveEq',
            minimalWinAmount=1_500_000
        ).with_amount(1_000_000).inject()

        # A provides liquidity after b made bet in the same block:
        pl_res = self.a.contract(self.juster.address).provideLiquidity(
            eventId=0,
            expectedRatioBelow=1,
            expectedRatioAboveEq=1,
            maxSlippage=1000
        ).with_amount(1_000_000).inject()

        self.bake_block()
        bet_res = self._find_call_result_by_hash(self.a, bet_res['hash'])

        with self.assertRaises(MichelsonError) as cm:
            pl_res = self._find_call_result_by_hash(self.a, pl_res['hash'])

        self.assertTrue(
            'Expected ratio very differs from current pool ratio'
            in str(cm.exception))

