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
            locked_pools=Pools.empty()
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
            locked_pools=Pools.empty()
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

        # TODO: maybe it is better to have self.available_pools as self.pools?
        available_pools = self.pools - self.locked_pools

        available_from = available_pools.get(pool_from)
        available_to = available_pools.get(pool_to)

        # should not allow insure if there are 0 available liquidity:
        assert available_from > 0
        assert available_to > 0

        ratio = available_from / (available_to + amount)
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

        # TODO: maybe there I need to use current pools instead of lock pools?
        # - I need to have a test to differentiate
        pools_cut = self.pools * shares / self.total_shares
        self.locked_pools += pools_cut

        lock = Lock(
            user=user,
            shares=shares,
            pools_cut=pools_cut,
            # unlock_time=self.time + self.duration
        )

        self.locks[self.next_lock_id] = lock
        self.next_lock_id += 1
        return self.next_lock_id - 1


    def withdraw_lock(self, lock_id):
        lock = self.locks.pop(lock_id)
        deposit = self.get_deposit(lock.user)
        lock_deposit = deposit * (lock.shares / deposit.shares)
        self.deposits[lock.user] -= lock_deposit

        # mixed approach: shares for pools and saved pools for revenues
        self.pools -= self.pools * lock.shares / self.total_shares
        self.locked_pools -= lock.pools_cut
        # TODO: or is it better to have lock_shares? instead of lock pools?
        self.total_shares -= lock.shares

        # TODO: who_win_at() add timestamp here and use lock.ulock_time
        win_pool = self.get_win_pool()

        # Profit calculates as:
        # [loosing pool shared cut] without [provided amount in lose pool]:
        win_profit = lock.pools_cut - lock_deposit.pools
        profit = win_profit.get(reverse(win_pool))

        self.balance_update(lock.user, lock_deposit.amount + profit)

    def claim_insurance_case(self):
        self.is_claimed = True

    '''
    def get_max_pool_name(self):
        return 'for' if self.pools['for'] > self.pools['against'] else 'against'
    '''

    def get_win_pool(self):
        return 'for' if self.is_claimed else 'against'

    def give_reward(self, agreement_id):
        agreement = self.agreements.pop(agreement_id)
        pool_to = agreement.pool
        pool_from = reverse(agreement.pool)

        # removing liquidity back:
        self.pools.remove(pool_to, agreement.amount)
        self.pools.add(pool_from, agreement.delta)

        # TODO: need to have some method to return actual pools?
        # TODO: maybe need to implement __add__ and __sub__ for pools?
        actual_pools = self.pools - self.locked_pools
        # TODO: assert actual_pools.assert_positive()
        max_pool = actual_pools.max()

        if agreement.pool == self.get_win_pool():
            # win case: get reward and decrease pools by agreement.delta
            shrink = (max_pool - agreement.delta) / max_pool
            self.balance_update(agreement.user, agreement.amount + agreement.delta)
        else:
            # lose case: increases pools by agreement.delta
            shrink = (max_pool + agreement.amount) / max_pool

        # TODO: need to update actual pools instead:
        # TODO: maybe I should use actual pools instead of sum of the pools
        self.pools = self.pools*shrink
        # OR:
        # self.pools = (self.pools - self.locked_pools)*shrink + self.locked_pools

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
        self.pools.assert_empty()

    def assert_balances_equal(self, balances, tolerance=1e-8):
        """ Checks all given balances dict that their values diffs less than
            tolerance value from the same keys in self.balances """

        diffs = {
            key: abs(self.balances.get(key, 0) - balances.get(key, 0))
            for key in balances
        }
        assert all(diff < tolerance for diff in diffs.values())

