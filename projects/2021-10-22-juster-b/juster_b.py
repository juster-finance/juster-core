import json
from deposit import Deposit
from agreement import Agreement
from lock import Lock


def reverse(pool):
    return 'against' if pool == 'for' else 'for'


class JusterB:

    @classmethod
    def new_with_deposit(cls, user, pool_for, pool_against):
        amount = max(pool_for, pool_against)
        deposit = Deposit(amount, pool_for, pool_against, amount)
        return cls(
            pool_for=pool_for,
            pool_against=pool_against,
            total_shares=amount,
            is_claimed=False,
            agreements={},
            deposits={user: deposit},
            next_agreement_id=0,
            balances={user: -amount},
            locks={},
            next_lock_id=0,
            lock_shares=0
        )

    def __init__(
            self,
            pool_for=0,
            pool_against=0,
            total_shares=0,
            is_claimed=False,
            agreements=None,
            deposits=None,
            next_agreement_id=0,
            balances=None,
            locks=None,
            next_lock_id=0,
            lock_shares=0
        ):
        # TODO: add fee?

        self.pools = {
            'for': pool_for,
            'against': pool_against
        }

        self.total_shares = total_shares
        self.is_claimed = is_claimed
        self.agreements = agreements or {}
        self.deposits = deposits or {}
        self.balances = balances or {}
        self.next_agreement_id = next_agreement_id
        self.locks = locks or {}
        self.next_lock_id = next_lock_id
        self.lock_shares = lock_shares

    def get_deposit(self, user):
        return self.deposits.get(user, Deposit.empty())

    def balance_update(self, user, change):
        self.balances[user] = self.balances.get(user, 0) + change

    def _add_deposit(self, user, deposit):
        # TODO: maybe recalculate for/against using shares?
        # and then maybe it would be possible to use within remove_liquidity
        self.deposits[user] = self.get_deposit(user) + deposit
        self.pools['for'] += deposit.pools['for']
        self.pools['against'] += deposit.pools['against']
        self.total_shares += deposit.shares
        self.balance_update(user, -deposit.deposited)

    def provide_liquidity(self, user, amount):
        max_pool = max(self.pools.values())
        new_deposit = Deposit(
            deposited=amount,
            provided_for=self.pools['for'] / max_pool * amount,
            provided_against=self.pools['against'] / max_pool * amount,
            shares=amount/max_pool*self.total_shares
        )
        self._add_deposit(user, new_deposit)

    def insure(self, user, amount, pool):
        pool_to = pool
        pool_from = reverse(pool)
        ratio = self.pools[ pool_from ] / (self.pools[ pool_to ] + amount)
        delta = ratio * amount

        self.pools[ pool_to ] += amount
        self.pools[ pool_from ] -= delta

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
            # win_for=lock_deposit.deposited + for_win_profit,
            # win_against=lock_deposit.deposited + against_win_profit,
            pools=self.pools
            # unlock_time=self.time + self.duration
        )

        self.lock_shares += shares

        # TODO: update lock_shares?
        self.locks[self.next_lock_id] = lock
        self.next_lock_id += 1
        return self.next_lock_id - 1


    def withdraw_lock(self, lock_id):
        lock = self.locks.pop(lock_id)
        deposit = self.get_deposit(lock.user)
        lock_deposit = deposit * (lock.shares / deposit.shares)
        self.deposits[lock.user] -= lock_deposit

        # TODO: maybe there I need to use current pools instead of lock pools?
        for_pool_cut = lock.pools['for'] * lock.shares / self.total_shares
        against_pool_cut = lock.pools['against'] * lock.shares / self.total_shares
        self.pools['for'] -= for_pool_cut
        self.pools['against'] -= against_pool_cut

        self.total_shares -= lock.shares
        self.lock_shares -= lock.shares

        # TODO: who_win_at() add timestamp here and use lock.ulock_time
        win_pool = self.get_win_pool()

        against_win_profit = for_pool_cut - lock_deposit.pools['for']
        for_win_profit = against_pool_cut - lock_deposit.pools['against']
        profit = for_win_profit if win_pool == 'for' else against_win_profit

        self.balance_update(lock.user, lock_deposit.deposited + profit)

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

        # max_pool = self.get_max_pool_name()

        # removing liquidity back:
        self.pools[ pool_to ] -= agreement.amount
        self.pools[ pool_from ] += agreement.delta
        max_pool = max(self.pools.values())

        if agreement.pool == self.get_win_pool():
            # win case: get reward and decrease pools by agreement.delta
            shrink = (max_pool - agreement.delta) / max_pool
            self.balance_update(agreement.user, agreement.amount + agreement.delta)
        else:
            # lose case: increases pools by agreement.delta
            shrink = (max_pool + agreement.amount) / max_pool

        self.pools['for'] = self.pools['for']*shrink
        self.pools['against'] = self.pools['against']*shrink

        # assert self.pools['for'] >= 0
        # assert self.pools['against'] >= 0

    def to_dict(self):
        """ Returns all storage values in dict form """

        def values_to_dict(dct):
            return {k: v.to_dict() for k, v in dct.items()}

        return dict(
            pool_for=self.pools['for'],
            pool_against=self.pools['against'],
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
        assert sum(self.balances.values()) < 1e-8
        assert sum(self.pools.values()) < 1e-8
        assert self.pools['for'] > -tolerance
        assert self.pools['against'] > -tolerance

