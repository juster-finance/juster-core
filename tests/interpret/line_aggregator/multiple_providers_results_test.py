from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase


class MultipleProvidersResultsTestCase(LineAggregatorBaseTestCase):
    def test_provider_should_get_all_rewards_from_the_event(self):

        # TODO: this test show one of the problems: if all liquidity of the new
        # provider are goes to one event and there are a lot of events are
        # running, and then another provider decides to exit, it would get
        # alot more liquidity from this last event, than it should

        # Maybe it is required to have some pool of newly added liquidity?
        # so instead of bumping all liquidity from the new provider to the one
        # event, it would be splitted for max_active_events?

        # the worst case: new provider adds little amount of liquidity:
        # 1 xtz in pool, 9 xtz added, 9 + 0.1 xtz go to the last event, provider return 0.9*9.1 = 8.19
        # 9 xtz in pool, 1 xtz added, 0.9 + 1 xtz go to the last event, provider return 0.1*1.9 = 0.19
        # 99 xtz in pool, 1 xtz added, 9.9 + 1 xtz go in the last event, provider return 0.01*10.9 = 0.109

        # Solutions:
        # 1) having a liquidityLock list [] with length = maxActiveEvents - 1
        #   when new provider comes, he updates this list and adds some amounts
        #   that should not be used to the next several events. For example:
        #   provider adds 9 tez for max K=3 events, he creates lock : [6xtz, 3xtz]
        #   this means that in the next event -6xtz should be used and lock transforms to [3xtz]
        #   and in the next of the next -3xtz should be used and lock transforms to []
        #   the problem here is how to manage if provider decides to go out before his locks are finished
        #   the easiest solution is not allowing him to exit before K events created

        # 2) having nextEventLiquidity estimated value in the storage. After each new
        #   event finished: recalculate this value (for example if there are 10 events
        #   and event finished with 10xtz loss, then nextEventLiquidity should be reduced by
        #   1 xtz). When liquidity added: increase value by amount/maxActiveEvents.
        #   And use this calculation to provide liquidity for the next events.
        #   the problem here is that is is possible that in a row of loss events it would be
        #   not enough balance to create new line.
        #   the solution is to have reserve percent + ability to create event with less liquidity

        # creating default event:
        self.add_line(max_active_events=2)

        # providing liquidity:
        provided_amount = 10_000_000
        self.deposit_liquidity(self.a, amount=provided_amount)

        # creating event where provider have 100% of the liquidity:
        # as far as max_active_events is 2: this event should receive 5xtz:
        self.create_event(event_line_id=0, next_event_id=0)

        # second provider adds liquidity with the same amount:
        self.deposit_liquidity(self.b, amount=provided_amount)

        # should receive the same amount of shares:
        self.assertEqual(
            self.storage['positions'][0]['shares'],
            self.storage['positions'][1]['shares']
        )

        # creating next event, total liquidity 15xtz all goes to the second
        self.wait(3600)
        self.create_event(event_line_id=0, next_event_id=1)

        # providers decided to remove their liquidity:
        withdrawn_amount = self.claim_liquidity(
            self.a, position_id=0, shares=10_000_000)
        self.assertEqual(withdrawn_amount, 0)

        withdrawn_amount = self.claim_liquidity(
            self.b, position_id=1, shares=10_000_000)
        self.assertEqual(withdrawn_amount, 0)

        # first event is finished with profit 2xtz, all this 7xtz should go to
        # the first provider:
        self.pay_reward(event_id=0, amount=7_000_000)

        # second event finished with the same amount as it started
        self.wait(3600)
        self.pay_reward(event_id=1, amount=15_000_000)

        # first provider first event 100%:
        amount = self.withdraw_liquidity(
            positions=[dict(positionId=0, eventId=0)],
            sender=self.a)
        self.assertEqual(amount, 7_000_000)

        # second provider second event 50%:
        amount = self.withdraw_liquidity(
            positions=[dict(positionId=1, eventId=1)],
            sender=self.b)
        self.assertEqual(amount, 7_500_000)

        # first provider second event 50%:
        amount = self.withdraw_liquidity(
            positions=[dict(positionId=0, eventId=1)],
            sender=self.a)
        self.assertEqual(amount, 7_500_000)

