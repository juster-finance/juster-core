from pools import Pools
import json


class Deposit:
    def __init__(self, pools, entry_inflation):
        self.pools = pools
        self.entry_inflation = entry_inflation

    def to_dict(self):
        return {
            'pools': self.pools.to_dict(),
            'entry_inflation': self.entry_inflation,
        }

    @classmethod
    def empty(cls):
        return cls(pools=Pools(0, 0), entry_inflation=1)

    def __repr__(self):
        return (f'<Deposit>\n{json.dumps(self.to_dict(), indent=4)}')


