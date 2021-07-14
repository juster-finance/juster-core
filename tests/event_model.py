def calc_liquidity_bonus_multiplier(
        current_time, start_time, close_time):
    """ Returns multiplier that applied to reduce bets """

    return (current_time - start_time) / (close_time - start_time)


def calc_bet_return(top, bottom, amount, fee=0):
    """ Calculates the amount that would be returned if participant wins
        Not included the bet amount itself, only added value
    """

    ratio = top / (bottom + amount)
    return int(amount * ratio * (1-fee))
    

def select_event(ledger, event_id):
    """ Selects only those records that are belongs to the
        event_id, key is tuple: (participant_address, event_id) """

    return {
        key[0]: value for key, value in ledger.items()
        if key[1] == event_id
    }


def select_event_ledgers(storage, event_id):
    """ Returns ledgers for given event_id from contract storage """

    ledger_names = [
        'betsAboveEq',
        'betsBelow',
        'providedLiquidityAboveEq',
        'providedLiquidityBelow',
        'liquidityShares',
        'depositedBets'
    ]

    return {
        ledger_name: select_event(storage[ledger_name], event_id)
        for ledger_name in ledger_names
    }


def rename_ledgers(ledgers, winning_pool):
    """ Renames ledgers based on the given outcome """

    if winning_pool == 'aboveEq':
        ledgers['winLedger'] = ledgers.pop('betsAboveEq')
        ledgers['splitLedger'] = ledgers.pop('providedLiquidityBelow')

    elif winning_pool == 'below':
        ledgers['winLedger'] = ledgers.pop('betsBelow')
        ledgers['splitLedger'] = ledgers.pop('providedLiquidityAboveEq')

    else:
        raise Exception('wrong winning pool')

    return ledgers


def calculate_diff(user, ledgers, split_pool):
    """ Calculate profit/loss for given user and ledgers """

    win_amount = ledgers['winLedger'].get(user, 0)
    deposited_bets = ledgers['depositedBets'].get(user, 0)
    split_liquidity = ledgers['splitLedger'].get(user, 0)
    share = ledgers['liquidityShares'].get(user, 0)
    total_shares = sum(ledgers['liquidityShares'].values())

    bets_diff = win_amount - deposited_bets

    split_share = (0 if total_shares == 0 else
        split_pool * share / total_shares)

    liquidity_diff = split_share - split_liquidity

    return int(bets_diff + liquidity_diff)


def filter_non_zero(dct):
    return {k: v for k, v in dct.items() if v != 0}


def calculate_diffs(ledgers, split_pool):
    """ Calculates profit/loss for all participants
        - ledgers: all event ledgers with win/split names
        - split_pool: the loosed pool amount in event
    """

    participants = set(
        participant for ledger in ledgers.values()
        for participant in ledger)

    diffs = {
        user: calculate_diff(user, ledgers, split_pool)
        for user in participants
    }

    return diffs


class EventModel:
    share_precision = 100_000_000

    def __init__(self, fee=0, winning_pool='aboveEq', pool_a=0, pool_b=0,
        total_shares=0, shares=None, diffs=None):

        self.pool_a = pool_a
        self.pool_b = pool_b
        self.total_shares = total_shares
        self.fee = fee
        self.winning_pool = winning_pool
        self.diffs = (diffs or {}).copy()
        self.shares = (shares or {}).copy()


    def provide_liquidity(self, user, amount, pool_a=0, pool_b=0):

        # NOTE: here I do not perform checking that provided ratio is valid
        # NOTE: provided a & b only make sense if there are empty pools
        pool_a = self.pool_a if self.pool_a > 0 else pool_a
        pool_b = self.pool_b if self.pool_b > 0 else pool_b

        assert pool_a > 0
        assert pool_b > 0

        max_pool = max(pool_a, pool_b)
        shares = int(self.total_shares * amount / max_pool)
        shares = shares if self.total_shares > 0 else self.share_precision

        provided_a = int(amount * pool_a / max_pool)
        provided_b = int(amount * pool_b / max_pool)

        self.shares[user] = self.shares.get(user, 0) + shares
        self.pool_a += provided_a
        self.pool_b += provided_b
        self.total_shares += shares

        return self


    def bet(self, user, amount, pool, time):

        multiplier = calc_liquidity_bonus_multiplier(time, 0, 1)
        is_above = pool == 'aboveEq'

        top = self.pool_b if is_above else self.pool_a
        bottom = self.pool_a if is_above else self.pool_b
        bet_profit = calc_bet_return(top, bottom, amount, self.fee*multiplier)

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
        ledgers = select_event_ledgers(storage, event_id)
        ledgers = rename_ledgers(ledgers, winning_pool)
        split_pool = (event['poolBelow']
            if winning_pool == 'aboveEq' else event['poolAboveEq'])

        return EventModel(
            fee=fee,
            winning_pool=winning_pool,
            pool_a=event['poolAboveEq'],
            pool_b=event['poolBelow'],
            total_shares=event['totalLiquidityShares'],
            shares=ledgers['liquidityShares'],
            diffs=calculate_diffs(ledgers, split_pool)
        )


    def __eq__(self, other):

        return all([
            self.pool_a == other.pool_a,
            self.pool_b == other.pool_b,
            self.total_shares == other.total_shares,
            self.fee == other.fee,
            self.winning_pool == other.winning_pool,
            filter_non_zero(self.shares) == filter_non_zero(other.shares),
            filter_non_zero(self.diffs) == filter_non_zero(other.diffs)
        ])

