from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase


class MultipleEventsAndProvidersTest(LineAggregatorBaseTestCase):
    def test_multiple_events_and_providers(self):

        # creating multiple lines with different pairs:
        self.add_line(currency_pair='XTZ-USD', max_active_events=1)
        self.add_line(currency_pair='ETH-USD', max_active_events=1)
        self.add_line(currency_pair='BTC-USD', max_active_events=1)

        # providing liquidity with first provider:
        self.deposit_liquidity(self.a, amount=3_000_000)
        self.assertEqual(self.storage['nextEventLiquidity'], 1_000_000)

        # running two events, in each should be added 1xtz:
        # TODO: this next line fails with "'Juster.getNextEventId view is not found'" Michelson runtime error
        self.create_event(event_line_id=0, next_event_id=0)
        self.create_event(event_line_id=1, next_event_id=1)

        # second provider adds the same amount of liquidity:
        self.deposit_liquidity(self.b, amount=3_000_000)
        self.assertEqual(self.storage['nextEventLiquidity'], 2_000_000)

        # running last event with 2xtz liquidity:
        self.create_event(event_line_id=2, next_event_id=2)

        self.wait(3600)

        # let first two events be profitable (+0.9 xtz):
        self.pay_reward(event_id=0, amount=1_900_000)
        self.assertEqual(self.storage['nextEventLiquidity'], 2_300_000)

        self.pay_reward(event_id=1, amount=1_900_000)
        self.assertEqual(self.storage['nextEventLiquidity'], 2_600_000)

        # and last one is not (-1.8 xtz):
        self.pay_reward(event_id=2, amount=200_000)
        self.assertEqual(self.storage['nextEventLiquidity'], 2_000_000)

        # TODO: looks like this logic can be exploitable:
        # when provider sees that there are event that profitable for aggregator
        # he can get into aggregator and then get shares cheaper that they are
        # will be right after event payReward called (arbitrague opportunity).
        # There are two ways to solve this:

        # 1) add fees for withdrawing liquidity in first K hours/days (the way plenty does)
        # 2) is it possible to record all activeEvents list to the provider position when he enters. And then when he leave: calculate and remove difference for all of the events he was not participated it?
        # 3) lock shares that are in provided liquidity and evaluate new provided liquidity (requires a lot of additional logic and might be impossible to implement)
        # - maybe some logic to acknowledge shares from events that was started?
        # - so provider enters, receive some shares from free liquidity and some `share_claims` that he can demand after event is complete? and some pool for entryLiquidity?

        # The second cycle both providers in place:
        self.create_event(event_line_id=0, next_event_id=3)
        self.create_event(event_line_id=1, next_event_id=4)
        self.create_event(event_line_id=2, next_event_id=5)

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

