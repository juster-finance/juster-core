import json
from pools import Pools


class Deposit:
    def __init__(self, amount=0, shares=0, pools=Pools.empty()):
        self.amount = amount
        self.shares = shares

        # making copy of the pools there would be impossible to create two
        # objects with the same pools by the accident:
        self.pools = pools.copy()

    @classmethod
    def empty(cls):
        return cls(amount=0, shares=0, pools=Pools.empty())

    def to_dict(self):
        return {
            'amount': self.amount,
            'shares': self.shares,
            'pools': self.pools.to_dict(),
        }

    def __add__(self, other):
        return Deposit(
            amount=self.amount + other.amount,
            shares=self.shares + other.shares,
            pools=self.pools + other.pools
        )

    def __mul__(self, other):
        return Deposit(
            amount=other*self.amount,
            shares=other*self.shares,
            pools=other*self.pools
        )

    __rmul__ = __mul__

    def __neg__(self):
        return self * (-1)

    def __sub__(self, other):
        return self.__add__(other*(-1))

    def __repr__(self):
        return (f'<Deposit>\n{json.dumps(self.to_dict(), indent=4)}')

