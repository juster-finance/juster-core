from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase


class SimpleProvideAndExitTest(LineAggregatorBaseTestCase):
    def test_simple_provide_and_exit(self):

        # creating default event:
        self.add_line()

        # providing liquidity:
        provided_amount = 10_000_000
        self.deposit_liquidity(self.a, amount=provided_amount)

        # removing liquidity:
        withdrawn_amount = self.claim_liquidity(
            self.a, position_id=0, shares=provided_amount)

        # checking that line_aggregator contract balance not changed
        self.assertEqual(withdrawn_amount, provided_amount)

