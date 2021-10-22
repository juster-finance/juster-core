class Deposit:
    def __init__(self, deposited=0, provided_for=0, provided_against=0, shares=0):
        self.deposited = deposited
        self.provided_for = provided_for
        self.provided_against = provided_against
        self.shares = shares

    @classmethod
    def empty(cls):
        return cls(deposited=0, provided_for=0, provided_against=0, shares=0)

    def to_dict(self):
        return {
            'deposited': self.deposited,
            'provided_for': self.provided_for,
            'provided_against': self.provided_against,
            'shares': self.shares
        }

    def __add__(self, other):
        return Deposit(
            deposited=self.deposited + other.deposited,
            provided_for=self.provided_for + other.provided_for,
            provided_against=self.provided_against + other.provided_against,
            shares=self.shares + other.shares
        )

