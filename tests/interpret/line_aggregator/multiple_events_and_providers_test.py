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
        self.create_event(0)
        self.create_event(1)

        # second provider adds the same amount of liquidity:
        self.deposit_liquidity(self.a, amount=3_000_000)

        # running last event with 4xtz liquidity:
        self.create_event(2)

        self.wait(3600)

        # let first two events be profitable and last not:
        self.pay_reward(0, 2_000_000)
        self.pay_reward(1, 2_000_000)
        self.pay_reward(2, 2_000_000)

        import pdb; pdb.set_trace()
        # So A should get all the profit from 0 and 1 (+2xtz)
        # and pay for the last event 50% (-1xtz)

        # B should pay for the last event 50% (-1xtz)

        # TODO: looks like this logic would not work here
        # it can be exploitable, when provider sees that there are event that
        # profitable for providers he can get into aggregator and then get shares
        # cheaper that they are

        # solutions? 1) keep as it is and exploit
        # 2) recalculate share price each time pay_reward is called (but is it possible?)
        # 3) lock shares that are in provided liquidity and evaluate new provided liquidity
        # according to the unknown price of locked shares (looks impossible)

        '''
        # removing liquidity:
        withdrawn_amount = self.claim_liquidity(
            self.a, position_id=0, shares=provided_amount)

        # checking that line_aggregator contract balance not changed
        self.assertEqual(withdrawn_amount, provided_amount)
        '''

