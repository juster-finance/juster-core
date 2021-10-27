import json


'''
class Lock:
    def __init__(self, user, shares, pools):
        self.user = user
        self.shares = shares
        self.pools = pools.copy()

    def to_dict(self):
        return {
            'user': self.user,
            'shares': self.shares,
            'pools': self.pools.to_dict()
        }

    def __repr__(self):
        return (f'<Lock>\n{json.dumps(self.to_dict(), indent=4)}')
'''


from container import Container

class Lock(Container):
    name = 'Lock'

