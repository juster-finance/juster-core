from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase


class MultipleEventsAndProvidersTest(LineAggregatorBaseTestCase):
    def test_multiple_events_and_providers(self):

        # creating multiple lines with different pairs:
        self.add_line(currency_pair='XTZ-USD', max_active_events=1)
        self.add_line(currency_pair='ETH-USD', max_active_events=1)
        self.add_line(currency_pair='BTC-USD', max_active_events=1)

        # providing liquidity with first provider:
        self.deposit_liquidity(self.a, amount=3_000_000)

        # import pdb; pdb.set_trace()
        # running two events, in each should be added 1xtz:
        # TODO: this next line fails with "'Juster.getNextEventId view is not found'" Michelson runtime error
        self.create_event(0, next_event_id=0)
        self.create_event(1, next_event_id=1)

        # second provider adds the same amount of liquidity:
        self.deposit_liquidity(self.b, amount=3_000_000)

        # running last event with 4xtz liquidity:
        self.create_event(2, next_event_id=2)

        self.wait(3600)

        # let first two events be profitable and last not:
        self.pay_reward(event_id=0, amount=2_000_000)
        self.pay_reward(event_id=1, amount=2_000_000)
        self.pay_reward(event_id=2, amount=2_000_000)

        # TODO: remove this thoughts somewhere else:
        # In ideal scenario A should get all the profit from 0 and 1 (+2xtz)
        # and pay for the last event 50% (-1xtz)
        # B should pay for the last event 50% (-1xtz)

        # However looks like this logic would not work here
        # it can be exploitable, when provider sees that there are event that
        # profitable for providers he can get into aggregator and then get shares
        # cheaper that they are

        # solutions? 1) keep as it is and exploit
        # 2) recalculate share price each time pay_reward is called (but is it possible?)
        # 3) lock shares that are in provided liquidity and evaluate new provided liquidity
        # according to the unknown price of locked shares (looks impossible)
        # 4) add fees for withdrawing liquidity in first K hours/days (the way plenty does)

        # The second cycle both providers in place:
        self.create_event(0, next_event_id=3)
        self.create_event(1, next_event_id=4)
        self.create_event(2, next_event_id=5)

        self.wait(3600)
        self.pay_reward(event_id=3, amount=3_000_000)
        self.pay_reward(event_id=4, amount=1_000_000)
        self.pay_reward(event_id=5, amount=4_000_000)

        # Both providers should have the same shares and should earn 2xtz:
        # removing liquidity:
        withdrawn_amount = self.claim_liquidity(
            self.a, position_id=0, shares=3_000_000)
        self.assertEqual(withdrawn_amount, 4_000_000)

        withdrawn_amount = self.claim_liquidity(
            self.b, position_id=1, shares=3_000_000)
        self.assertEqual(withdrawn_amount, 4_000_000)

