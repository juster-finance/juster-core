from tests.interpret.pool.pool_base import PoolBaseTestCase


class MultipleProvidersResultsTestCase(PoolBaseTestCase):
    def test_provider_should_get_all_rewards_from_the_event(self):

        # creating default event:
        self.add_line(max_events=2)

        # providing liquidity:
        provided_amount = 10_000_000
        self.deposit_liquidity(self.a, amount=provided_amount)
        provider_one = self.approve_entry(self.a, entry_id=0)

        # creating event where provider have 100% of the liquidity:
        # as far as max_events is 2: this event should receive 5xtz:
        self.create_event(line_id=0, next_event_id=0)

        # second provider adds liquidity with the same amount:
        self.deposit_liquidity(self.b, amount=provided_amount)
        provider_two = self.approve_entry(self.a, entry_id=1)

        # should receive the same amount of shares:
        self.assertEqual(
            self.storage['shares'][provider_one],
            self.storage['shares'][provider_two],
        )

        # creating next event, total liquidity 20xtz (5xtz kept on contract)
        self.wait(3600)
        self.create_event(line_id=0, next_event_id=1)

        # providers decided to remove their liquidity:
        withdrawn_amount = self.claim_liquidity(
            self.a, provider=provider_one, shares=10_000_000
        )

        # as far as there is 5 xtz on the contract, first provider gets 50% of
        # free liquidity:
        self.assertEqual(withdrawn_amount, 2_500_000)

        withdrawn_amount = self.claim_liquidity(
            self.b, provider=provider_two, shares=10_000_000
        )
        self.assertEqual(withdrawn_amount, 2_500_000)

        # first event is finished with profit 2xtz, and this 7xtz should be
        # distributed between both providers:
        self.pay_reward(event_id=0, amount=7_000_000)

        # second event finished with the same amount as it started
        self.wait(3600)
        self.pay_reward(event_id=1, amount=10_000_000)

        # both providers receive the same amount of event results:
        claims = [
            dict(provider=provider_one, eventId=0),
            dict(provider=provider_two, eventId=0),
        ]

        amounts = self.withdraw_claims(claims=claims, sender=self.a)
        self.assertEqual(amounts[self.a], 3_500_000)
        self.assertEqual(amounts[self.b], 3_500_000)

        claims = [
            dict(provider=provider_one, eventId=1),
            dict(provider=provider_two, eventId=1),
        ]
        amounts = self.withdraw_claims(claims=claims, sender=self.b)
        self.assertEqual(amounts[self.a], 5_000_000)
        self.assertEqual(amounts[self.b], 5_000_000)
