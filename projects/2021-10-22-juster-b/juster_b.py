import json
from deposit import Deposit
from agreement import Agreement


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
            agreements=[],
            deposits={user: deposit}
        )

    def __init__(
            self,
            pool_for=0,
            pool_against=0,
            total_shares=0,
            is_claimed=False,
            agreements=None,
            deposits=None
        ):
        # TODO: add fee?

        self.pool_for = pool_for
        self.pool_against = pool_against
        self.total_shares = total_shares
        self.is_claimed = is_claimed
        self.agreements = agreements or []
        self.deposits = deposits or {}

    def get_deposit(self, user):
        return self.deposits.get(user, Deposit.empty())

    def add_deposit(self, user, deposit):
        self.deposits[user] = self.get_deposit(user) + deposit
        self.pool_for += deposit.provided_for
        self.pool_against += deposit.provided_against
        self.total_shares += deposit.shares

    def provide_liqudity(self, user, amount):
        max_pool = max(self.pool_for, self.pool_against)
        new_deposit = Deposit(
            deposited=amount,
            provided_for=self.pool_for / max_pool * amount,
            provided_against=self.pool_against / max_pool * amount,
            shares=amount/max_pool*self.total_shares
        )
        self.add_deposit(user, new_deposit)

    def insure(self, user, amount, pool):
        pool_to = self.pool_for if pool == 'for' else self.pool_against
        pool_from = self.pool_against if pool == 'for' else self.pool_for
        delta = pool_from/(pool_to + amount) * amount
        reward = amount + delta
        self.pool_for += amount if pool == 'for' else -delta
        self.pool_against += -delta if pool == 'for' else amount
        self.agreements.append(Agreement(user, pool, reward))

    def remove_liqudity(self, user, shares):
        # TODO: need to understand how to implement this
        pass

    def claim_insurance_case(self):
        self.storage['is_claimed'] = True

    def give_reward(self, agreement_id):
        pass

    def to_dict(self):
        """ Returns all storage values in dict form """

        return dict(
            pool_for=self.pool_for,
            pool_against=self.pool_against,
            total_shares=self.total_shares,
            is_claimed=self.is_claimed,
            agreements=[agreement.to_dict() for agreement in self.agreements],
            deposits={
                user: deposit.to_dict()
                for user, deposit in self.deposits.items()
            }
        )

    def __repr__(self):
        return (f'<Line>\n{json.dumps(self.to_dict(), indent=4)}')
