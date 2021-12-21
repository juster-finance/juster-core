from tests.interpret.line_aggregator.line_aggregator_base import LineAggregatorBaseTestCase


class MultipleProvidersResultsTestCase(LineAggregatorBaseTestCase):
    def test_provider_should_get_all_rewards_from_the_event(self):

        # creating default event:
        self.add_line(max_active_events=2)

        # providing liquidity:
        provided_amount = 10_000_000
        self.deposit_liquidity(self.a, amount=provided_amount)
        self.approve_liquidity(self.a, entry_position_id=0)

        # creating event where provider have 100% of the liquidity:
        # as far as max_active_events is 2: this event should receive 5xtz:
        self.create_event(event_line_id=0, next_event_id=0)

        # second provider adds liquidity with the same amount:
        self.deposit_liquidity(self.b, amount=provided_amount)
        self.approve_liquidity(self.a, entry_position_id=1)

        # should receive the same amount of shares:
        self.assertEqual(
            self.storage['positions'][0]['shares'],
            self.storage['positions'][1]['shares']
        )

        # creating next event, total liquidity 10xtz (5xtz kept on contract)
        self.wait(3600)
        self.create_event(event_line_id=0, next_event_id=1)

        # providers decided to remove their liquidity:
        withdrawn_amount = self.claim_liquidity(
            self.a, position_id=0, shares=10_000_000)
        self.assertEqual(withdrawn_amount, 0)

        withdrawn_amount = self.claim_liquidity(
            self.b, position_id=1, shares=10_000_000)
        self.assertEqual(withdrawn_amount, 5_000_000)

        # first event is finished with profit 2xtz, all this 7xtz should go to
        # the first provider:
        self.pay_reward(event_id=0, amount=7_000_000)

        # second event finished with the same amount as it started
        self.wait(3600)
        self.pay_reward(event_id=1, amount=10_000_000)

        # first provider first event 100%:
        amount = self.withdraw_liquidity(
            positions=[dict(positionId=0, eventId=0)],
            sender=self.a)
        self.assertEqual(amount, 7_000_000)

        # second provider second event 50%:
        amount = self.withdraw_liquidity(
            positions=[dict(positionId=1, eventId=1)],
            sender=self.b)
        self.assertEqual(amount, 5_000_000)

        # first provider second event 50%:
        amount = self.withdraw_liquidity(
            positions=[dict(positionId=0, eventId=1)],
            sender=self.a)
        self.assertEqual(amount, 5_000_000)

