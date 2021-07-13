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
