class Lock:
    def __init__(self, user, shares, pools):
        self.user = user
        self.shares = shares
        self.pools = pools

    def to_dict(self):
        return {
            'user': self.user,
            'win_for': self.shares,
            'win_against': self.pools
        }

