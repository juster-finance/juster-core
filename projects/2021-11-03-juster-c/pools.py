import json


class Pools:
    def __init__(self, amount_for=0, amount_against=0, tolerance=1e-8):
        # TODO: maybe self.a, self.f -> to access pools?
        # TODO: maybe __init__(self, a=0, f=0): ?
        self.pools = {
            'for': amount_for,
            'against': amount_against
        }
        self.tolerance = tolerance

    def max(self):
        return max(self.pools.values())

    def min(self):
        return min(self.pools.values())

    def __add__(self, other):
        return Pools(
            amount_for=self.pools['for'] + other.pools['for'],
            amount_against=self.pools['against'] + other.pools['against']
        )

    @classmethod
    def empty(cls):
        return cls(amount_for=0, amount_against=0)

    def to_dict(self):
        return self.pools

    def __mul__(self, other):
        return Pools(
            amount_for=self.pools['for']*other,
            amount_against=self.pools['against']*other
        )

    __rmul__ = __mul__

    def __truediv__(self, other):
        return self * (1/other)

    def __sub__(self, other):
        return self.__add__(other*(-1))

    def __repr__(self):
        return (f'<Pools>\n{json.dumps(self.to_dict(), indent=4)}')

    def norm(self):
        return self / self.max()

    def assert_positive(self):
        assert self.pools['for'] >= 0
        assert self.pools['against'] >= 0

    def get(self, pool_name):
        return self.pools[pool_name]

    def add(self, pool_name, amount):
        self.pools[ pool_name ] += amount

    def remove(self, pool_name, amount):
        self.pools[ pool_name ] -= amount

    def is_empty(self):
        return abs(sum(self.pools.values())) < self.tolerance

    def assert_empty(self):
        assert self.is_empty()
        self.assert_positive()

    def __eq__(self, other):
        for_diff = abs(self.pools['for'] - other.pools['for'])
        against_diff = abs(self.pools['against'] - other.pools['against'])
        return (for_diff < self.tolerance) and (against_diff < self.tolerance)

    def copy(self):
        return Pools(
            amount_for=self.pools['for'],
            amount_against=self.pools['against'],
            tolerance=self.tolerance
        )

    def dot_product(self, other):
        return (
            self.pools['for'] * other.pools['for']
            + self.pools['against'] * other.pools['against'])

    def reverse(self):
        return Pools(
            amount_for=self.pools['against'],
            amount_against=self.pools['for'],
            tolerance=self.tolerance
        )

    def sum(self):
        return sum(self.pools.values())

