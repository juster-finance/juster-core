import json
from deposit import Deposit
from agreement import Agreement
from lock import Lock
from pools import Pools
from exceptions import InvalidState


def reverse(pool):
    return 'against' if pool == 'for' else 'for'


class JusterB:

    @classmethod
    def new_with_deposit(cls, user, pool_for, pool_against):
        pools = Pools(pool_for, pool_against)
        amount = pools.max()
        deposit = Deposit(amount, amount, pools)
        jb = cls(
            pools=pools,
            total_shares=amount,
            is_claimed=False,
            agreements={},
            deposits={user: deposit},
            next_agreement_id=0,
            balances=0,
            locks={},
            next_lock_id=0,
            inflation=1
        )
        jb.balance_update(user, -amount)
        return jb

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
            inflation=1,
            tolerance=1e-8
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
        self.inflation = inflation
        self.tolerance = tolerance
        self.balancer_pool = Pools.empty()

    def get_deposit(self, user):
        return self.deposits.get(user, Deposit.empty())

    def balance_update(self, user, change):
        self.balances[user] = self.balances.get(user, 0) + change
        self.balances['contract'] = self.balances.get('contract', 0) - change
        if self.balances['contract'] < -self.tolerance:
            raise InvalidState('Negative amount on contract')

    def provide_liquidity(self, user, amount):
        deposit = Deposit(
            amount=amount,
            pools=self.pools.norm() * amount,
            shares=amount / self.pools.max() * self.total_shares
        )

        self.deposits[user] = self.get_deposit(user) + deposit
        self.pools += deposit.pools
        self.total_shares += deposit.shares
        self.balance_update(user, -deposit.amount)

    def insure(self, user, amount, pool):
        pool_to = pool
        pool_from = reverse(pool)

        ratio = self.pools.get(pool_from) / (self.pools.get(pool_to) + amount*self.inflation)
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
            inflation=self.inflation
            # unlock_time=self.time + self.duration
        )

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
        pools_for_deposit = lock.pools * deposit.shares / self.total_shares # / lock.inflation
        pools_profit = pools_for_deposit - deposit.pools

        # profit for first participant should be inflated by x4 and by second by self.inflation
        # -30 + (-3.75)
        profit = pools_profit.get(reverse(win_pool))
        # profit += self.balancer_pool.get(reverse(win_pool))
        # profit = pools_profit.dot_product(self.balancer_pool.reverse().norm())

        withdrawn_fraction = lock.shares / deposit.shares
        withdrawn_liquidity = (deposit.amount + profit) * withdrawn_fraction
        self.balance_update(lock.user, withdrawn_liquidity)
        self.deposits[lock.user] *= 1 - withdrawn_fraction
        self.total_shares -= lock.shares

    def claim_insurance_case(self):
        self.is_claimed = True

    def get_win_pool(self):
        return 'for' if self.is_claimed else 'against'

    def inflate(self, amount):
        """ Inflate/deflate pools by given amount
            self.inflation keeps inflation data to properly calculate
            provider rewards
        """

        total_liquidity = self.pools.max()
        added = amount / total_liquidity if total_liquidity != 0 else 1

        rate = 1 if total_liquidity == 0 else 1 + amount/total_liquidity
        # self.pools *= rate
        self.inflation /= rate

    def rebalance_pools(self):
        pass

    def give_reward(self, agreement_id):
        agreement = self.agreements.pop(agreement_id)

        if agreement.pool == self.get_win_pool():
            self.balance_update(agreement.user, agreement.amount + agreement.delta)
            removed_liquidity = agreement.delta + agreement.amount
            self.inflate(-removed_liquidity)
            self.balancer_pool.remove(agreement.pool, removed_liquidity)
        else:
            self.inflate(agreement.amount)
            self.balancer_pool.add(agreement.pool, agreement.amount)

        # TODO: assert self.pools.assert_positive()

    def to_dict(self):
        """ Returns all storage values in dict form """

        def values_to_dict(dct):
            return {k: v.to_dict() for k, v in dct.items()}

        return dict(
            pools=self.pools.to_dict(),
            total_shares=self.total_shares,
            is_claimed=self.is_claimed,
            agreements=values_to_dict(self.agreements),
            deposits=values_to_dict(self.deposits),
            locks=values_to_dict(self.locks),
            balances=self.balances
        )

    def __repr__(self):
        return (f'<Line>\n{json.dumps(self.to_dict(), indent=4)}')

    def assert_empty(self):
        assert abs(sum(self.balances.values())) < self.tolerance
        self.pools.assert_empty()
        assert abs(self.balances['contract']) < self.tolerance
        assert self.total_shares == 0
        assert len(self.agreements) == 0
        # TODO: assert all(deposit.is_empty() for deposit in self.deposits)

    def assert_balances_equal(self, balances):
        """ Checks all given balances dict that their values diffs less than
            tolerance value from the same keys in self.balances """

        diffs = {
            key: abs(self.balances.get(key, 0) - balances.get(key, 0))
            for key in balances
        }
        assert all(diff < self.tolerance for diff in diffs.values())

