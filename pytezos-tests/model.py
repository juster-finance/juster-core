""" Model with helpers, used to calculate different logic
    implemented in contract """


class JusterModel:
    share_precision = 100_000_000

    def __init__(self):
        pass

    def calc_provide_liquidity_split(
        self, provided_amount, pool_a, pool_b, total_shares):

        assert pool_a > 0
        assert pool_b > 0

        max_pool = max(pool_a, pool_b)
        shares = int(total_shares * provided_amount / max_pool)
        shares = shares if total_shares > 0 else self.share_precision

        return {
            'provided_a': int(provided_amount * pool_a / max_pool),
            'provided_b': int(provided_amount * pool_b / max_pool),
            'shares': shares
        }


    def calc_liquidity_bonus_multiplier(
            self, current_time, start_time, close_time):
        """ Returns multiplier that applied to reduce bets """

        return (current_time - start_time) / (close_time - start_time)


    def calc_bet_return(self, top, bottom, amount, fee=0):
        """ Calculates the amount that would be returned if participant wins
            Not included the bet amount itself, only added value
        """

        ratio = top / (bottom + amount)
        return int(amount * ratio * (1-fee))


    def calc_bet_params_change(
            self, storage, event_id, participant, bet, amount, current_time):

        """ Returns dict with differences that caused
            by adding new bet to event
        """
        # TODO: I don't like that this is very bounded with storage/event
        # structures

        event = storage['events'][event_id]
        fee = event['liquidityPercent'] / storage['liquidityPrecision']

        close_time = event['betsCloseTime']
        start_time = event['createdTime']

        fee *= self.calc_liquidity_bonus_multiplier(
            current_time, start_time, close_time)
        key = (participant, event_id)

        if bet == 'aboveEq':
            top = event['poolBelow']
            bottom = event['poolAboveEq']
            above_eq_count = 0 if key in storage['betsAboveEq'] else 1
            bet_profit = self.calc_bet_return(top, bottom, amount, fee)

            return dict(
                bet_profit=bet_profit,
                diff_above_eq=amount,
                diff_below=-bet_profit,
                above_eq_count=above_eq_count,
                below_count=0
            )

        elif bet == 'below':
            top = event['poolAboveEq']
            bottom = event['poolBelow']
            below_count = 0 if key in storage['betsBelow'] else 1
            bet_profit = self.calc_bet_return(top, bottom, amount, fee)

            return dict(
                bet_profit=bet_profit,
                diff_above_eq=-bet_profit,
                diff_below=amount,
                above_eq_count=0,
                below_count=below_count
            )

        else:
            raise Exception('Wrong bet type')
