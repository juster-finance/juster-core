import json


class Agreement:
    def __init__(self, user, amount, delta, remain_until):
        self.user = user
        self.amount = amount
        self.delta = delta
        self.remain_until = remain_until

    def to_dict(self):
        return {
            'user': self.user,
            'amount': self.amount,
            'delta': self.delta,
            'remain_until': self.remain_until
        }

    def __repr__(self):
        return (f'<Agreement>\n{json.dumps(self.to_dict(), indent=4)}')

