from tests.interpret.pool.pool_base import PoolBaseTestCase


class ProviderInAndOutTestCase(PoolBaseTestCase):
    def test_provider_should_have_the_same_shares_if_decided_to_reenter(self):

        # creating default event:
        self.add_line(max_events=10)

        # providing liquidity:
        provided_amount = 80_000_000
        entry_id = self.deposit_liquidity(self.a, amount=provided_amount)
        provider_one = self.approve_entry(self.a, entry_id=entry_id)

        # creating 9 events:
        for next_event_id in range(9):
            self.create_event(line_id=0, next_event_id=next_event_id)
            self.wait(3600)

        # second provider adds some liquidity with 20% shares:
        entry_id = self.deposit_liquidity(self.b, amount=20_000_000)
        provider_two = self.approve_entry(self.a, entry_id=entry_id)

        # creating 10th event: 8xtz + 2xtz should be provided:
        self.create_event(line_id=0, next_event_id=9)

        # A decided to remove liquidity and then redeposit it back:
        withdrawn_amount = self.claim_liquidity(
            self.a, provider=provider_one, shares=80_000_000
        )
        # free liquidity is 18 xtz (0 xtz from A and 18 xtz from B)
        # A receives claims for all events + 80% of free liquidity:
        self.assertEqual(withdrawn_amount, 14_400_000)
        # so A exchanges 20% of his 9 events for 14.4 xtz (20% * 72 xtz)

        entry_id = self.deposit_liquidity(self.c, amount=provided_amount)
        provider_three = self.approve_entry(self.c, entry_id=entry_id)

        # should receive the same amount of shares:
        self.assertEqual(
            self.storage['shares'][provider_three], provided_amount
        )
        self.assertEqual(self.storage['totalShares'], 100_000_000)
        self.assertEqual(self.get_next_liquidity(), 10_000_000)
