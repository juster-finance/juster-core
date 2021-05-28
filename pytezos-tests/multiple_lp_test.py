""" Event: XTZ-USD dynamics would be > 1 in 1 hour after betting period of 1 hour.
    Liquidity pool 0%

    Three participants: a, b and c making next interactions:
    (1) participant A adds initial liquidity at the beginning: 2tez with ratio 1:1

                                               +30m
                                     A.LP B.F  A.LP C.LP D.A  B.F  A.LP
                                     (1)  (2)  (3)  (4)  (5)  (6)  (7)
    poolBellow:                     1.0  0.5  1.0  2.0  4.0  2.0  2.5
    poolAboveEq:                         1.0  2.0  4.0  8.0  4.0  8.0 10.0

    liquidityShares % added          -         100% 100%           25%
    liquidityShares diff             100  -    100  200  -    -    100
    totalLiquidityShares             100       200  400  -    -    500

    A shares: 300, C shares: 200

    (2) participant B bets aboveEq 1tez
        - new ratio: 0.5:2
    (3) participant A adds more liquidity: 2.5tez with ratio 1:4, after 30 mins
    (4) participant C adds more liquidity: 5tez with ratio 1:4, after 30 mins
    (5) participant D bets bellow for 2tez
    (6) participant B bets aboveEq 4tez
    (7) participant A adds more liquidity 5tez

    Result: betBellow win
        - A: get liquidity bonus:
            (1) get 100% of first B bet: + 1.0
            (2) loose 50% of D bet: -2.0
            (3) get 50% of second B bet: +2.0
            (4) returns all provided liquidity in the end: 9.5tez
                --- +10.50tez
        - B: loose 5 tez (returns 0)
        - C: get liquidity bonus:
            (5) looses to participant D: -2.0
            (6) get 50% of second B bet: +2.0
            (7) returns liquidity: 5tez
                --- +5.00tez
        - D: wins 4 tez: 2 + 4

            10.5 + 0 + 5 + 6
        - total 21.5 tez
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
            expected_above_eq=1,
            expected_bellow=1)

        # Participant B: bets aboveEq for 1 tez:
        self.storage = self.check_bet_succeed(
            participant=self.b,
            amount=1_000_000,
            bet='aboveEq',
            minimal_win=1_000_000)

        # Participant A: adding more liquidity after 30 mins with 1:4:
        self.current_time = int(RUN_TIME + 0.5*ONE_HOUR)
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=2_500_000,
            expected_above_eq=4,
            expected_bellow=1)

        # Participant C: adding more liquidity after 30 mins with 1:4:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.c,
            amount=5_000_000,
            expected_above_eq=4,
            expected_bellow=1)

        # Participant D: bets bellow for 2 tez:
        self.storage = self.check_bet_succeed(
            participant=self.d,
            amount=2_000_000,
            bet='bellow',
            minimal_win=2_000_000)

        # Participant B: bets aboveEq for 4 tez:
        self.storage = self.check_bet_succeed(
            participant=self.b,
            amount=4_000_000,
            bet='aboveEq',
            minimal_win=4_000_000)

        # Participant A: adding more liquidity after 30 mins with 1:4:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=5_000_000,
            expected_above_eq=4,
            expected_bellow=1)

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
        self.storage = self.check_withdraw_succeed(self.a, 10_500_000)
        self.storage = self.check_withdraw_succeed(self.b, 0)
        self.storage = self.check_withdraw_succeed(self.c, 5_000_000)
        self.storage = self.check_withdraw_succeed(self.d, 6_000_000)
