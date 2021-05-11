""" Event: XTZ-USD dynamics would be > 1 in 1 hour after betting period of 1 hour.
    Liquidity pool 1%

    Three participants: a, b and c making next interactions:
    (1) participant A adds initial liquidity at the beginning: 2tez with ratio 1:1
        TODO: assert firstProviderForSharesSum is correct (is changed and value good)
        TODO: assert firstProviderAgainstSharesSum is correct (is changed and value good)
        TODO: assert totalLiquidityForSharesSum is correct
        TODO: assert totalLiquidityAgainstSharesSum is correct
        TODO: assert totalLiquidityForSharesSum/firstProviderForSharesSum == 1
        TODO: assert totalLiquidityAgainstSharesSum/firstProviderAgainstSharesSum == 1
        TODO: assert winForProfitLossPerShareAtEntry for (a, 0) is equal to 0
        TODO: assert winAgainstProfitLossPerShareAtEntry for (a, 0) is equal to 0
        TODO: check result integrity (!)
                                               +30m
                                     A.LP B.F  A.LP C.LP D.A  B.F  A.LP
                                     (1)  (2)  (3)  (4)  (5)  (6)  (7)
    betsAgainstLiquidityPoolSum:     1.0  0.5  1.0  2.0  4.0  2.0  2.5
    betsForLiquidityPoolSum:         1.0  2.0  4.0  8.0  4.0  8.0 10.0
    firstProviderAgainstSharesSum:   1.0   -    -    -    -    -    -
    firstProviderForSharesSum:       1.0   -    -    -    -    -    -

    totalLiquidityAgainstSharesSum:  1.0  1.0  1.25 1.75 1.75 1.75 2.0
        - diff                       1.0  0.0  0.25 0.5  0.0  0.0  0.25
  
    totalLiquidityForSharesSum:      1.0  1.0  2.0  4.0  4.0  4.0  5.0
        - diff                       1.0  0.0  1.0  2.0  0.0  0.0  1.0

    winAgainstProfitLossPerShare:      0  1.0  1.0  1.0 -3.0  1.0  1.0
        - diff                         0  1.0   -    -  -4.0  4.0   -
        - diff corrected by LFor       0  1.0  0.0  0.0 -1.0  1.0  0.0

    winForProfitLossPerShare:          0 -0.5 -0.5 -0.5  1.5 -0.5 -0.5
        - diff                         0 -0.5   -    -   2.0 -2.0   -


    (2) participant B bets FOR 1tez
        - new ratio: 0.5:2
        TODO: assert that winForProfitLossPerShare is correct (equal to -1.5tez)
        TODO: assert that winAgainstProfitLossPerShare is correct (equal to +1tez)
        TODO: assert that ratio is correct 0.5:2
        TODO: assert that bet recorded in depositedBets

    (3) participant A adds more liquidity: 2.5tez with ratio 1:4, after 30 mins
        TODO: assert firstProviderForSharesSum is not changed
        TODO: assert firstProviderAgainstSharesSum is not changed
        TODO: assert totalLiquidityForSharesSum is correct 2tez + 0.5tez
        TODO: assert totalLiquidityAgainstSharesSum is correct 2tez + 1.5tez
        TODO: assert winForProfitLossPerShareAtEntry for -1.5tez
        TODO: assert winAgainstProfitLossPerShareAtEntry for +1tez

    (4) participant C adds more liquidity: 5tez with ratio 1:4, after 30 mins
        TODO: make that all prev asserts works

    (5) participant D bets AGAINST for 2tez
    (6) participant B bets FOR 4tez
    (7) participant A adds more liquidity 5tez

    Result: betAgainst win
        - A: get liquidity bonus:
            (1) get 100% of first B bet: + 1.0
            (2) loose x% of D bet: -2.0 * 99%
            (3) get x% of second B bet: +2.0
            (4) returns all provided liquidity in the end: 9.5tez
                --- +10.52tez
        - B: loose 5 tez (returns 0)
        - C: get liquidity bonus:
            (5) looses to participant D: -2.0 * 99%
            (6) get x% of second B bet: +2.0
            (7) returns liquidity: 5tez
                --- +5.02tez
        - D: wins 4*99% tez: 2 + 3.96

            10.52 + 0 + 5.02 + 5.96
        - total 21.5 tez

        TODO: check withdrawals successfull
        TODO: add balance to contract model (to self.balance) and keep tracking it
    
        TODO: this test should check that Ev of the participants at the add liquidity moment is zero
"""

from state_transformation_base import StateTransformationBaseTest, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class MultipleLPDeterminedTest(StateTransformationBaseTest):

    def test_with_multiple_providers(self):

        self.current_time = RUN_TIME
        self.id = len(self.storage['events'])

        # Creating event:
        event_params = self.default_event_params.copy()
        event_params.update({
            'liquidityPercent': 10_000,
            'betsCloseTime': RUN_TIME + ONE_HOUR,
            'measurePeriod': ONE_HOUR,
        })
        self.storage = self.check_new_event_succeed(
            event_params=event_params,
            amount=self.measure_start_fee + self.expiration_fee)

        # Participant A: adding liquidity 1/1 just at start:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=2_000_000,
            expected_for=1,
            expected_against=1)

        # Participant B: bets FOR for 1 tez:
        self.storage = self.check_bet_succeed(
            participant=self.b,
            amount=1_000_000,
            bet='for',
            minimal_win=1_000_000)

        # Participant A: adding more liquidity after 30 mins with 1:4:
        self.current_time = int(RUN_TIME + 0.5*ONE_HOUR)
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=2_500_000,
            expected_for=4,
            expected_against=1)

        # Participant C: adding more liquidity after 30 mins with 1:4:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.c,
            amount=5_000_000,
            expected_for=4,
            expected_against=1)

        # Participant D: bets AGAINST for 2 tez:
        self.storage = self.check_bet_succeed(
            participant=self.d,
            amount=2_000_000,
            bet='against',
            minimal_win=2_000_000)

        # Participant B: bets FOR for 4 tez:
        self.storage = self.check_bet_succeed(
            participant=self.b,
            amount=4_000_000,
            bet='for',
            minimal_win=4_000_000)

        # Participant A: adding more liquidity after 30 mins with 1:4:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=5_000_000,
            expected_for=4,
            expected_against=1)

        # Running measurement:
        self.current_time = RUN_TIME + 2*ONE_HOUR
        self.storage = self.check_start_measurement_succeed(sender=self.a)

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - int(0.5*ONE_HOUR),
            'rate': 8_000_000
        }
        self.storage = self.check_start_measurement_callback_succeed(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)
            
        # Closing event:
        self.current_time = RUN_TIME + 3*ONE_HOUR
        self.storage = self.check_close_succeed(sender=self.b)

        # Emulating calback with price is increased 25%:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - int(0.5*ONE_HOUR),
            'rate': 6_000_000
        }
        self.storage = self.check_close_callback_succeed(
            callback_values=callback_values,
            source=self.b,
            sender=self.oracle_address)

        # Withdrawals:
        self.current_time = RUN_TIME + 4*ONE_HOUR
        self.storage = self.check_withdraw_succeed(self.a, 10_520_000)
        self.storage = self.check_withdraw_succeed(self.b, 0)
        self.storage = self.check_withdraw_succeed(self.c, 5_020_000)
        self.storage = self.check_withdraw_succeed(self.d, 5_960_000)
