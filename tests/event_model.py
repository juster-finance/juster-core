from juster_base import JusterModel


# TODO: try to use this model in tests instead of Juster, all Juster methods can be included in this class

class EventModel:
    def __init__(self, fee=0, winning_pool='aboveEq', a=0, b=0, total_shares=0):
        self.juster = JusterModel()
        self.pool_a = a
        self.pool_b = b
        self.total_shares = total_shares
        self.fee = fee
        self.winning_pool = winning_pool
        self.diffs = {}
        self.shares = {}


    def provide_liquidity(self, user, amount, a=0, b=0):

        # NOTE: here I do not perform checking that provided ratio is valid
        # NOTE: provided a & b only make sense if there are empty pools
        a = self.pool_a if self.pool_a > 0 else a
        b = self.pool_b if self.pool_b > 0 else b

        provided_split = self.juster.calc_provide_liquidity_split(
            amount, a, b, self.total_shares)

        self.shares[user] = self.shares.get(user, 0) + provided_split['shares']
        self.pool_a += provided_split['provided_a']
        self.pool_b += provided_split['provided_b']
        self.total_shares += provided_split['shares']

        return self


    def bet(self, user, amount, pool, time):

        multiplier = self.juster.calc_liquidity_bonus_multiplier(time, 0, 1)
        is_above = pool == 'above_Eq'

        top = self.pool_b if is_above else self.pool_a
        bottom = self.pool_a if is_above else self.pool_b
        bet_profit = self.juster.calc_bet_return(top, bottom, amount, self.fee*multiplier)

        self.pool_a += amount if is_above else -bet_profit
        self.pool_b += -bet_profit if is_above else amount

        if pool == self.winning_pool:
            self.diffs[user] = self.diffs.get(user, 0) + bet_profit
            self.distribute_between_providers(-bet_profit)
        else:
            self.diffs[user] = self.diffs.get(user, 0) - amount
            self.distribute_between_providers(amount)

        # TODO: save event diffs history?
        return self


    def distribute_between_providers(self, amount):
        """ distributes profit/loss between liquidity providers """

        for provider, shares in self.shares.items():
            fraction = self.shares.get(provider, 0) / self.total_shares
            self.diffs[provider] = self.diffs.get(provider, 0) + fraction*amount


    def __repr__(self):
        return (f'<Event>\n{self.pool_a=}\n{self.pool_b=}\n{self.total_shares=}\n{self.fee=}'
            + f'\n{self.winning_pool=}\n{self.diffs=}\n{self.shares=}')


    @classmethod
    def from_storage(cls, storage, event_id, winning_pool):
        """ Creates exemplar of this class using contract storage data """

        event = storage['events'][event_id]
        fee_nat = event['liquidityPercent']
        fee = fee_nat / storage['liquidityPrecision']

        return EventModel(
            fee=fee,
            winning_pool=winning_pool,
            a=event['poolAboveEq'],
            b=event['poolBelow'],
            total_shares=event['totalLiquidityShares']
        )


    def __eq__(self, other):
        # TODO: check shares and diffs the same
        return all([
            self.pool_a == other.pool_a,
            self.pool_b == other.pool_b,
            self.total_shares == other.total_shares,
            self.fee == other.fee,
            self.winning_pool == other.winning_pool,
        ])


def event_model_tests():
    # TODO: make unit tests!

    # bet pool A win test:
    event = EventModel(fee=0.03, winning_pool='aboveEq', a=1_000_000, b=1_000_000)
    event.bet('user', 1_000_000, 'aboveEq', 0)
    assert event.diffs['user'] == 500_000
    assert event.pool_a == 500_000
    assert event.pool_b == 2_000_000

    # bet pool B win test:
    event = EventModel(fee=0, winning_pool='below', a=4_000_000, b=1_000_000)
    event.bet('user', 1_000_000, 'below', 1)
    assert event.diffs['user'] == 2_000_000
    assert event.pool_a == 2_000_000
    assert event.pool_b == 2_000_000

    # bet pool B lose test:
    event = EventModel(fee=0, winning_pool='aboveEq', a=2_000_000, b=1_000_000)
    event.bet('user', 1_000_000, 'below', 1)
    assert event.diffs['user'] == -1_000_000
    assert event.pool_a == 1_000_000
    assert event.pool_b == 2_000_000

    # provide liquidity test:
    event = EventModel(fee=0, winning_pool='aboveEq', a=1_000_000, b=1_000_000, total_shares=100)
    event.provide_liquidity('provider', 1_000_000)
    assert event.shares['provider'] == 100
    assert event.total_shares == 200
    assert event.pool_a == 2_000_000
    assert event.pool_b == 2_000_000

    event.bet('loser', 2_000_000, 'below', 1)
    assert event.pool_b == 4_000_000
    assert event.pool_a == 1_000_000
    assert event.diffs['loser'] == -2_000_000
    assert event.diffs['provider'] == 1_000_000

    # first provider test:
    event = EventModel(fee=0, winning_pool='aboveEq', total_shares=100)
    event.provide_liquidity('provider', 4_000_000, 4, 1)
    assert event.pool_a == 4_000_000
    assert event.pool_b == 1_000_000
    event.bet('loser', 0, 'below', 1)
    assert event.diffs['loser'] == 0
    assert event.diffs['provider'] == 0

    # bet with fee win test:
    event = EventModel(fee=0.2, winning_pool='aboveEq', a=1_000_000, b=1_000_000)
    event.bet('user', 1_000_000, 'aboveEq', 0.5)
    assert event.diffs['user'] == 450_000
    assert event.pool_a == 550_000
    assert event.pool_b == 2_000_000


    # TODO: test from_storage
    # TODO: test __eq__ with two same objects
    # TODO: test __eq__ with two different objects


event_model_tests()

