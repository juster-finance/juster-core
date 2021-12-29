from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase
from pytezos import MichelsonRuntimeError


class WithdrawLiquidityTestCase(LineAggregatorBaseTestCase):
    def test_should_fail_if_trying_to_withdraw_not_finished_event(self):
        self.add_line()
        self.deposit_liquidity(sender=self.a)
        self.approve_liquidity()
        self.create_event(next_event_id=0)
        self.claim_liquidity(position_id=0)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.withdraw_liquidity(
                sender=self.a,
                positions=[{'eventId': 0, 'positionId': 0}]
            )
        msg = 'Event result is not received yet'
        self.assertTrue(msg in str(cm.exception))


    def test_should_fail_if_trying_to_withdraw_position_with_no_claim(self):
        self.add_line()
        self.deposit_liquidity(sender=self.a)
        self.approve_liquidity(entry_position_id=0)
        self.deposit_liquidity(sender=self.b)
        self.approve_liquidity(entry_position_id=1)
        self.create_event(next_event_id=0)
        self.claim_liquidity(position_id=0)
        self.pay_reward(event_id=0)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.withdraw_liquidity(
                sender=self.b,
                positions=[{'eventId': 0, 'positionId': 1}]
            )
        msg = 'Claim is not found'
        self.assertTrue(msg in str(cm.exception))


    def test_should_fail_if_trying_to_withdraw_from_others_position(self):
        pass

    def test_anyone_can_call_withdraw_for_finished_position(self):
        pass

    def test_multiple_withdraw_should_be_possible(self):
        pass

