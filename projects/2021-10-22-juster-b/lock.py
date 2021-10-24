import json


class Lock:
    def __init__(self, user, shares, pools_cut):
        self.user = user
        self.shares = shares
        self.pools_cut = pools_cut.copy()

    def to_dict(self):
        return {
            'user': self.user,
            'shares': self.shares,
            'pools_cut': self.pools_cut.to_dict()
        }

    def __repr__(self):
        return (f'<Lock>\n{json.dumps(self.to_dict(), indent=4)}')

