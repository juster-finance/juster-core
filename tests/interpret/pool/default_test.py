from tests.interpret.pool.pool_base import PoolBaseTestCase
from pytezos import MichelsonRuntimeError


class DefaultEntryTestCase(PoolBaseTestCase):
    def test_should_increase_next_liquidity_if_have_not_paused_events(self):
        self.add_line(max_events=10)
        self.default(sender=self.c, amount=1_000_000)
        self.assertEqual(self.get_next_liquidity(), 100_000)

    def test_should_allow_to_withdraw_amount_from_contract_for_provider(self):
        self.add_line(max_events=2)
        # someone puts liquidity to contract that no one owns:
        self.default(sender=self.d, amount=1_000_000)
        self.assertEqual(self.get_next_liquidity(), 500_000)

        # b deposit 1 xtz and get 100% shares of the contract, so he owns both 2 xtz:
        self.deposit_liquidity(sender=self.b, amount=1_000_000)
        self.approve_liquidity(entry_id=0)
        self.assertEqual(self.get_next_liquidity(), 1_000_000)
        self.claim_liquidity(sender=self.b, position_id=0, shares=1_000_000)
        self.assertEqual(self.balances[self.b], 1_000_000)

        # someone puts liquidity again:
        self.default(sender=self.d, amount=2_000_000)
        self.assertEqual(self.get_next_liquidity(), 1_000_000)

        self.deposit_liquidity(sender=self.c, amount=2_000_000)
        self.approve_liquidity(entry_id=1)
        self.assertEqual(self.storage['totalShares'], 2_000_000)

        self.assertEqual(self.get_next_liquidity(), 2_000_000)
        self.default(sender=self.d, amount=2_000_000)
        self.assertEqual(self.get_next_liquidity(), 3_000_000)

        self.claim_liquidity(sender=self.c, position_id=1, shares=2_000_000)
        self.assertEqual(self.balances[self.c], 4_000_000)
        self.assertEqual(self.balances['contract'], 0)

