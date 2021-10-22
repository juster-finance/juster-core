class Agreement:
    def __init__(self, user, pool, amount, delta):
        self.user = user
        self.pool = pool
        self.amount = amount
        self.delta = delta

    def to_dict(self):
        return {
            'user': self.user,
            'pool': self.pool,
            'amount': self.amount,
            'delta': self.delta
        }

