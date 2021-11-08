import json
from agreement import Agreement
from lock import Lock
from pools import Pools
from exceptions import InvalidState


def reverse(pool):
    return 'against' if pool == 'for' else 'for'


class JusterC:

    def __init__(
            self,
            pools=Pools.empty(),
            locked_pools=Pools.empty(),
            is_claimed=False,
            claimed_time=None,
            agreements=None,
            deposits=None,
            next_agreement_id=0,
            locks=None,
            balances=None,
            next_lock_id=0,
            tolerance=1e-8,
            duration=3600,
            inflation=1,
            total_shares=0,
            time=0
        ):
        # TODO: add fee?

        self.pools = pools
        self.locked_pools = locked_pools
        self.is_claimed = is_claimed
        self.claimed_time = claimed_time
        self.agreements = agreements or {}
        self.deposits = deposits or {}
        self.next_agreement_id = next_agreement_id
        self.locks = locks or {}
        self.balances = balances or {}
        self.next_lock_id = next_lock_id
        self.tolerance = tolerance
        self.inflation = inflation
        self.duration = duration
        self.time = time
        self.total_shares = total_shares

    def wait(self, seconds):
        self.time += seconds

    def balance_update(self, user, change):
        self.balances[user] = self.balances.get(user, 0) + change
        self.balances['contract'] = self.balances.get('contract', 0) - change
        if self.balances['contract'] < -self.tolerance:
            raise InvalidState('Negative amount on contract')

    def provide(self, user, amount_for, amount_against):
        """ provide liquidity from the `user`,
            with ratio f:a (for:against)
        """

        deposit = Pools(
            amount_for=amount_for,
            amount_against=amount_against
        )
        self.deposits[user] = self.deposits.get(user, Pools(0, 0)) + deposit

        inflated_deposit = deposit * self.inflation
        self.pools += inflated_deposit

        # TODO: is it possible to optimize liquidity and add only to the max pool?
        self.balance_update(user, -inflated_deposit.get('for'))
        self.balance_update(user, -inflated_deposit.get('against'))

    def add_agreement(self, agreement):
        """ Adds agreement to self.agreements, increased counter and returns
            added agreement id """

        agreement_id = self.next_agreement_id
        self.agreements[agreement_id] = agreement
        self.next_agreement_id += 1
        return agreement_id

    def insure(self, user, amount):
        ratio = self.pools.get('against') / (self.pools.get('for') + amount)
        delta = ratio * amount

        self.pools.remove('against', delta)
        self.balance_update(user, -amount)
        # TODO: insure MUST increase FOR pool to, otherwise two small insurances
        # will be better than one big:
        # - A places 100 to 100:100 ------ 100/200 * 100 = 50
        # - A places 50 twice to 100:100 - 100/150 * 50 + 100/200 * 50 = 58.33

        agreement = Agreement(
            user=user,
            amount=amount,
            delta=delta,
            remain_until=self.time + self.duration)

        return self.add_agreement(agreement)

    def add_lock(self, lock):
        """ Adds lock, increases counter, returns added lock id """

        lock_id = self.next_lock_id
        self.locks[lock_id] = lock
        self.next_lock_id += 1
        return lock_id

    def lock(self, provider, amount_for, amount_against):
        """ Locks liquidity to withdraw when lock period ended. Lock period
            equals to `duration` to ensure that all insurance claims that used
            provided liquidity are backed by amount till the end of the agreement
        """

        # Amounts should be provided in uniflated ratio
        # (as it saved in deposits ledger):
        deposit = Pools(
            amount_for=amount_for,
            amount_against=amount_against)
        self.deposits[provider] -= deposit
        self.deposits[provider].assert_positive()

        lock = Lock(
            provider=provider,
            deposit=deposit,
            # inflation should be calculated at the withdraw moment to add all profits that was agregated
            # BUT here is the problem: what if provider does not withdraw his lock and wait for more cases?
            # MAYBE this would be duty of other providers to kick this provider off?

            unlock_time=self.time + self.duration,
        )

        # Including profits:
        inflated_deposit = deposit * self.inflation

        self.pools -= inflated_deposit
        self.locked_pools += inflated_deposit

        return self.add_lock(lock)

    def is_claimed_at(self, claimed_time):
        assert self.claimed_time is not None
        return self.claimed_time < claimed_time

    def withdraw(self, lock_id):
        lock = self.locks.pop(lock_id)
        inflated_deposit = lock.deposit * self.inflation

        if not self.is_claimed:
            # provider WIN case:
            assert lock.unlock_time >= self.time

            self.locked_pools -= inflated_deposit
            self.locked_pools.assert_almost_positive()
            # TODO: need to understand, is it possible to make self.pool < 0 here?
            withdrawn_liquidity = inflated_deposit.sum()

        if self.is_claimed:
            # provider LOSE case:
            pools = self.pools + self.locked_pools
            share = inflated_deposit.get('for') / pools.get('for')
            splitted_against = share * pools.get('against')
            withdrawn_liquidity = inflated_deposit.get('for') + splitted_against

        self.balance_update(lock.provider, withdrawn_liquidity)

    def claim_insurance_case(self):
        self.is_claimed = True
        self.claimed_time = self.time

    def reward(self, agreement_id):
        assert self.is_claimed

        agreement = self.agreements.pop(agreement_id)
        self.balance_update(agreement.user, agreement.amount + agreement.delta)

    def dissolve(self, agreement_id):
        """ Distribiute provided agreement value between pools """

        agreement = self.agreements.pop(agreement_id)
        assert agreement.remain_until >= self.time

        if self.is_claimed:
            assert not self.is_claimed_at(agreement.remain_until)

        self.pools.add('against', agreement.delta)

        # MAYBE: to have some coefficient to split profits and part of the profits
        # should go to providers and another part should go directly to the AGAINST pool?
        # the current case is where this coef equal to ratio:

        # adding amount to pools:
        share = agreement.amount / (self.pools.sum() + self.locked_pools.sum())
        self.pools *= 1 + share
        self.locked_pools *= 1 + share
        self.inflation *= 1 + share

    def to_dict(self):
        """ Returns all storage values in dict form """

        def values_to_dict(dct):
            return {k: v.to_dict() for k, v in dct.items()}

        return dict(
            pools=self.pools.to_dict(),
            locked_pools=self.locked_pools.to_dict(),
            is_claimed=self.is_claimed,
            inflation=self.inflation,
            agreements=values_to_dict(self.agreements),
            deposits=values_to_dict(self.deposits),
            locks=values_to_dict(self.locks),
            balances=self.balances
        )

    def __repr__(self):
        return (f'<Line>\n{json.dumps(self.to_dict(), indent=4)}')

    def assert_empty(self):
        assert abs(sum(self.balances.values())) < self.tolerance
        # self.pools.assert_empty()
        assert abs(self.balances['contract']) < self.tolerance
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

