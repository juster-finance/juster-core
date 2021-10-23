import json


class Lock:
    def __init__(self, user, shares, for_pool_cut, against_pool_cut):
        self.user = user
        self.shares = shares
        self.for_pool_cut = for_pool_cut
        self.against_pool_cut = against_pool_cut

    def to_dict(self):
        return {
            'user': self.user,
            'shares': self.shares,
            'for_pool_cut': self.for_pool_cut,
            'against_pool_cut': self.against_pool_cut
        }

    def __repr__(self):
        return (f'<Lock>\n{json.dumps(self.to_dict(), indent=4)}')

