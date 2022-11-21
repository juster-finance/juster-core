from tests.interpret.pool.pool_base import PoolBaseTestCase


class DurationPointsTestCase(PoolBaseTestCase):
    def test_should_give_zero_duration_points_to_new_provider(self):
        # creating default event:
        self.add_line()

        # providing liquidity:
        provider = self.a
        entry_id = self.deposit_liquidity(sender=provider)
        self.level = 33
        self.approve_entry(entry_id=entry_id)
        assert self.storage['durationPoints'][provider]['updateLevel'] == 33
        assert self.storage['durationPoints'][provider]['amount'] == 0
        assert self.storage['totalDurationPoints'] == 0

    def test_duration_points_calculation(self):
        # creating default event:
        self.add_line()

        # providing liquidity:
        provider = self.a
        self.level = 1
        entry_id = self.deposit_liquidity(sender=provider, amount=30)
        self.approve_entry(entry_id=entry_id)

        # updates liquidity after 100 blocks, should have 30*100 DPs:
        self.level = 101
        entry_id = self.deposit_liquidity(sender=provider, amount=10)
        self.approve_entry(entry_id=entry_id)
        assert self.storage['durationPoints'][provider]['updateLevel'] == 101
        assert self.storage['durationPoints'][provider]['amount'] == 3_000

        # claims liquidity in the same block/level as approve, same DPs
        self.claim_liquidity(provider=provider, shares=20)
        assert self.storage['durationPoints'][provider]['updateLevel'] == 101
        assert self.storage['durationPoints'][provider]['amount'] == 3_000

        # updates liquidity again after 100 blocks, should have +20*100 DPs:
        self.level = 201
        self.claim_liquidity(provider=provider, shares=20)
        assert self.storage['durationPoints'][provider]['updateLevel'] == 201
        assert self.storage['durationPoints'][provider]['amount'] == 5_000

        # cals DPs recalc after 100 more blocks, should have same DPs:
        self.level = 301
        self.update_duration_points(provider=provider)
        assert self.storage['durationPoints'][provider]['updateLevel'] == 301
        assert self.storage['durationPoints'][provider]['amount'] == 5_000
        assert self.storage['totalDurationPoints'] == 5_000

    def test_should_allow_anyone_to_update_duration_points(self):
        # creating default event:
        self.add_line()

        # providing liquidity:
        provider = self.a
        entry_id = self.deposit_liquidity(sender=provider, amount=1)
        self.approve_entry(entry_id=entry_id)

        self.level += 100
        self.update_duration_points(sender=self.b, provider=provider)
        assert (
            self.storage['durationPoints'][provider]['updateLevel']
            == self.level
        )
        assert self.storage['durationPoints'][provider]['amount'] == 100
        assert self.storage['totalDurationPoints'] == 100
