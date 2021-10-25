import json
from deposit import Deposit
from agreement import Agreement
from lock import Lock
from pools import Pools


def reverse(pool):
    return 'against' if pool == 'for' else 'for'


class JusterB:

    @classmethod
    def new_with_deposit(cls, user, pool_for, pool_against):
        # TODO: pool_for, pool_against -> pools<Pools>
        pools = Pools(pool_for, pool_against)
        amount = pools.max()
        deposit = Deposit(amount, amount, pools)
        return cls(
            pools=pools,
            total_shares=amount,
            is_claimed=False,
            agreements={},
            deposits={user: deposit},
            next_agreement_id=0,
            balances={user: -amount},
            locks={},
            next_lock_id=0,
            locked_pools=Pools.empty(),
            locked_shares=0
        )

    def __init__(
            self,
            pools=Pools.empty(),
            total_shares=0,
            is_claimed=False,
            agreements=None,
            deposits=None,
            next_agreement_id=0,
            balances=None,
            locks=None,
            next_lock_id=0,
            locked_pools=Pools.empty(),
            locked_shares=0
        ):
        # TODO: add fee?

        self.pools = pools
        self.total_shares = total_shares
        self.is_claimed = is_claimed
        self.agreements = agreements or {}
        self.deposits = deposits or {}
        self.balances = balances or {}
        self.next_agreement_id = next_agreement_id
        self.locks = locks or {}
        self.next_lock_id = next_lock_id
        self.locked_pools = locked_pools or {}
        self.locked_shares = locked_shares

    def get_deposit(self, user):
        return self.deposits.get(user, Deposit.empty())

    def balance_update(self, user, change):
        self.balances[user] = self.balances.get(user, 0) + change

    def _add_deposit(self, user, deposit):
        # TODO: maybe recalculate for/against using shares?
        # and then maybe it would be possible to use within remove_liquidity
        self.deposits[user] = self.get_deposit(user) + deposit
        self.pools += deposit.pools
        self.total_shares += deposit.shares
        self.balance_update(user, -deposit.amount)

    def provide_liquidity(self, user, amount):
        new_deposit = Deposit(
            amount=amount,
            pools=self.pools.norm() * amount,
            shares=amount / self.pools.max() * self.total_shares
        )
        self._add_deposit(user, new_deposit)

    def insure(self, user, amount, pool):
        pool_to = pool
        pool_from = reverse(pool)
        # actual_pools = self.pools * (1 - self.locked_shares / self.total_shares)

        ratio = self.pools.get(pool_from) / (self.pools.get(pool_to) + amount)
        delta = ratio * amount

        self.pools.add(pool_to, amount)
        self.pools.remove(pool_from, delta)

        agreement = Agreement(user, pool, amount, delta)
        self.agreements[self.next_agreement_id] = agreement
        self.next_agreement_id += 1
        self.balance_update(user, -amount)

        return self.next_agreement_id - 1

    def lock_liquidity(self, user, shares):
        # TODO: in contract it is required to check that shares < deposit.shares and save already locked amt

        lock = Lock(
            user=user,
            shares=shares,
            pools=self.pools,
            # unlock_time=self.time + self.duration
        )

        self.locked_shares += shares
        self.pools *= 1 - shares / self.total_shares

        self.locks[self.next_lock_id] = lock
        self.next_lock_id += 1
        return self.next_lock_id - 1


    def withdraw_lock(self, lock_id):
        lock = self.locks.pop(lock_id)
        deposit = self.get_deposit(lock.user)

        # TODO: who_win_at() add timestamp here and use lock.ulock_time
        win_pool = self.get_win_pool()

        # Profit calculates as:
        # [loosing pool shared cut] without [provided amount in lose pool]:
        pools_for_deposit = lock.pools * deposit.shares / self.total_shares
        pools_profit = pools_for_deposit - deposit.pools
        profit = pools_profit.get(reverse(win_pool))

        withdrawn_fraction = lock.shares / deposit.shares
        withdrawn_liquidity = (deposit.amount + profit) * withdrawn_fraction
        self.balance_update(lock.user, withdrawn_liquidity)
        self.deposits[lock.user] *= 1 - withdrawn_fraction
        # self.pools *= 1 - lock.shares / self.total_shares
        self.total_shares -= lock.shares
        self.locked_shares -= lock.shares

    def claim_insurance_case(self):
        self.is_claimed = True

    def get_win_pool(self):
        return 'for' if self.is_claimed else 'against'

    def give_reward(self, agreement_id):
        agreement = self.agreements.pop(agreement_id)

        if agreement.pool == self.get_win_pool():
            self.balance_update(agreement.user, agreement.amount + agreement.delta)

        # TODO: assert self.pools.assert_positive()

    def to_dict(self):
        """ Returns all storage values in dict form """

        def values_to_dict(dct):
            return {k: v.to_dict() for k, v in dct.items()}

        return dict(
            actual_pools=(self.pools - self.locked_pools).to_dict(),
            total_shares=self.total_shares,
            is_claimed=self.is_claimed,
            agreements=values_to_dict(self.agreements),
            deposits=values_to_dict(self.deposits),
            locks=values_to_dict(self.locks),
            balances=self.balances
        )

    def __repr__(self):
        return (f'<Line>\n{json.dumps(self.to_dict(), indent=4)}')

    def assert_empty(self, tolerance=1e-8):
        assert abs(sum(self.balances.values())) < 1e-8
        # self.pools.assert_empty()

    def assert_balances_equal(self, balances, tolerance=1e-8):
        """ Checks all given balances dict that their values diffs less than
            tolerance value from the same keys in self.balances """

        diffs = {
            key: abs(self.balances.get(key, 0) - balances.get(key, 0))
            for key in balances
        }
        assert all(diff < tolerance for diff in diffs.values())

