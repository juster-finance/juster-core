from tests.interpret.pool.pool_base import PoolBaseTestCase


class SimpleProvideAndExitTest(PoolBaseTestCase):
    def test_simple_provide_and_exit(self):

        # creating default event:
        self.add_line()

        # providing liquidity:
        provided_amount = 10_000_000
        self.deposit_liquidity(self.a, amount=provided_amount)
        self.approve_liquidity(self.a, entry_id=0)

        # removing liquidity:
        withdrawn_amount = self.claim_liquidity(
            self.a, position_id=0, shares=provided_amount)

        # checking that pool contract balance not changed
        self.assertEqual(withdrawn_amount, provided_amount)

