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
            claimed_time=None,
            agreements={},
            deposits={user: deposit},
            next_agreement_id=0,
            balances=0,
            locks={},
            next_lock_id=0,
            duration=3600,
            time=0
        )
        jb.balance_update(user, -amount)
        return jb

    def __init__(
            self,
            pools=Pools.empty(),
            total_shares=0,
            is_claimed=False,
            claimed_time=None,
            agreements=None,
            deposits=None,
            next_agreement_id=0,
            balances=None,
            locks=None,
            next_lock_id=0,
            tolerance=1e-8,
            duration=3600,
            time=0
        ):
        # TODO: add fee?

        self.pools = pools
        self.total_shares = total_shares
        self.is_claimed = is_claimed
        self.claimed_time = claimed_time
        self.agreements = agreements or {}
        self.deposits = deposits or {}
        self.balances = balances or {}
        self.next_agreement_id = next_agreement_id
        self.locks = locks or {}
        self.next_lock_id = next_lock_id
        self.tolerance = tolerance
        self.duration = duration
        self.time = time

    def wait(self, seconds):
        self.time += seconds

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

        ratio = self.pools.get(pool_from) / (self.pools.get(pool_to) + amount)
        delta = ratio * amount

        self.pools.add(pool_to, amount)
        self.pools.remove(pool_from, delta)

        # TODO: add `remain_until` variable in agreement
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
            unlock_time=self.time + self.duration
        )

        self.pools *= 1 - shares / self.total_shares

        self.locks[self.next_lock_id] = lock
        self.next_lock_id += 1
        return self.next_lock_id - 1


    def is_claimed_at(self, claimed_time):
        assert self.claimed_time is not None
        # TODO: return self.claimed_time < claimed_time
        return False


    def withdraw_lock(self, lock_id):
        lock = self.locks.pop(lock_id)
        deposit = self.get_deposit(lock.user)

        # TODO: maybe good to have who_win_at() add timestamp here and use lock.ulock_time
        # win_pool = self.get_win_pool()

        if not self.is_claimed_at(lock.unlock_time):
            # then profit calculates the way juster calculates it:
            # [loosing pool shared cut] without [provided amount in lose pool]:

            pools_for_deposit = lock.pools * deposit.shares / self.total_shares
            pools_profit = pools_for_deposit - deposit.pools
            profit = pools_profit.get('for')

            withdrawn_fraction = lock.shares / deposit.shares
            withdrawn_liquidity = (deposit.amount + profit) * withdrawn_fraction

        if self.is_claimed_at(lock.unlock_time):
            # waiting untill all participants claim their rewards (in contract
            # we allow anyone to call give_reward)
            assert len(self.agreements) == 0

            # TODO: find a way hot to handle unclaimed withdrawals that was
            # finished before claim and was not withdrawn

            # TODO: assert that there are no locks that have
            # lock.unlock_time < self.claimed_time (how?)

            # Finally: split all that left according to the shares
            # TODO: how calculate what left?

            # TODO: and the baddest question: is it possible to use liquidty from
            # other participants? because it looks like not. Then it is crushing
            # this idea to inflation pools (and I don't like this)

            # So: the test is already there, what happens if one participant
            # votes against event, then someone used his vote as liquidity, the
            # first wins before claim and get his liquidity back and then there
            # is not liquidity to pay back for the second. SAD

        self.balance_update(lock.user, withdrawn_liquidity)
        self.deposits[lock.user] *= 1 - withdrawn_fraction
        self.total_shares -= lock.shares

    def claim_insurance_case(self):
        # TODO: in the contract time / block level of the claim should be recorded
        # and only agreements that finished after this time should be considered
        # as winning for
        self.is_claimed = True
        self.claimed_time = self.time


    def get_win_pool(self):
        return 'for' if self.is_claimed else 'against'

    def rebalance_pools(self):
        pass

    def give_reward(self, agreement_id):
        agreement = self.agreements.pop(agreement_id)

        if agreement.pool == self.get_win_pool():
            self.balance_update(agreement.user, agreement.amount + agreement.delta)

        self.pools.assert_positive()

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
        assert all(deposit.is_empty() for deposit in self.deposits.values())

    def assert_balances_equal(self, balances):
        """ Checks all given balances dict that their values diffs less than
            tolerance value from the same keys in self.balances """

        diffs = {
            key: abs(self.balances.get(key, 0) - balances.get(key, 0))
            for key in balances
        }
        assert all(diff < self.tolerance for diff in diffs.values())

