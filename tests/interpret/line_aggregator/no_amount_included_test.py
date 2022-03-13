from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase
from pytezos import MichelsonRuntimeError


class NoAmountIncludedTestCase(LineAggregatorBaseTestCase):

    def test_entrypoints_should_not_allow_to_send_any_xtz(self):
        calls = [
            lambda: self.add_line(sender=self.admin, amount=100),
            lambda: self.approve_liquidity(sender=self.admin, amount=100),
            lambda: self.cancel_liquidity(sender=self.admin, amount=100),
            lambda: self.claim_liquidity(sender=self.admin, amount=100),
            lambda: self.withdraw_liquidity(sender=self.admin, amount=100),
            lambda: self.create_event(sender=self.admin, amount=100),
        ]

        for call in calls:
            with self.assertRaises(MichelsonRuntimeError) as cm:
                call()
            self.assertTrue('This entrypoint should not receive tez' in str(cm.exception))

