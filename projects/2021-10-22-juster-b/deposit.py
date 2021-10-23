import json


class Deposit:
    def __init__(self, deposited=0, provided_for=0, provided_against=0, shares=0):
        self.deposited = deposited
        self.pools = {
            'for': provided_for,
            'against': provided_against
        }
        self.shares = shares

    @classmethod
    def empty(cls):
        return cls(deposited=0, provided_for=0, provided_against=0, shares=0)

    def to_dict(self):
        return {
            'deposited': self.deposited,
            'provided_for': self.pools['for'],
            'provided_against': self.pools['against'],
            'shares': self.shares
        }

    def __add__(self, other):
        return Deposit(
            deposited=self.deposited + other.deposited,
            provided_for=self.pools['for'] + other.pools['for'],
            provided_against=self.pools['against'] + other.pools['against'],
            shares=self.shares + other.shares
        )

    def __mul__(self, other):
        return Deposit(
            deposited=other*self.deposited,
            provided_for=other*self.pools['for'],
            provided_against=other*self.pools['against'],
            shares=other*self.shares
        )

    __rmul__ = __mul__

    def __neg__(self):
        return self * (-1)

    def __sub__(self, other):
        return self.__add__(other*(-1))

    def __repr__(self):
        return (f'<Deposit>\n{json.dumps(self.to_dict(), indent=4)}')

