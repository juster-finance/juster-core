from tests.interpret.pool.pool_base import PoolBaseTestCase


class DurationPointsTestCase(PoolBaseTestCase):
    def test_duration_points_calculation(self):
        # creating default event:
        self.add_line()

        # providing liquidity:
        provider = self.a
        self.level = 1
        self.deposit_liquidity(sender=provider, amount=30)
        self.approve_entry(entry_id=0)
        assert self.storage['durationPoints'][provider]['updateLevel'] == 1
        assert self.storage['durationPoints'][provider]['amount'] == 0
        assert self.storage['totalDurationPoints'] == 0

        # updates liquidity after 100 blocks, should have 30*100 DPs:
        self.level = 101
        self.claim_liquidity(provider=provider, shares=10)
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
