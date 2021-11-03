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

        self.pools += deposit

        # Normalizing deposit by current profit inflation ratio:
        # (to make all providers on the one scale, if there are some profits)
        norm_deposit = deposit / self.inflation
        self.deposits[user] = self.deposits.get(user, Pools(0, 0)) + norm_deposit

        # TODO: maybe this is possible to manage this inside for pool?
        self.total_shares += norm_deposit.get('for')

        # TODO: is it possible to optimize liquidity and add only to the max pool?
        self.balance_update(user, -amount_for)
        self.balance_update(user, -amount_against)

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

        # REMOVE: user should not add liquidity to for pool!
        # self.pools.add('for', amount)
        self.pools.remove('against', delta)
        self.balance_update(user, -amount)

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

        # TODO: assert that both pools in deposit < user deposit pools in ldgr

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

        # looks like it is not required to remove this inflated deposit if self.is_claimed
        # BUT: what if self.claimed during locked deposit?
        # TODO: need to have a test for this case
        if not self.is_claimed:
            self.pools -= inflated_deposit

        return self.add_lock(lock)

    def is_claimed_at(self, claimed_time):
        assert self.claimed_time is not None
        return self.claimed_time < claimed_time

    def withdraw(self, lock_id):
        lock = self.locks.pop(lock_id)

        # deposit = self.deposits[lock.provider]
        inflated_deposit = lock.deposit * self.inflation

        # if not self.is_claimed_at(lock.unlock_time):
        if not self.is_claimed:
            # provider WIN case:
            assert lock.unlock_time >= self.time

            self.pools -= inflated_deposit
            # TODO: is it possible to make self.pool < 0 here?
            self.pools.assert_positive()
            withdrawn_liquidity = inflated_deposit.sum()

        # if self.is_claimed_at(lock.unlock_time):
        if self.is_claimed:
            # provider LOSE case:

            # TODO: what if provider losed after lock? Looks like he should
            # return his liquidity back to the self.pools before share calculation, is it?

            # share = inflated_deposit.get('for') / self.total_shares

            # TODO: would it be correct if current pools would be saved in lock and provider
            # will calculate his return using those pools data?

            share = inflated_deposit.get('for') / self.pools.get('for')
            splitted_against = share * self.pools.get('against')
            withdrawn_liquidity = inflated_deposit.get('for') + splitted_against

        # TODO: do I need to have this total_shares or self.pools:for is enough?
        # self.total_shares -= lock.deposit.get('for')
        self.balance_update(lock.provider, withdrawn_liquidity)
        self.deposits[lock.provider] -= lock.deposit

    def claim_insurance_case(self):
        # TODO: in the contract time / block level of the claim should be recorded
        # and only agreements that finished after this time should be considered
        # as winning for
        self.is_claimed = True
        self.claimed_time = self.time

    def reward(self, agreement_id):
        assert self.is_claimed

        agreement = self.agreements.pop(agreement_id)
        self.balance_update(agreement.user, agreement.amount + agreement.delta)

        # No pools change are hapenning because this is the end of the insurance line:
        '''
        self.pools.remove('for', agreement.amount)
        self.pools.add('against', agreement.delta)

        # removing delta from pools:
        share = agreement.delta / self.pools.sum()
        self.pools *= 1 - share
        self.inflation *= 1 - share
        self.pools.assert_positive()
        '''

    def dissolve(self, agreement_id):
        """ Distribiute provided agreement value between pools """

        agreement = self.agreements.pop(agreement_id)
        assert agreement.remain_until >= self.time

        if self.is_claimed:
            assert not self.is_claimed_at(agreement.remain_until)

        # REMOVE: as far as user not added liquidity to pool, he should not remove it:
        # self.pools.remove('for', agreement.amount)
        self.pools.add('against', agreement.delta)

        # adding amount to pools:
        share = agreement.amount / self.pools.sum()
        self.pools *= 1 + share
        self.inflation *= 1 + share
        self.pools.assert_positive()

    def to_dict(self):
        """ Returns all storage values in dict form """

        def values_to_dict(dct):
            return {k: v.to_dict() for k, v in dct.items()}

        return dict(
            pools=self.pools.to_dict(),
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
        # assert self.total_shares == 0
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

